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
        await db.execute("UPDATE app_state SET break_until = NULL WHERE id = 1")
        # Set evening cutoff to 23:59 to allow tests to run any time
        await db.execute("UPDATE settings SET evening_cutoff = '23:59' WHERE id = 1")
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


async def test_delete_nextup():
    """Test deleting a next_up item."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create item
        create_resp = await client.post("/api/nextup", json={"text": "To delete"})
        item_id = create_resp.json()["id"]

        # Delete it
        response = await client.delete(f"/api/nextup/{item_id}")
        assert response.status_code == 200

        # Verify it's gone
        list_resp = await client.get("/api/nextup")
        assert list_resp.json()["count"] == 0


async def test_update_nextup():
    """Test updating a next_up item."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create item
        create_resp = await client.post("/api/nextup", json={"text": "Original"})
        item_id = create_resp.json()["id"]

        # Update it
        response = await client.put(
            f"/api/nextup/{item_id}",
            json={"text": "Updated", "due_date": "2026-01-15"}
        )
        assert response.status_code == 200
        assert response.json()["text"] == "Updated"

        # Verify in list
        list_resp = await client.get("/api/nextup")
        items = list_resp.json()["items"]
        assert items[0]["text"] == "Updated"
        assert items[0]["due_date"] == "2026-01-15"


async def test_start_session_with_nextup():
    """Test starting a session linked to a next_up item."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create next_up item
        create_resp = await client.post("/api/nextup", json={"text": "Work on feature"})
        item_id = create_resp.json()["id"]

        # Start session with next_up_id
        response = await client.post("/api/sessions/start", json={
            "type": "expected",
            "intention": "Work on feature",
            "next_up_id": item_id
        })
        assert response.status_code == 200

        # Verify session count on next_up item
        list_resp = await client.get("/api/nextup")
        items = list_resp.json()["items"]
        assert items[0]["session_count"] == 1
