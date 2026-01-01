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

    # Clean up data from previous tests
    async with get_db() as db:
        await db.execute("DELETE FROM sessions")
        await db.execute("DELETE FROM priorities")
        await db.commit()
    yield


async def test_list_priorities_empty():
    """Test listing priorities when none exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/priorities")
        assert response.status_code == 200
        assert response.json() == []


async def test_list_priorities_with_data():
    """Test listing priorities with existing data."""
    # Insert test priorities
    async with get_db() as db:
        await db.execute(
            "INSERT INTO priorities (name, rank, created_at) VALUES (?, ?, ?)",
            ("Thesis", 1, "2025-01-01T00:00:00")
        )
        await db.execute(
            "INSERT INTO priorities (name, rank, created_at) VALUES (?, ?, ?)",
            ("Health", 2, "2025-01-01T00:00:00")
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/priorities")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Thesis"
        assert data[0]["rank"] == 1
        assert data[0]["session_count"] == 0
        assert data[1]["name"] == "Health"
        assert data[1]["rank"] == 2


async def test_list_priorities_excludes_archived():
    """Test that archived priorities are excluded from list."""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO priorities (name, rank, created_at) VALUES (?, ?, ?)",
            ("Active", 1, "2025-01-01T00:00:00")
        )
        await db.execute(
            "INSERT INTO priorities (name, rank, created_at, archived_at) VALUES (?, ?, ?, ?)",
            ("Archived", 2, "2025-01-01T00:00:00", "2025-01-02T00:00:00")
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/priorities")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Active"


async def test_list_priorities_with_session_count():
    """Test that session count is correctly calculated."""
    async with get_db() as db:
        # Create a priority
        cursor = await db.execute(
            "INSERT INTO priorities (name, rank, created_at) VALUES (?, ?, ?)",
            ("Work", 1, "2025-01-01T00:00:00")
        )
        priority_id = cursor.lastrowid

        # Create some sessions linked to this priority
        await db.execute(
            "INSERT INTO sessions (type, priority_id, started_at) VALUES (?, ?, ?)",
            ("expected", priority_id, "2025-01-01T10:00:00")
        )
        await db.execute(
            "INSERT INTO sessions (type, priority_id, started_at) VALUES (?, ?, ?)",
            ("expected", priority_id, "2025-01-01T11:00:00")
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/priorities")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Work"
        assert data[0]["session_count"] == 2


async def test_create_priority():
    """Test creating a new priority."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/priorities", json={"name": "Thesis"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Thesis"
        assert data["rank"] == 1
        assert data["id"] is not None


async def test_create_priority_auto_ranks():
    """Test that priorities auto-increment ranks."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/priorities", json={"name": "First"})
        response = await client.post("/api/priorities", json={"name": "Second"})
        assert response.json()["rank"] == 2
