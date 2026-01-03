# kasten/tests/test_integration.py
import pytest
import tempfile
import os
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import init_db


async def setup_integration_env():
    """Setup clean test environment"""
    await init_db("sqlite+aiosqlite:///:memory:")
    tmpdir = tempfile.mkdtemp()
    os.environ["NOTES_PATH"] = tmpdir
    return tmpdir


@pytest.mark.asyncio
async def test_full_source_to_note_flow():
    """Test complete flow: create source -> create note with source -> view note with source"""
    await setup_integration_env()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create source (simulating what Canvas would do)
        source_resp = await client.post("/api/sources", json={
            "url": "https://youtu.be/ABC123",
            "title": "How to Learn Effectively",
            "description": "A video about spaced repetition and active recall",
            "video_id": "ABC123"
        })
        assert source_resp.status_code == 201
        source = source_resp.json()
        source_id = source["id"]

        # 2. Create note linked to source
        note_resp = await client.post("/api/notes", json={
            "title": "Learning Techniques",
            "content": "Key insight: Active recall beats passive review",
            "source_id": source_id
        })
        assert note_resp.status_code == 201
        note_id = note_resp.json()["id"]

        # 3. Get note via API - should include source
        get_resp = await client.get(f"/api/notes/{note_id}")
        assert get_resp.status_code == 200
        note_data = get_resp.json()

        assert note_data["source"] is not None
        assert note_data["source"]["url"] == "https://youtu.be/ABC123"
        assert note_data["source"]["title"] == "How to Learn Effectively"
        assert note_data["source"]["video_id"] == "ABC123"

        # 4. Get source - should list note
        source_get_resp = await client.get(f"/api/sources/{source_id}")
        assert source_get_resp.status_code == 200
        source_data = source_get_resp.json()
        assert note_id in source_data["note_ids"]

        # 5. View note page - should include source
        page_resp = await client.get(f"/note/{note_id}")
        assert page_resp.status_code == 200
        assert b"Source:" in page_resp.content
        assert b"How to Learn Effectively" in page_resp.content
        assert b"youtu.be" in page_resp.content


@pytest.mark.asyncio
async def test_note_without_source():
    """Test that notes without sources still work"""
    await setup_integration_env()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create note without source
        note_resp = await client.post("/api/notes", json={
            "title": "Standalone Note",
            "content": "No source for this one"
        })
        assert note_resp.status_code == 201
        note_id = note_resp.json()["id"]

        # Get note - source should be None
        get_resp = await client.get(f"/api/notes/{note_id}")
        note_data = get_resp.json()
        assert note_data["source"] is None

        # View note page - should NOT have source header
        page_resp = await client.get(f"/note/{note_id}")
        assert page_resp.status_code == 200
        assert b"Source:" not in page_resp.content
