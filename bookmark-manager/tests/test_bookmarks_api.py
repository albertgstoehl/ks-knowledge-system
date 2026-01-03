import pytest
from httpx import AsyncClient, ASGITransport
from src.models import Bookmark, BookmarkState
from src import database
from sqlalchemy import select, delete
from src.main import app

@pytest.fixture(scope="function", autouse=True)
async def clean_db():
    """Clean database between tests"""
    # Clear all bookmarks between tests
    async with database.async_session_maker() as session:
        await session.execute(delete(Bookmark))
        await session.commit()

    yield

@pytest.mark.asyncio
async def test_create_bookmark():
    """Test creating a new bookmark"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/bookmarks",
            json={"url": "https://example.com"}
        )

        assert response.status_code == 201
        data = response.json()
        # Pydantic HttpUrl adds trailing slash
        assert data["url"] == "https://example.com/" or data["url"] == "https://example.com"
        assert data["state"] == "inbox"

@pytest.mark.asyncio
async def test_list_bookmarks():
    """Test listing bookmarks"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create bookmark first
        await client.post("/bookmarks", json={"url": "https://example.com"})

        # List bookmarks
        response = await client.get("/bookmarks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0


@pytest.mark.asyncio
async def test_get_recently_archived():
    """Should return recently archived bookmarks"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/bookmarks/recently-archived")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_bookmark_response_has_is_thesis():
    """Test that bookmark response includes is_thesis field"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/bookmarks", json={"url": "https://example.com/thesis-test"})
        assert response.status_code == 201
        data = response.json()
        assert "is_thesis" in data
        assert "expires_at" in data


@pytest.mark.asyncio
async def test_bookmark_expires_in_7_days():
    """Regular bookmarks expire in 7 days"""
    from datetime import datetime, timedelta, timezone

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/bookmarks", json={"url": "https://example.com/expiry-calc"})
        assert response.status_code == 201
        data = response.json()

        # Parse expires_at - handle Z suffix
        expires_str = data["expires_at"]
        if expires_str.endswith("Z"):
            expires_str = expires_str[:-1] + "+00:00"
        expires_at = datetime.fromisoformat(expires_str)

        # Make expires_at offset-naive for comparison
        if expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)

        expected = datetime.utcnow() + timedelta(days=7)

        # Within 5 minutes of expected (test takes ~3 min due to archive timeouts)
        assert abs((expires_at - expected).total_seconds()) < 300


@pytest.mark.asyncio
async def test_pin_clears_expiry():
    """Pinning a bookmark should clear its expiry"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post("/bookmarks", json={"url": "https://example.com/pin-expiry"})
        data = create_resp.json()
        bookmark_id = data["id"]

        # Initially has expiry
        assert data["expires_at"] is not None

        # Pin it
        response = await client.patch(f"/bookmarks/{bookmark_id}/pin", json={"pinned": True})
        assert response.status_code == 200
        assert response.json()["expires_at"] is None


@pytest.mark.asyncio
async def test_toggle_thesis_clears_expiry():
    """Marking as thesis should clear expiry"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post("/bookmarks", json={"url": "https://example.com/thesis-expiry"})
        data = create_resp.json()
        bookmark_id = data["id"]

        # Initially has expiry (not detected as thesis)
        assert data["expires_at"] is not None

        # Mark as thesis
        response = await client.patch(f"/bookmarks/{bookmark_id}/thesis", json={"is_thesis": True})
        assert response.status_code == 200
        assert response.json()["expires_at"] is None
        assert response.json()["is_thesis"] is True


@pytest.mark.asyncio
async def test_list_bookmarks_by_view():
    """Test view filter parameter"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create regular inbox bookmark
        inbox_resp = await client.post("/bookmarks", json={"url": "https://example.com/inbox-item-view"})
        inbox_id = inbox_resp.json()["id"]

        # Create and mark as thesis
        thesis_resp = await client.post("/bookmarks", json={"url": "https://example.com/thesis-item-view"})
        thesis_id = thesis_resp.json()["id"]
        await client.patch(f"/bookmarks/{thesis_id}/thesis", json={"is_thesis": True})

        # Create and pin
        pin_resp = await client.post("/bookmarks", json={"url": "https://example.com/pinned-item-view"})
        pin_id = pin_resp.json()["id"]
        await client.patch(f"/bookmarks/{pin_id}/pin", json={"pinned": True})

        # Test inbox view (excludes thesis and pinned)
        inbox_list = await client.get("/bookmarks?view=inbox")
        inbox_urls = [b["url"] for b in inbox_list.json()]
        assert "https://example.com/inbox-item-view" in inbox_urls or "https://example.com/inbox-item-view/" in inbox_urls
        # Thesis and pinned should not be in inbox view
        assert not any("thesis-item-view" in url for url in inbox_urls)
        assert not any("pinned-item-view" in url for url in inbox_urls)

        # Test thesis view
        thesis_list = await client.get("/bookmarks?view=thesis")
        thesis_urls = [b["url"] for b in thesis_list.json()]
        assert any("thesis-item-view" in url for url in thesis_urls)

        # Test pins view
        pins_list = await client.get("/bookmarks?view=pins")
        pins_urls = [b["url"] for b in pins_list.json()]
        assert any("pinned-item-view" in url for url in pins_urls)


@pytest.mark.asyncio
async def test_export_bookmark():
    """Test export endpoint returns full bookmark data"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post("/bookmarks", json={"url": "https://example.com/export-test"})
        bookmark_id = create_resp.json()["id"]

        response = await client.get(f"/bookmarks/{bookmark_id}/export")
        assert response.status_code == 200
        data = response.json()

        assert "url" in data
        assert "title" in data
        assert "description" in data
        assert "content" in data
        assert "video_id" in data


@pytest.mark.asyncio
async def test_expiring_bookmarks():
    """Test endpoint to list bookmarks expiring soon"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create a bookmark (will have 7-day expiry)
        await client.post("/bookmarks", json={"url": "https://example.com/expiring-soon"})

        response = await client.get("/bookmarks/expiring")
        assert response.status_code == 200
        # Should return list (may be empty if no bookmarks expiring within 24h)
        assert isinstance(response.json(), list)
