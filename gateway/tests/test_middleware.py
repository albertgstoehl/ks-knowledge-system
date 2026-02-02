"""Tests for gateway middleware."""

import pytest


@pytest.mark.asyncio
async def test_middleware_applies_rate_limit(tmp_path):
    """Middleware should check rate limit for gateway endpoints."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "mw_rate.db")
    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "mw_audit.db")

    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport

    from shared.gateway import gateway_endpoint, init_ratelimit_db, init_audit_db
    from shared.gateway.registry import clear_registry
    from gateway.middleware import GatewayMiddleware

    clear_registry()
    await init_ratelimit_db()
    await init_audit_db()

    app = FastAPI()
    app.add_middleware(GatewayMiddleware)

    @gateway_endpoint(
        method="GET",
        path="/test",
        rate_limit="2/hour",
        description="Test",
    )
    async def test_endpoint():
        return {"ok": True}

    app.get("/test")(test_endpoint)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.get("/test")
        assert r1.status_code == 200

        r2 = await client.get("/test")
        assert r2.status_code == 200

        r3 = await client.get("/test")
        assert r3.status_code == 429


@pytest.mark.asyncio
async def test_middleware_logs_requests(tmp_path):
    """Middleware should audit log gateway requests."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "mw_rate2.db")
    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "mw_audit2.db")

    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport

    from shared.gateway import (
        gateway_endpoint,
        init_ratelimit_db,
        init_audit_db,
        get_recent_logs,
    )
    from shared.gateway.registry import clear_registry
    from gateway.middleware import GatewayMiddleware

    clear_registry()
    await init_ratelimit_db()
    await init_audit_db()

    app = FastAPI()
    app.add_middleware(GatewayMiddleware)

    @gateway_endpoint(
        method="POST",
        path="/logged",
        rate_limit="100/hour",
        description="Logged endpoint",
    )
    async def logged_endpoint():
        return {"logged": True}

    app.post("/logged")(logged_endpoint)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/logged")

    logs = await get_recent_logs(limit=10)
    assert len(logs) == 1
    assert logs[0]["endpoint"] == "/logged"
    assert logs[0]["method"] == "POST"
    assert logs[0]["status_code"] == 200


@pytest.mark.asyncio
async def test_middleware_skips_non_gateway_routes(tmp_path):
    """Middleware should pass through non-gateway routes unchanged."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "mw_rate3.db")
    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "mw_audit3.db")

    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport

    from shared.gateway import init_ratelimit_db, init_audit_db, get_recent_logs
    from shared.gateway.registry import clear_registry
    from gateway.middleware import GatewayMiddleware

    clear_registry()
    await init_ratelimit_db()
    await init_audit_db()

    app = FastAPI()
    app.add_middleware(GatewayMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200

    logs = await get_recent_logs(limit=10)
    assert len(logs) == 0
