"""Tests for audit logging."""

import pytest


@pytest.mark.asyncio
async def test_log_request_creates_entry(tmp_path):
    """log_request should create audit log entry."""
    import os

    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "test_audit.db")

    from shared.gateway.audit import init_audit_db, log_request, get_recent_logs

    await init_audit_db()

    await log_request(
        endpoint="/api/test",
        method="POST",
        client_ip="127.0.0.1",
        params={"key": "value"},
        status_code=200,
    )

    logs = await get_recent_logs(limit=10)
    assert len(logs) == 1
    assert logs[0]["endpoint"] == "/api/test"
    assert logs[0]["method"] == "POST"
    assert logs[0]["client_ip"] == "127.0.0.1"
    assert logs[0]["status_code"] == 200


@pytest.mark.asyncio
async def test_log_request_with_error(tmp_path):
    """log_request should store error message."""
    import os

    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "test_audit2.db")

    from shared.gateway.audit import init_audit_db, log_request, get_recent_logs

    await init_audit_db()

    await log_request(
        endpoint="/api/fail",
        method="GET",
        client_ip="10.0.0.1",
        params={},
        status_code=500,
        error="Internal server error",
    )

    logs = await get_recent_logs(limit=10)
    assert logs[0]["error"] == "Internal server error"
    assert logs[0]["status_code"] == 500


@pytest.mark.asyncio
async def test_get_recent_logs_ordered_by_newest(tmp_path):
    """get_recent_logs should return newest first."""
    import os

    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "test_audit3.db")

    from shared.gateway.audit import init_audit_db, log_request, get_recent_logs

    await init_audit_db()

    await log_request("/first", "GET", "127.0.0.1", {}, 200)
    await log_request("/second", "GET", "127.0.0.1", {}, 200)
    await log_request("/third", "GET", "127.0.0.1", {}, 200)

    logs = await get_recent_logs(limit=10)
    assert logs[0]["endpoint"] == "/third"
    assert logs[2]["endpoint"] == "/first"
