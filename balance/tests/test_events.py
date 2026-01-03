# balance/tests/test_events.py
import pytest
from httpx import AsyncClient, ASGITransport
import os

# Verify DATABASE_URL is set
assert "DATABASE_URL" in os.environ, "Run tests with DATABASE_URL=./data/test.db"

from src.database import init_db, get_db
from src.main import app


_db_initialized = False


@pytest.fixture(autouse=True)
async def setup_test():
    """Initialize database and cleanup between tests."""
    global _db_initialized
    if not _db_initialized:
        await init_db()
        _db_initialized = True

    # Clean up events from previous tests
    async with get_db() as db:
        await db.execute("DELETE FROM events")
        await db.commit()
    yield


@pytest.mark.asyncio
async def test_get_events_empty():
    """Test getting events when none exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/events")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "balance"
        assert data["events"] == []


@pytest.mark.asyncio
async def test_get_events_with_data():
    """Test getting events with data."""
    # Insert test event
    async with get_db() as db:
        await db.execute(
            "INSERT INTO events (timestamp, event_type, name, metadata) VALUES (?, ?, ?, ?)",
            ("2026-01-01T00:00:00", "feature", "youtube_session_started", '{"duration_minutes": 15}')
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/events")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["name"] == "youtube_session_started"
        assert data["events"][0]["metadata"]["duration_minutes"] == 15


@pytest.mark.asyncio
async def test_get_events_with_since_filter():
    """Test filtering events by timestamp."""
    # Insert test event
    async with get_db() as db:
        await db.execute(
            "INSERT INTO events (timestamp, event_type, name, metadata) VALUES (?, ?, ?, ?)",
            ("2026-01-01T00:00:00", "feature", "nextup_created", '{"text": "Test task"}')
        )
        await db.commit()

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
