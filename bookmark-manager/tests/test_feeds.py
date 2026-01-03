# tests/test_feeds.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_feeds_ui_returns_html():
    """Feeds view should return HTML page"""
    response = client.get("/ui/?view=feeds")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Feeds" in response.text


def test_list_feeds_empty():
    """List feeds should return empty list initially"""
    response = client.get("/feeds")
    assert response.status_code == 200
    assert response.json() == []


def test_create_feed_invalid_url():
    """Creating feed with invalid RSS should fail"""
    response = client.post("/feeds", json={"url": "https://example.com/not-a-feed"})
    assert response.status_code == 400
