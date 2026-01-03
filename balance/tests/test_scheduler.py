# balance/tests/test_scheduler.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import os

assert "DATABASE_URL" in os.environ, "Run tests with DATABASE_URL=./data/test.db"

from src.database import init_db, get_db
from src.scheduler import check_expired_sessions


@pytest.fixture(autouse=True)
async def setup_test():
    """Initialize database and cleanup between tests."""
    await init_db()
    async with get_db() as db:
        await db.execute("DELETE FROM sessions")
        await db.execute("UPDATE app_state SET break_until = NULL WHERE id = 1")
        await db.commit()
    yield


@pytest.mark.asyncio
async def test_expired_youtube_session_triggers_block():
    """Expired YouTube sessions should trigger NextDNS block and set break."""
    async with get_db() as db:
        past_time = datetime.now() - timedelta(minutes=5)
        await db.execute(
            """INSERT INTO sessions (type, intention, started_at, duration_minutes)
               VALUES (?, ?, ?, ?)""",
            ("youtube", "test", past_time.isoformat(), 1)
        )
        await db.commit()

    with patch("src.services.nextdns.get_nextdns_service") as mock_nextdns:
        mock_service = AsyncMock()
        mock_nextdns.return_value = mock_service

        await check_expired_sessions()

        mock_service.block_youtube.assert_called_once()

    # Verify break was set
    async with get_db() as db:
        cursor = await db.execute("SELECT break_until FROM app_state WHERE id = 1")
        row = await cursor.fetchone()
        assert row["break_until"] is not None


@pytest.mark.asyncio
async def test_expired_focus_session_sets_break():
    """Expired focus sessions should set break even without client callback."""
    async with get_db() as db:
        # Create expired expected session (25 min default, started 30 min ago)
        past_time = datetime.now() - timedelta(minutes=30)
        await db.execute(
            """INSERT INTO sessions (type, intention, started_at)
               VALUES (?, ?, ?)""",
            ("expected", "coding task", past_time.isoformat())
        )
        # Clear any existing break
        await db.execute("UPDATE app_state SET break_until = NULL WHERE id = 1")
        await db.commit()

    await check_expired_sessions()

    # Verify session was ended and break was set
    async with get_db() as db:
        cursor = await db.execute("SELECT ended_at FROM sessions WHERE type = 'expected'")
        row = await cursor.fetchone()
        assert row["ended_at"] is not None

        cursor = await db.execute("SELECT break_until FROM app_state WHERE id = 1")
        row = await cursor.fetchone()
        assert row["break_until"] is not None
