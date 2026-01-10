"""Bookmark Manager service API smoke tests."""
import pytest
import httpx


@pytest.mark.asyncio
async def test_health_check(bookmark_url):
    """Verify bookmark-manager service is healthy."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{bookmark_url}/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_create_and_retrieve_bookmark(bookmark_url):
    """Verify bookmark creation and retrieval."""
    async with httpx.AsyncClient() as client:
        # Create bookmark
        response = await client.post(
            f"{bookmark_url}/api/bookmarks",
            json={"url": "https://example.com", "title": "Example"}
        )
        assert response.status_code == 201
        bookmark_id = response.json()["id"]
        
        # Retrieve bookmark
        response = await client.get(f"{bookmark_url}/api/bookmarks/{bookmark_id}")
        assert response.status_code == 200
        assert response.json()["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_list_bookmarks(bookmark_url):
    """Verify bookmark listing works."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{bookmark_url}/api/bookmarks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_rss_feeds(bookmark_url):
    """Verify RSS feeds endpoint works."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{bookmark_url}/api/feeds")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
