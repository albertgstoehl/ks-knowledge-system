"""
UI test fixtures and utilities for Playwright tests.
"""
import pytest
import httpx
from playwright.sync_api import Page


@pytest.fixture
def api_client(base_url):
    """HTTP client for API setup calls."""
    # Convert UI URL to API URL (remove /dev suffix for API calls)
    api_base = base_url.rstrip("/")
    with httpx.Client(base_url=api_base, timeout=30.0) as client:
        yield client


@pytest.fixture
def balance_api(balance_url):
    """HTTP client for Balance API."""
    with httpx.Client(base_url=balance_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def bookmark_api(bookmark_manager_url):
    """HTTP client for Bookmark Manager API."""
    with httpx.Client(base_url=bookmark_manager_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def canvas_api(canvas_url):
    """HTTP client for Canvas API."""
    with httpx.Client(base_url=canvas_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def kasten_api(kasten_url):
    """HTTP client for Kasten API."""
    with httpx.Client(base_url=kasten_url, timeout=30.0) as client:
        yield client


def wait_for_idle(page: Page, timeout: int = 5000):
    """Wait for network idle and animations to settle."""
    page.wait_for_load_state("networkidle", timeout=timeout)
    page.wait_for_timeout(100)  # Brief pause for JS to settle
