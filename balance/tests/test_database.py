import pytest

from src.database import init_db, get_db


@pytest.fixture
async def test_db(tmp_path):
    """Initialize fresh database for each test."""
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    return db_path


@pytest.mark.asyncio
async def test_priorities_table_exists(test_db):
    """Test that priorities table is created during init_db."""
    async with get_db(test_db) as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='priorities'"
        )
        result = await cursor.fetchone()
        assert result is not None
        assert result[0] == "priorities"


@pytest.mark.asyncio
async def test_priorities_table_schema(test_db):
    """Test that priorities table has correct columns."""
    async with get_db(test_db) as db:
        cursor = await db.execute("PRAGMA table_info(priorities)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        assert "id" in column_names
        assert "name" in column_names
        assert "rank" in column_names
        assert "created_at" in column_names
        assert "archived_at" in column_names


@pytest.mark.asyncio
async def test_sessions_has_priority_id_column(test_db):
    """Test that sessions table has priority_id column for linking to priorities."""
    async with get_db(test_db) as db:
        cursor = await db.execute("PRAGMA table_info(sessions)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        assert "priority_id" in column_names
