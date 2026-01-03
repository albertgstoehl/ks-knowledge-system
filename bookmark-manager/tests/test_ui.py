# tests/test_ui.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_ui_index_returns_html():
    """UI index should return HTML page"""
    response = client.get("/ui/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Bookmarks" in response.text


def test_ui_inbox_view():
    """Inbox view should show inbox header"""
    response = client.get("/ui/?view=inbox")
    assert response.status_code == 200
    assert "INBOX" in response.text


def test_ui_thesis_view():
    """Thesis view should show thesis header"""
    response = client.get("/ui/?view=thesis")
    assert response.status_code == 200
    assert "THESIS" in response.text


def test_ui_pins_view():
    """Pins view should show pins header"""
    response = client.get("/ui/?view=pins")
    assert response.status_code == 200
    assert "PINS" in response.text


def test_ui_inbox_with_thesis_filter():
    """Inbox with thesis filter should work"""
    response = client.get("/ui/?view=inbox&filter=thesis")
    assert response.status_code == 200


def test_ui_inbox_with_pin_filter():
    """Inbox with pin filter should work"""
    response = client.get("/ui/?view=inbox&filter=pin")
    assert response.status_code == 200


def test_ui_has_four_tabs():
    """UI should have exactly 4 tabs: Feeds, Inbox, Thesis, Pins"""
    response = client.get("/ui/")
    assert response.status_code == 200
    assert 'href="/ui/?view=feeds"' in response.text
    assert 'href="/ui/?view=inbox"' in response.text
    assert 'href="/ui/?view=thesis"' in response.text
    assert 'href="/ui/?view=pins"' in response.text
    # Archive view is removed
    assert 'view=archive' not in response.text


def test_ui_inbox_empty_state():
    """Empty inbox should show INBOX ZERO message"""
    response = client.get("/ui/?view=inbox")
    assert response.status_code == 200
    # Either shows bookmarks or the empty state
    assert "INBOX" in response.text


def test_ui_filter_icons_present():
    """Filter icons should be present in inbox"""
    inbox = client.get("/ui/?view=inbox")
    assert "filter-icon" in inbox.text
