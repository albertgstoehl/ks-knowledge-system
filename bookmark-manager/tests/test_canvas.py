import pytest
import httpx
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from src.models import Bookmark
from src import database
from sqlalchemy import delete
from src.main import app


@pytest.fixture(scope="function", autouse=True)
async def clean_db():
    """Clean database between tests"""
    async with database.async_session_maker() as session:
        await session.execute(delete(Bookmark))
        await session.commit()
    yield


@pytest.fixture
async def test_bookmark():
    """Create a test bookmark"""
    async with database.async_session_maker() as session:
        bookmark = Bookmark(
            url="https://example.com/article",
            title="Test Article",
            content="This is test content for selection"
        )
        session.add(bookmark)
        await session.commit()
        await session.refresh(bookmark)
        return bookmark


@pytest.mark.asyncio
async def test_push_quote_to_canvas(test_bookmark):
    """Test pushing a quote to Canvas"""

    with patch('src.routers.canvas.httpx.AsyncClient') as mock_client_class:
        # Setup mock
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/canvas/quotes",
                json={
                    "bookmark_id": test_bookmark.id,
                    "quote": "Test quote from source"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


@pytest.mark.asyncio
async def test_push_quote_bookmark_not_found():
    """Test pushing quote for non-existent bookmark"""

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/canvas/quotes",
            json={
                "bookmark_id": 99999,
                "quote": "Test quote"
            }
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_push_quote_canvas_unavailable(test_bookmark):
    """Test handling when Canvas is unavailable"""

    with patch('src.routers.canvas.httpx.AsyncClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(
            side_effect=httpx.RequestError("Connection refused")
        )
        mock_client_class.return_value = mock_client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/canvas/quotes",
                json={
                    "bookmark_id": test_bookmark.id,
                    "quote": "Test quote"
                }
            )

            assert response.status_code == 503
