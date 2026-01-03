import pytest
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_expire_old_bookmarks():
    """Test that expired bookmarks are deleted"""
    from src import database
    from src.models import Bookmark, BookmarkState
    from src.services.expiry_service import expire_old_bookmarks
    from sqlalchemy import select, delete

    # Clean up first
    async with database.async_session_maker() as session:
        await session.execute(delete(Bookmark))
        await session.commit()

    async with database.async_session_maker() as session:
        # Create expired bookmark
        expired = Bookmark(
            url="https://example.com/expired",
            state=BookmarkState.inbox,
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        # Create non-expired bookmark
        valid = Bookmark(
            url="https://example.com/valid",
            state=BookmarkState.inbox,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        session.add_all([expired, valid])
        await session.commit()

        expired_id = expired.id
        valid_id = valid.id

        # Run expiry
        deleted_count = await expire_old_bookmarks(session)

        assert deleted_count == 1

        # Verify expired is gone
        result = await session.get(Bookmark, expired_id)
        assert result is None

        # Verify valid still exists
        result = await session.get(Bookmark, valid_id)
        assert result is not None
