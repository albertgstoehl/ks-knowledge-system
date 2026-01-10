"""Balance service API smoke tests."""
import pytest
import httpx


@pytest.mark.asyncio
async def test_health_check(balance_url):
    """Verify Balance service is healthy."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{balance_url}/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_session_workflow(balance_url):
    """Verify basic session workflow (start, abandon)."""
    async with httpx.AsyncClient() as client:
        # Check status endpoint works
        response = await client.get(f"{balance_url}/api/status")
        assert response.status_code == 200
        status = response.json()
        assert "mode" in status
        
        # Test session start endpoint exists (may fail validation, which is ok)
        # Just verify the endpoint is reachable and returns proper error codes
        response = await client.post(
            f"{balance_url}/api/sessions/start",
            json={"type": "expected", "priority_id": 999}  # Invalid priority
        )
        # Should either succeed (200) or reject validation (400), but not 500 or 404
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        
        # Test abandon endpoint exists
        response = await client.post(f"{balance_url}/api/sessions/abandon")
        # May succeed or fail depending on if session active, but endpoint should exist
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"


@pytest.mark.asyncio
async def test_log_meditation(balance_url):
    """Verify meditation logging works."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{balance_url}/api/meditation",
            json={"duration_minutes": 10}
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_log_exercise(balance_url):
    """Verify exercise logging works."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{balance_url}/api/exercise",
            json={"type": "cardio", "duration_minutes": 30, "intensity": "medium"}
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_stats(balance_url):
    """Verify stats endpoint returns data."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{balance_url}/api/stats/today")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data or "pomodoros_completed" in data
