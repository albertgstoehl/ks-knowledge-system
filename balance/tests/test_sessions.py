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
    else:
        # Clean up from previous test
        async with get_db() as db:
            await db.execute("DELETE FROM sessions")
            await db.execute("UPDATE app_state SET break_until = NULL WHERE id = 1")
            await db.commit()
    yield


async def test_start_session():
    """Test starting a new session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions/start", json={
            "type": "expected",
            "intention": "Fix bug"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "expected"
        assert data["intention"] == "Fix bug"
        assert "id" in data
        assert "started_at" in data


async def test_end_session():
    """Test ending a session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start session first
        start_response = await client.post("/api/sessions/start", json={
            "type": "personal",
            "intention": "Research"
        })
        assert start_response.status_code == 200

        # End it
        response = await client.post("/api/sessions/end", json={
            "distractions": "none",
            "did_the_thing": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ended_at"] is not None
        assert data["distractions"] == "none"
        assert data["did_the_thing"] == 1  # SQLite returns 1 for True


async def test_break_check_not_on_break():
    """Test break check when not on break."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/check")
        assert response.status_code == 200
        data = response.json()
        assert data["on_break"] is False
        assert data["remaining_seconds"] == 0


async def test_break_check_on_break():
    """Test break check when on break."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start and end a session to trigger break
        await client.post("/api/sessions/start", json={"type": "expected"})
        await client.post("/api/sessions/end", json={
            "distractions": "none",
            "did_the_thing": True
        })

        # Check if on break
        response = await client.get("/api/check")
        assert response.status_code == 200
        data = response.json()
        assert data["on_break"] is True
        assert data["remaining_seconds"] > 0
