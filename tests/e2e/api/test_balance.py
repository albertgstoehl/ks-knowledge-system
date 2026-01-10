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
        # Check status
        response = await client.get(f"{balance_url}/api/status")
        assert response.status_code == 200
        status = response.json()
        
        # If in break mode, skip session start (can't start during break)
        if status.get("mode") == "break":
            pytest.skip("System in break mode, cannot start session")
        
        # Create a priority first (fresh database might not have any)
        create_priority_response = await client.post(
            f"{balance_url}/api/priorities",
            json={"name": "Test Priority", "order": 1}
        )
        # Get the created priority ID
        priority_id = create_priority_response.json().get("id", 1)
        
        # Start a session
        response = await client.post(
            f"{balance_url}/api/sessions/start",
            json={"type": "expected", "priority_id": priority_id}
        )
        assert response.status_code == 200
        
        # Abandon session
        response = await client.post(f"{balance_url}/api/sessions/abandon")
        assert response.status_code == 200


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
