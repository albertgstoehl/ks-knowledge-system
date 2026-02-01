"""Tests for bookmarks gateway routes."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_create_bookmark_calls_service(tmp_path):
    """create_bookmark should call bookmark-manager service."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "bm_rate.db")
    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "bm_audit.db")

    from shared.gateway.registry import clear_registry

    clear_registry()

    from gateway.routes import bookmarks

    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "id": 1,
        "url": "https://example.com",
        "title": "Example",
        "summary": None,
        "created_at": "2026-02-01T12:00:00",
    }
    mock_response.raise_for_status = AsyncMock()

    with patch("gateway.routes.bookmarks.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value = (
            mock_response
        )

        result = await bookmarks.create_bookmark(
            bookmarks.BookmarkCreateRequest(url="https://example.com")
        )

        assert result.id == 1
        assert result.url == "https://example.com"


@pytest.mark.asyncio
async def test_list_bookmarks_calls_service(tmp_path):
    """list_bookmarks should call bookmark-manager service."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "bm_rate2.db")
    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "bm_audit2.db")

    from shared.gateway.registry import clear_registry

    clear_registry()

    from gateway.routes import bookmarks

    mock_response = AsyncMock()
    mock_response.json.return_value = [
        {
            "id": 1,
            "url": "https://a.com",
            "title": "A",
            "summary": None,
            "created_at": "2026-02-01T12:00:00",
        },
        {
            "id": 2,
            "url": "https://b.com",
            "title": "B",
            "summary": None,
            "created_at": "2026-02-01T11:00:00",
        },
    ]
    mock_response.raise_for_status = AsyncMock()

    with patch("gateway.routes.bookmarks.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = (
            mock_response
        )

        result = await bookmarks.list_bookmarks(limit=20)

        assert len(result) == 2
        assert result[0].id == 1
