import pytest
from httpx import AsyncClient, ASGITransport
import os

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

    async with get_db() as db:
        await db.execute("DELETE FROM next_up")
        await db.execute("DELETE FROM sessions")
        await db.execute("DELETE FROM priorities")
        await db.commit()
    yield


async def test_list_nextup_empty():
    """Test listing next_up when empty."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/nextup")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["count"] == 0
        assert data["max"] == 5


async def test_create_nextup():
    """Test creating a next_up item."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/nextup", json={"text": "Do taxes"})
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Do taxes"
        assert data["id"] is not None


async def test_create_nextup_max_limit():
    """Test that creating beyond max fails."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create 5 items
        for i in range(5):
            response = await client.post("/api/nextup", json={"text": f"Task {i}"})
            assert response.status_code == 200

        # 6th should fail
        response = await client.post("/api/nextup", json={"text": "Task 6"})
        assert response.status_code == 400
        assert "Maximum" in response.json()["detail"]
