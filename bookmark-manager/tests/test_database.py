import pytest
from src import database
from src.models import Bookmark, BookmarkState
from sqlalchemy import select
import os

@pytest.mark.asyncio
async def test_database_initialization():
    """Test database initializes successfully"""
    test_db = "test_bookmarks.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    try:
        await database.init_db(f"sqlite:///{test_db}")

        # Should create database file
        assert os.path.exists(test_db)
    finally:
        # Cleanup
        if os.path.exists(test_db):
            os.remove(test_db)

@pytest.mark.asyncio
async def test_bookmark_creation():
    """Test creating a bookmark"""
    test_db = "test_bookmarks.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    try:
        await database.init_db(f"sqlite+aiosqlite:///{test_db}")

        async with database.async_session_maker() as session:
            bookmark = Bookmark(
                url="https://example.com",
                title="Example",
                state=BookmarkState.inbox
            )
            session.add(bookmark)
            await session.commit()

            result = await session.execute(select(Bookmark))
            saved_bookmark = result.scalar_one()

            assert saved_bookmark.url == "https://example.com"
            assert saved_bookmark.state == BookmarkState.inbox
    finally:
        if os.path.exists(test_db):
            os.remove(test_db)


@pytest.mark.asyncio
async def test_bookmark_has_expires_at_column():
    """Test that bookmark model has expires_at column"""
    from datetime import datetime, timedelta

    test_db = "test_bookmarks.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    try:
        await database.init_db(f"sqlite+aiosqlite:///{test_db}")

        async with database.async_session_maker() as session:
            expires = datetime.utcnow() + timedelta(days=7)
            bookmark = Bookmark(
                url="https://example.com/expiry-test",
                state=BookmarkState.inbox,
                expires_at=expires
            )
            session.add(bookmark)
            await session.commit()
            await session.refresh(bookmark)

            assert bookmark.expires_at is not None
            assert abs((bookmark.expires_at - expires).total_seconds()) < 1
    finally:
        if os.path.exists(test_db):
            os.remove(test_db)
