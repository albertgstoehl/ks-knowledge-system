# kasten/tests/test_events.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.database import init_db


def get_test_app():
    """Create test app without static file mounts."""
    from fastapi import FastAPI
    from src.routers import events

    test_app = FastAPI(title="Kasten Events Test")
    test_app.include_router(events.router)
    return test_app


@pytest.mark.asyncio
async def test_get_events_empty():
    """Test getting events when none exist"""
    await init_db("sqlite+aiosqlite:///:memory:")
    app = get_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/events")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "kasten"
        assert data["events"] == []


@pytest.mark.asyncio
async def test_get_events_with_since_filter():
    """Test that since filter works (empty case)"""
    await init_db("sqlite+aiosqlite:///:memory:")
    app = get_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/events?since=2025-01-01T00:00:00")
        assert response.status_code == 200
        assert response.json()["events"] == []
