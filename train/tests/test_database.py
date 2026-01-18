import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import init_db, get_db


def test_init_db_creates_schema():
    asyncio.run(init_db("sqlite+aiosqlite:///:memory:"))
    session_generator = get_db()
    session = asyncio.run(session_generator.__anext__())
    assert isinstance(session, AsyncSession)
    asyncio.run(session.close())
