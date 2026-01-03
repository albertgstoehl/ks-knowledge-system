# kasten/tests/test_api.py
import pytest
import tempfile
import os
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import init_db

async def setup_test_env():
    """Initialize database and create temp dir with test notes."""
    await init_db("sqlite+aiosqlite:///:memory:")
    tmpdir = tempfile.mkdtemp()
    with open(os.path.join(tmpdir, "1219a.md"), "w") as f:
        f.write("Note A title\n\nLinks to [[1219b]]")
    with open(os.path.join(tmpdir, "1219b.md"), "w") as f:
        f.write("Note B title\n\nNo outgoing links")
    os.environ["NOTES_PATH"] = tmpdir
    return tmpdir

@pytest.mark.asyncio
async def test_get_notes():
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/reindex")
        response = await client.get("/api/notes")
        assert response.status_code == 200
        notes = response.json()
        assert len(notes) == 2

@pytest.mark.asyncio
async def test_get_note():
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/reindex")
        response = await client.get("/api/notes/1219a")
        assert response.status_code == 200
        note = response.json()
        assert note["id"] == "1219a"
        assert "content" in note

@pytest.mark.asyncio
async def test_get_entry_points():
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/reindex")
        response = await client.get("/api/notes/entry-points")
        assert response.status_code == 200
        entries = response.json()
        # 1219a has outgoing link but 1219b has backlink, so 1219a is entry point
        assert any(e["id"] == "1219a" for e in entries)

@pytest.mark.asyncio
async def test_get_random():
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/reindex")
        response = await client.get("/api/notes/random")
        assert response.status_code == 200
        note = response.json()
        assert note["id"] in ["1219a", "1219b"]

@pytest.mark.asyncio
async def test_get_links():
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/reindex")
        response = await client.get("/api/notes/1219a/links")
        assert response.status_code == 200
        links = response.json()
        assert "forward" in links
        assert "back" in links
        assert "1219b" in [l["id"] for l in links["forward"]]


@pytest.mark.asyncio
async def test_create_source():
    """Test POST /api/sources creates a source"""
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sources", json={
            "url": "https://example.com/article",
            "title": "Test Article",
            "description": "A fascinating article about testing"
        })
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["url"] == "https://example.com/article"
        assert data["title"] == "Test Article"


@pytest.mark.asyncio
async def test_get_source():
    """Test GET /api/sources/{id} returns source with note_ids"""
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create source
        create_resp = await client.post("/api/sources", json={
            "url": "https://example.com/get-test",
            "title": "Get Test"
        })
        source_id = create_resp.json()["id"]

        # Get source
        response = await client.get(f"/api/sources/{source_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == source_id
        assert data["url"] == "https://example.com/get-test"
        assert "note_ids" in data


@pytest.mark.asyncio
async def test_create_note_with_source():
    """Test creating a note linked to a source"""
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create source first
        source_resp = await client.post("/api/sources", json={
            "url": "https://example.com/note-source",
            "title": "Note Source"
        })
        source_id = source_resp.json()["id"]

        # Create note with source
        response = await client.post("/api/notes", json={
            "title": "Note from Source",
            "content": "This note came from a source",
            "source_id": source_id
        })
        assert response.status_code == 201
        data = response.json()
        assert "id" in data


@pytest.mark.asyncio
async def test_get_note_with_source():
    """Test GET /api/notes/{id} includes source data"""
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create source
        source_resp = await client.post("/api/sources", json={
            "url": "https://example.com/full-test",
            "title": "Full Test Source",
            "description": "A test description"
        })
        source_id = source_resp.json()["id"]

        # Create note with source
        note_resp = await client.post("/api/notes", json={
            "title": "Note With Source",
            "content": "Content here",
            "source_id": source_id
        })
        note_id = note_resp.json()["id"]

        # Get note
        response = await client.get(f"/api/notes/{note_id}")
        assert response.status_code == 200
        data = response.json()
        assert "source" in data
        assert data["source"]["url"] == "https://example.com/full-test"
        assert data["source"]["title"] == "Full Test Source"
