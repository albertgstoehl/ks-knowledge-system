import pytest
import httpx


@pytest.mark.asyncio
async def test_start_session_with_plan_id(train_url):
    async with httpx.AsyncClient() as client:
        plan_resp = await client.get(f"{train_url}/api/plan/current")
        if plan_resp.status_code == 404:
            register_resp = await client.post(
                f"{train_url}/api/plan/register",
                json={"title": "Test Plan", "markdown": "# Test Plan"},
            )
            assert register_resp.status_code == 200
            plan_id = register_resp.json()["id"]
        else:
            plan_id = plan_resp.json()["id"]

        resp = await client.post(
            f"{train_url}/api/sessions/start",
            json={"template_key": "A", "plan_id": plan_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_id"] == plan_id


@pytest.mark.asyncio
async def test_list_sessions(train_url):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{train_url}/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_sessions_with_since_filter(train_url):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{train_url}/api/sessions",
            params={"since": "2020-01-01"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_sets(train_url):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{train_url}/api/sets")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_sets_with_session_filter(train_url):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{train_url}/api/sets",
            params={"session_id": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_context(train_url):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{train_url}/api/context")
        assert resp.status_code == 200
        data = resp.json()
        assert "plan" in data
        assert "sessions" in data
        assert "sets" in data
        assert "summary" in data


@pytest.mark.asyncio
async def test_context_summary_has_volume(train_url):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{train_url}/api/context")
        assert resp.status_code == 200
        data = resp.json()
        summary = data["summary"]
        assert "weeks_on_plan" in summary
        assert "total_sessions" in summary
        assert "volume_by_muscle" in summary


@pytest.mark.asyncio
async def test_list_exercises(train_url):
    """Test listing all exercises."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{train_url}/api/exercises")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_exercises_include_last_set(train_url):
    """Test that exercises endpoint includes last set data."""
    async with httpx.AsyncClient() as client:
        # First log a set
        session_resp = await client.post(
            f"{train_url}/api/sessions/start",
            json={"template_key": "Test"},
        )
        assert session_resp.status_code == 200
        session_id = session_resp.json()["id"]

        await client.post(
            f"{train_url}/api/sets",
            json={
                "session_id": session_id,
                "exercise_name": "Test Exercise",
                "weight": 50,
                "reps": 10,
                "rir": 2,
            },
        )

        # Check exercises endpoint
        resp = await client.get(f"{train_url}/api/exercises")
        assert resp.status_code == 200
        data = resp.json()

        exercise = next((e for e in data if e["name"] == "Test Exercise"), None)
        assert exercise is not None
        assert exercise["last_set"]["weight"] == 50
        assert exercise["last_set"]["reps"] == 10


@pytest.mark.asyncio
async def test_list_sets_with_exercise_filter(train_url):
    """Test filtering sets by exercise name."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{train_url}/api/sets",
            params={"exercise_name": "Bench Press"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
