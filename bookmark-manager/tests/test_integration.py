import pytest
from httpx import AsyncClient
from src.main import app
import asyncio


@pytest.mark.asyncio
async def test_full_bookmark_workflow():
    """Test complete workflow: add → search → mark read → search filtered"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Add bookmark
        response = await client.post(
            "/bookmarks",
            json={"url": "https://python.org"}
        )
        assert response.status_code == 201
        bookmark = response.json()
        bookmark_id = bookmark["id"]
        assert bookmark["state"] == "inbox"

        # 2. Wait for background processing
        await asyncio.sleep(3)

        # 3. Verify bookmark was processed
        response = await client.get(f"/bookmarks/{bookmark_id}")
        assert response.status_code == 200
        processed = response.json()
        assert processed["title"] is not None

        # 4. Semantic search
        response = await client.post(
            "/search/semantic",
            json={"query": "programming language", "limit": 10}
        )
        assert response.status_code == 200
        results = response.json()
        assert len(results) > 0

        # 5. Mark as read
        response = await client.patch(
            f"/bookmarks/{bookmark_id}",
            json={"state": "read"}
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["state"] == "read"
        assert updated["read_at"] is not None

        # 6. Search with state filter (inbox should be empty)
        response = await client.post(
            "/search/keyword",
            json={"query": "python", "state": "inbox"}
        )
        assert response.status_code == 200
        inbox_results = response.json()
        assert len(inbox_results) == 0

        # 7. Search read items
        response = await client.post(
            "/search/keyword",
            json={"query": "python", "state": "read"}
        )
        assert response.status_code == 200
        read_results = response.json()
        assert len(read_results) > 0

        # 8. Delete bookmark
        response = await client.delete(f"/bookmarks/{bookmark_id}")
        assert response.status_code == 204

        # 9. Verify deleted
        response = await client.get(f"/bookmarks/{bookmark_id}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_backup_workflow():
    """Test backup and restore"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create backup
        response = await client.post("/backup/create")
        assert response.status_code == 201

        # List backups
        response = await client.get("/backup/list")
        assert response.status_code == 200
        backups = response.json()
        assert len(backups) > 0
