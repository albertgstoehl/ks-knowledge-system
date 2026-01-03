import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_semantic_search():
    """Test semantic search"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create test bookmarks
        await client.post("/bookmarks", json={"url": "https://python.org"})

        # Wait a moment for background processing
        import asyncio
        await asyncio.sleep(2)

        # Search
        response = await client.post(
            "/search/semantic",
            json={"query": "python programming", "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

@pytest.mark.asyncio
async def test_keyword_search():
    """Test keyword search"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Search
        response = await client.post(
            "/search/keyword",
            json={"query": "python", "limit": 10}
        )

        assert response.status_code == 200
