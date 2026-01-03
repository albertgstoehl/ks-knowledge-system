import pytest
from httpx import AsyncClient, ASGITransport
import os

# Verify DATABASE_URL is set
assert "DATABASE_URL" in os.environ, "Run tests with DATABASE_URL=./data/test.db"

from src.database import init_db, get_db
from src.main import app


_db_initialized = False


@pytest.fixture(autouse=True)
async def setup_test():
    """Initialize database and cleanup between tests."""
    global _db_initialized
    if not _db_initialized:
        await init_db()
        _db_initialized = True

    # Clean up data from previous tests
    async with get_db() as db:
        await db.execute("DELETE FROM session_analyses")
        await db.execute("DELETE FROM sessions")
        await db.execute("DELETE FROM priorities")
        await db.execute("UPDATE app_state SET break_until = NULL WHERE id = 1")
        # Set evening cutoff to 23:59 to allow tests to run any time
        await db.execute("UPDATE settings SET evening_cutoff = '23:59' WHERE id = 1")
        await db.commit()
    yield


async def test_start_session():
    """Test starting a new session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions/start", json={
            "type": "expected",
            "intention": "Fix bug"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "expected"
        assert data["intention"] == "Fix bug"
        assert "id" in data
        assert "started_at" in data


async def test_end_session():
    """Test ending a session (questionnaire submission)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start session first
        start_response = await client.post("/api/sessions/start", json={
            "type": "personal",
            "intention": "Research"
        })
        assert start_response.status_code == 200
        session_id = start_response.json()["id"]

        # Call timer-complete to start break (simulates timer ending)
        timer_response = await client.post("/api/sessions/timer-complete")
        assert timer_response.status_code == 200

        # Submit questionnaire
        response = await client.post("/api/sessions/end", json={
            "distractions": "none",
            "did_the_thing": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["session_id"] == session_id


async def test_break_check_not_on_break():
    """Test break check when not on break."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/check")
        assert response.status_code == 200
        data = response.json()
        assert data["on_break"] is False
        assert data["remaining_seconds"] == 0


async def test_break_check_on_break():
    """Test break check when on break."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start a session and call timer-complete to trigger break
        await client.post("/api/sessions/start", json={"type": "expected"})
        await client.post("/api/sessions/timer-complete")
        await client.post("/api/sessions/end", json={
            "distractions": "none",
            "did_the_thing": True
        })

        # Check if on break
        response = await client.get("/api/check")
        assert response.status_code == 200
        data = response.json()
        assert data["on_break"] is True
        assert data["remaining_seconds"] > 0


async def test_session_active_no_session():
    """Test /api/session/active when no session is active."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/session/active")
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False
        assert data["reason"] == "no_session"


async def test_session_active_with_session():
    """Test /api/session/active when a session is active."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start a session
        await client.post("/api/sessions/start", json={
            "type": "expected",
            "intention": "Test task"
        })

        response = await client.get("/api/session/active")
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        assert data["session"]["type"] == "expected"
        assert data["session"]["intention"] == "Test task"
        assert data["session"]["remaining_seconds"] > 0


async def test_session_active_on_break():
    """Test /api/session/active when on break."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start a session and call timer-complete to trigger break
        await client.post("/api/sessions/start", json={"type": "expected"})
        await client.post("/api/sessions/timer-complete")
        await client.post("/api/sessions/end", json={
            "distractions": "none",
            "did_the_thing": True
        })

        response = await client.get("/api/session/active")
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False
        assert data["reason"] == "on_break"
        assert data["break_remaining"] > 0


async def test_quick_start_success():
    """Test quick-starting a session from terminal."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/session/quick-start", json={
            "type": "personal",
            "intention": "Fix bug"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["session_id"] is not None

        # Verify session was created
        current = await client.get("/api/sessions/current")
        assert current.json()["active"] is True
        assert current.json()["session"]["intention"] == "Fix bug"


async def test_quick_start_on_break():
    """Test quick-start fails when on break."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a break via timer-complete
        await client.post("/api/sessions/start", json={"type": "expected"})
        await client.post("/api/sessions/timer-complete")
        await client.post("/api/sessions/end", json={
            "distractions": "none",
            "did_the_thing": True
        })

        # Try to quick-start
        response = await client.post("/api/session/quick-start", json={
            "type": "personal",
            "intention": "Another task"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["reason"] == "on_break"
        assert data["remaining"] > 0


async def test_quick_start_already_in_session():
    """Test quick-start fails when already in session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start a session
        await client.post("/api/sessions/start", json={"type": "expected"})

        # Try to quick-start another
        response = await client.post("/api/session/quick-start", json={
            "type": "personal",
            "intention": "Another task"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["reason"] == "session_active"


async def test_mark_claude_used():
    """Test marking a session as using Claude."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start a session
        await client.post("/api/sessions/start", json={
            "type": "expected",
            "intention": "Test"
        })

        # Mark as using Claude
        response = await client.post("/api/session/mark-claude-used")
        assert response.status_code == 200
        data = response.json()
        assert data["marked"] is True

        # Call again - should still succeed (idempotent)
        response2 = await client.post("/api/session/mark-claude-used")
        assert response2.status_code == 200
        assert response2.json()["marked"] is True


async def test_mark_claude_used_no_session():
    """Test mark-claude-used fails when no session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/session/mark-claude-used")
        assert response.status_code == 200
        data = response.json()
        assert data["marked"] is False


async def test_start_session_with_priority():
    """Test starting a session with a priority."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a priority first
        priority_resp = await client.post("/api/priorities", json={"name": "Thesis"})
        priority_id = priority_resp.json()["id"]

        # Start session with priority
        response = await client.post("/api/sessions/start", json={
            "type": "expected",
            "intention": "Write chapter 1",
            "priority_id": priority_id
        })
        assert response.status_code == 200
        assert response.json()["priority_id"] == priority_id


async def test_stats_drift():
    """Test drift stats endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/stats/drift")
        assert response.status_code == 200
        data = response.json()
        assert "biggest_drift" in data
        assert "breakdown" in data


async def test_get_unanalyzed_sessions():
    """Test getting sessions that need analysis."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/sessions/unanalyzed")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


async def test_store_session_analysis():
    """Test storing analysis results for a session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a session first
        await client.post("/api/sessions/start", json={
            "type": "expected",
            "intention": "Test intention"
        })
        # Mark it as using claude and end it
        await client.post("/api/session/mark-claude-used")
        await client.post("/api/sessions/timer-complete")
        await client.post("/api/sessions/end", json={
            "distractions": "none",
            "did_the_thing": True
        })

        # Get the session ID
        sessions = await client.get("/api/sessions/unanalyzed")
        session_id = sessions.json()[0]["id"]

        # Store analysis
        response = await client.post(f"/api/sessions/{session_id}/analysis", json={
            "intention_alignment": "aligned",
            "alignment_detail": "Work matched intention",
            "scope_behavior": "focused",
            "scope_detail": None,
            "project_switches": 0,
            "tool_appropriate_count": 5,
            "tool_questionable_count": 1,
            "tool_questionable_examples": ["prompt 3: simple file read"],
            "red_flags": [],
            "one_line_summary": "Focused session on intended task",
            "severity": "none",
            "projects_used": ["knowledge-system"],
            "prompt_count": 6
        })
        assert response.status_code == 200
        assert response.json()["id"] is not None


async def test_get_effectiveness_stats():
    """Test getting effectiveness statistics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/stats/effectiveness")
        assert response.status_code == 200
        data = response.json()
        assert "total_analyzed" in data
        assert "alignment_breakdown" in data


async def test_start_youtube_session():
    """YouTube sessions require duration_minutes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions/start", json={
            "type": "youtube",
            "intention": "exploring music production",
            "duration_minutes": 30
        })
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "youtube"
        assert data["duration_minutes"] == 30


async def test_start_youtube_session_without_duration_fails():
    """YouTube sessions must have duration."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions/start", json={
            "type": "youtube",
            "intention": "exploring"
        })
        assert response.status_code == 400


async def test_start_youtube_session_invalid_duration_fails():
    """YouTube sessions must have valid duration (15, 30, 45, 60)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions/start", json={
            "type": "youtube",
            "intention": "exploring",
            "duration_minutes": 25  # Invalid - not in allowed list
        })
        assert response.status_code == 400
