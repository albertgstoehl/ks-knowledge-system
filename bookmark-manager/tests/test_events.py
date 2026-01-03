# bookmark-manager/tests/test_events.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src import database
from src.models import Event
from sqlalchemy import delete, select
from datetime import datetime
import json


@pytest.fixture(scope="function", autouse=True)
async def clean_events():
    """Clean events table between tests"""
    async with database.async_session_maker() as session:
        await session.execute(delete(Event))
        await session.commit()
    yield


@pytest.mark.asyncio
async def test_get_events_empty():
    """Test getting events when none exist"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/events")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "bookmark-manager"
        assert data["events"] == []


@pytest.mark.asyncio
async def test_get_events_with_data():
    """Test getting events with data"""
    # Insert test event
    async with database.async_session_maker() as session:
        event = Event(
            timestamp=datetime(2026, 1, 1, 0, 0, 0),
            event_type="funnel",
            name="bookmark_created",
            event_metadata=json.dumps({"source": "manual"})
        )
        session.add(event)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/events")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["name"] == "bookmark_created"
        assert data["events"][0]["metadata"]["source"] == "manual"


@pytest.mark.asyncio
async def test_get_events_with_since_filter():
    """Test filtering events by timestamp"""
    # Insert test event
    async with database.async_session_maker() as session:
        event = Event(
            timestamp=datetime(2026, 1, 1, 0, 0, 0),
            event_type="funnel",
            name="bookmark_created",
            event_metadata=json.dumps({"source": "manual"})
        )
        session.add(event)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Should find the event
        response = await client.get("/api/events?since=2025-12-01T00:00:00")
        assert response.status_code == 200
        assert len(response.json()["events"]) == 1

        # Should not find the event (since is after)
        response = await client.get("/api/events?since=2026-02-01T00:00:00")
        assert response.status_code == 200
        assert len(response.json()["events"]) == 0
