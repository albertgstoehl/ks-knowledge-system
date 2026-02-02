"""Tests for canvas gateway routes."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_push_quote_calls_service(tmp_path):
    """push_quote should call canvas service."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "cv_rate.db")
    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "cv_audit.db")

    from shared.gateway.registry import clear_registry

    clear_registry()

    from gateway.routes import canvas

    mock_response = AsyncMock()
    mock_response.json.return_value = {"id": 1, "content": "Test quote"}
    mock_response.raise_for_status = AsyncMock()

    with patch("gateway.routes.canvas.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value = (
            mock_response
        )

        result = await canvas.push_quote(canvas.QuotePushRequest(content="Test quote"))

        assert result["id"] == 1


@pytest.mark.asyncio
async def test_get_draft_calls_service(tmp_path):
    """get_draft should call canvas service."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "cv_rate2.db")
    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "cv_audit2.db")

    from shared.gateway.registry import clear_registry

    clear_registry()

    from gateway.routes import canvas

    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "content": "Draft content",
        "updated_at": "2026-02-01T12:00:00",
    }
    mock_response.raise_for_status = AsyncMock()

    with patch("gateway.routes.canvas.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = (
            mock_response
        )

        result = await canvas.get_draft()

        assert result.content == "Draft content"
