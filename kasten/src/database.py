# kasten/src/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from typing import AsyncGenerator
import os

class Base(DeclarativeBase):
    pass

engine = None
async_session_maker = None

async def init_db(database_url: str = None) -> None:
    global engine, async_session_maker

    if database_url is None:
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/kasten.db")

    if database_url.startswith("sqlite:///"):
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

    if database_url.startswith("sqlite+aiosqlite:///") and not database_url.endswith(":memory:"):
        db_path = database_url.replace("sqlite+aiosqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    engine = create_async_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    from src import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
