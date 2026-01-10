"""Canvas service API smoke tests."""
import pytest
import httpx


@pytest.mark.asyncio
async def test_health_check(canvas_url):
    """Verify canvas service is healthy."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{canvas_url}/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_canvas(canvas_url):
    """Verify canvas retrieval works."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{canvas_url}/api/canvas")
        assert response.status_code == 200
        data = response.json()
        assert "quotes" in data


@pytest.mark.asyncio
async def test_get_workspace(canvas_url):
    """Verify workspace retrieval works."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{canvas_url}/api/workspace")
        assert response.status_code == 200
        data = response.json()
        assert "notes" in data
