import pytest
from sqlalchemy import text
from src.database import init_db, get_db

@pytest.mark.asyncio
async def test_init_db_creates_tables():
    await init_db("sqlite+aiosqlite:///:memory:")
    async for session in get_db():
        result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result.fetchall()]
        assert "canvas_state" in tables
        break

@pytest.mark.asyncio
async def test_canvas_state_model():
    await init_db("sqlite+aiosqlite:///:memory:")
    from src.models import CanvasState
    async for session in get_db():
        state = CanvasState(content="test content")
        session.add(state)
        await session.commit()
        await session.refresh(state)
        assert state.id == 1
        assert state.content == "test content"
        assert state.updated_at is not None
        break

@pytest.mark.asyncio
async def test_workspace_note_model():
    await init_db("sqlite+aiosqlite:///:memory:")
    from src.models import WorkspaceNote
    async for session in get_db():
        note = WorkspaceNote(km_note_id="abc123", content="Note content", x=100.0, y=200.0)
        session.add(note)
        await session.commit()
        await session.refresh(note)
        assert note.id is not None
        assert note.km_note_id == "abc123"
        break

@pytest.mark.asyncio
async def test_workspace_connection_model():
    await init_db("sqlite+aiosqlite:///:memory:")
    from src.models import WorkspaceNote, WorkspaceConnection
    async for session in get_db():
        note1 = WorkspaceNote(km_note_id="a", content="A", x=0, y=0)
        note2 = WorkspaceNote(km_note_id="b", content="B", x=100, y=0)
        session.add_all([note1, note2])
        await session.commit()

        conn = WorkspaceConnection(from_note_id=note1.id, to_note_id=note2.id, label="therefore")
        session.add(conn)
        await session.commit()
        assert conn.id is not None
        assert conn.label == "therefore"
        break
