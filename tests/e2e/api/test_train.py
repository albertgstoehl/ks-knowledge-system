import pytest
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
