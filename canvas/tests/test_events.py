# canvas/tests/test_events.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.database import init_db


def get_test_app():
    from fastapi import FastAPI
    from src.routers import events

    test_app = FastAPI(title="Canvas Events Test")
    test_app.include_router(events.router)
    return test_app


@pytest.fixture
async def client():
    await init_db("sqlite+aiosqlite:///:memory:")
    app = get_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_get_events_empty(client):
    """Test getting events when none exist"""
    response = await client.get("/api/events")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "canvas"
    assert data["events"] == []


@pytest.mark.asyncio
async def test_get_events_with_since_filter(client):
    """Test that since filter works (empty case)"""
    response = await client.get("/api/events?since=2025-01-01T00:00:00")
    assert response.status_code == 200
    assert response.json()["events"] == []
