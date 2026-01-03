import pytest
from httpx import AsyncClient, ASGITransport
from src.database import init_db

# Create a fresh app for testing
def get_test_app():
    from fastapi import FastAPI
    from src.routers import canvas, workspace

    test_app = FastAPI(title="Canvas Test")
    test_app.include_router(canvas.router)
    test_app.include_router(workspace.router)
    return test_app

@pytest.fixture
async def client():
    await init_db("sqlite+aiosqlite:///:memory:")
    app = get_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_get_workspace_empty(client):
    response = await client.get("/api/workspace")
    assert response.status_code == 200
    data = response.json()
    assert data["notes"] == []
    assert data["connections"] == []

@pytest.mark.asyncio
async def test_add_note_to_workspace(client):
    response = await client.post("/api/workspace/notes", json={
        "km_note_id": "abc123",
        "content": "Test note content"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["km_note_id"] == "abc123"
    assert "id" in data

@pytest.mark.asyncio
async def test_add_connection(client):
    # Add two notes
    r1 = await client.post("/api/workspace/notes", json={"km_note_id": "a", "content": "A"})
    r2 = await client.post("/api/workspace/notes", json={"km_note_id": "b", "content": "B"})
    note1_id = r1.json()["id"]
    note2_id = r2.json()["id"]

    # Add connection
    response = await client.post("/api/workspace/connections", json={
        "from_note_id": note1_id,
        "to_note_id": note2_id,
        "label": "therefore"
    })
    assert response.status_code == 201
    assert response.json()["label"] == "therefore"

@pytest.mark.asyncio
async def test_delete_note(client):
    r = await client.post("/api/workspace/notes", json={"km_note_id": "a", "content": "A"})
    note_id = r.json()["id"]

    response = await client.delete(f"/api/workspace/notes/{note_id}")
    assert response.status_code == 200

    workspace = await client.get("/api/workspace")
    assert len(workspace.json()["notes"]) == 0
