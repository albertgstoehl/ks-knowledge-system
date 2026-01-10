"""Kasten service API smoke tests."""
import pytest
import httpx


@pytest.mark.asyncio
async def test_health_check(kasten_url):
    """Verify kasten service is healthy."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{kasten_url}/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_notes(kasten_url):
    """Verify note listing works."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{kasten_url}/api/notes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_entry_points(kasten_url):
    """Verify entry points endpoint works."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{kasten_url}/api/notes/entry-points")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
