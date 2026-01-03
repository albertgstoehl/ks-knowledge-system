import pytest
from httpx import AsyncClient, ASGITransport
from src.database import init_db

# Create a fresh app for testing
def get_test_app():
    from fastapi import FastAPI
    from src.routers import canvas

    test_app = FastAPI(title="Canvas Test")
    test_app.include_router(canvas.router)
    return test_app

@pytest.fixture
async def client():
    await init_db("sqlite+aiosqlite:///:memory:")
    app = get_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_get_canvas_empty(client):
    response = await client.get("/api/canvas")
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert data["content"] == ""

@pytest.mark.asyncio
async def test_put_canvas(client):
    response = await client.put("/api/canvas", json={"content": "Hello world"})
    assert response.status_code == 200

    response = await client.get("/api/canvas")
    assert response.json()["content"] == "Hello world"

@pytest.mark.asyncio
async def test_post_quote(client):
    response = await client.post("/api/quotes", json={
        "quote": "Test quote",
        "source_url": "https://example.com",
        "source_title": "Example"
    })
    assert response.status_code == 201

    response = await client.get("/api/canvas")
    content = response.json()["content"]
    assert '> "Test quote"' in content
    assert "Example" in content


@pytest.mark.asyncio
async def test_delete_canvas(client):
    # First add some content
    await client.put("/api/canvas", json={"content": "Some draft content"})
    response = await client.get("/api/canvas")
    assert response.json()["content"] == "Some draft content"

    # Delete (clear) the canvas
    response = await client.delete("/api/canvas")
    assert response.status_code == 200
    assert response.json()["status"] == "cleared"

    # Verify it's empty
    response = await client.get("/api/canvas")
    assert response.json()["content"] == ""
