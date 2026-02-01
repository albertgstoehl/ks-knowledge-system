"""Tests for balance gateway routes."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_start_session_calls_service(tmp_path):
    """start_session should call balance service."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "bal_rate.db")
    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "bal_audit.db")

    from shared.gateway.registry import clear_registry

    clear_registry()

    from gateway.routes import balance

    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "id": 1,
        "session_type": "expected",
        "started_at": "2026-02-01T12:00:00",
        "status": "active",
    }
    mock_response.raise_for_status = AsyncMock()

    with patch("gateway.routes.balance.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value = (
            mock_response
        )

        result = await balance.start_session(
            balance.SessionStartRequest(session_type="expected")
        )

        assert result.id == 1
        assert result.session_type == "expected"


@pytest.mark.asyncio
async def test_get_status_calls_service(tmp_path):
    """get_status should call balance service."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "bal_rate2.db")
    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "bal_audit2.db")

    from shared.gateway.registry import clear_registry

    clear_registry()

    from gateway.routes import balance

    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "status": "in_session",
        "session_type": "expected",
        "minutes_remaining": 15,
    }
    mock_response.raise_for_status = AsyncMock()

    with patch("gateway.routes.balance.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = (
            mock_response
        )

        result = await balance.get_status()

        assert result["status"] == "in_session"
