# kasten/tests/test_database.py
import pytest
from sqlalchemy import text
from src.database import init_db, get_db

@pytest.mark.asyncio
async def test_init_db_creates_tables():
    await init_db("sqlite+aiosqlite:///:memory:")
    async for session in get_db():
        result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result.fetchall()]
        assert "notes" in tables
        assert "links" in tables
        break

@pytest.mark.asyncio
async def test_note_model():
    await init_db("sqlite+aiosqlite:///:memory:")
    from src.models import Note
    async for session in get_db():
        note = Note(id="1219a", title="Test note", file_path="1219a.md")
        session.add(note)
        await session.commit()
        await session.refresh(note)
        assert note.id == "1219a"
        assert note.title == "Test note"
        break

@pytest.mark.asyncio
async def test_link_model():
    await init_db("sqlite+aiosqlite:///:memory:")
    from src.models import Note, Link
    async for session in get_db():
        note1 = Note(id="1219a", title="Note A", file_path="1219a.md")
        note2 = Note(id="1219b", title="Note B", file_path="1219b.md")
        session.add_all([note1, note2])
        await session.commit()

        link = Link(from_note_id="1219a", to_note_id="1219b")
        session.add(link)
        await session.commit()
        assert link.id is not None
        break


@pytest.mark.asyncio
async def test_source_model():
    """Test that Source model exists and can be created"""
    from src.models import Source
    from src.database import init_db, get_db

    await init_db("sqlite+aiosqlite:///:memory:")

    async for session in get_db():
        source = Source(
            url="https://example.com/article",
            title="Test Article",
            description="A test description"
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)

        assert source.id is not None
        assert source.url == "https://example.com/article"
        assert source.archived_at is not None
        break


@pytest.mark.asyncio
async def test_sources_table_created():
    """Test that sources table is created on init"""
    from src.database import init_db
    from sqlalchemy import inspect
    import src.database

    await init_db("sqlite+aiosqlite:///:memory:")

    async with src.database.engine.connect() as conn:
        def get_tables(connection):
            inspector = inspect(connection)
            return inspector.get_table_names()

        tables = await conn.run_sync(get_tables)
        assert "sources" in tables
        assert "notes" in tables
