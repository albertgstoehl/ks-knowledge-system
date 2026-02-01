"""Tests for kasten gateway routes."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_get_note_calls_service(tmp_path):
    """get_note should call kasten service."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "kas_rate.db")
    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "kas_audit.db")

    from shared.gateway.registry import clear_registry

    clear_registry()

    from gateway.routes import kasten

    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "id": "0001a",
        "title": "Test Note",
        "content": "Note content",
        "links": ["0002b"],
    }
    mock_response.raise_for_status = AsyncMock()

    with patch("gateway.routes.kasten.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = (
            mock_response
        )

        result = await kasten.get_note(note_id="0001a")

        assert result.id == "0001a"
        assert result.title == "Test Note"


@pytest.mark.asyncio
async def test_get_entry_points_calls_service(tmp_path):
    """get_entry_points should call kasten service."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "kas_rate2.db")
    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "kas_audit2.db")

    from shared.gateway.registry import clear_registry

    clear_registry()

    from gateway.routes import kasten

    mock_response = AsyncMock()
    mock_response.json.return_value = [
        {"id": "0001a", "title": "Entry 1"},
        {"id": "0002b", "title": "Entry 2"},
    ]
    mock_response.raise_for_status = AsyncMock()

    with patch("gateway.routes.kasten.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = (
            mock_response
        )

        result = await kasten.get_entry_points()

        assert len(result) == 2
        assert result[0]["id"] == "0001a"
