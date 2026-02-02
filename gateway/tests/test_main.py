"""Tests for main gateway app."""

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(tmp_path):
    """Health endpoint should return ok."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "main_rate.db")
    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "main_audit.db")

    from shared.gateway.registry import clear_registry

    clear_registry()

    from httpx import AsyncClient, ASGITransport
    from gateway.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_skill_endpoint(tmp_path):
    """Skill endpoint should return markdown."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "main_rate2.db")
    os.environ["GATEWAY_AUDIT_DB_PATH"] = str(tmp_path / "main_audit2.db")

    from shared.gateway.registry import clear_registry

    clear_registry()

    from httpx import AsyncClient, ASGITransport
    from gateway.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/skill")
        assert r.status_code == 200
        assert "knowledge-gateway" in r.text
        assert "---" in r.text
