import pytest
import os
from playwright.sync_api import Page, Browser
from playwright.sync_api import sync_playwright

@pytest.fixture(scope="session")
def base_url():
    """Base URL for E2E tests (defaults to dev environment)."""
    return os.getenv("BASE_URL", "https://bookmark.gstoehl.dev/dev")

@pytest.fixture(scope="session")
def bookmark_url(base_url):
    """Bookmark manager service URL."""
    # Dev: https://bookmark.gstoehl.dev/dev
    # Prod: https://bookmark.gstoehl.dev
    return base_url.replace("bookmark.gstoehl.dev", "bookmark.gstoehl.dev")

@pytest.fixture(scope="session")
def canvas_url(base_url):
    """Canvas service URL."""
    return base_url.replace("bookmark.gstoehl.dev", "canvas.gstoehl.dev")

@pytest.fixture(scope="session")
def kasten_url(base_url):
    """Kasten service URL."""
    return base_url.replace("bookmark.gstoehl.dev", "kasten.gstoehl.dev")

@pytest.fixture(scope="session")
def balance_url(base_url):
    """Balance service URL."""
    return base_url.replace("bookmark.gstoehl.dev", "balance.gstoehl.dev")

# Playwright fixtures for UI tests
@pytest.fixture(scope="session")
def browser():
    """Browser instance for UI tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()

@pytest.fixture
def page(browser):
    """Page instance for UI tests."""
    page = browser.new_page()
    yield page
    page.close()

# Alias fixtures for backward compatibility with API tests
@pytest.fixture(scope="session")
def bookmark_manager_url(bookmark_url):
    """Alias for bookmark_url for consistency."""
    return bookmark_url
