import pytest
import os

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
