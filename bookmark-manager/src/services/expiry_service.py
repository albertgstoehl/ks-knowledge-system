from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, func
from src.models import Bookmark, FeedItem
import logging

logger = logging.getLogger(__name__)


async def expire_old_bookmarks(session: AsyncSession) -> int:
    """Delete bookmarks past their expiry date. Returns count deleted."""
    now = datetime.utcnow()

    # Count before delete
    count_query = select(func.count()).select_from(Bookmark).where(
        Bookmark.expires_at != None,
        Bookmark.expires_at < now
    )
    result = await session.execute(count_query)
    count = result.scalar()

    if count > 0:
        await session.execute(
            delete(Bookmark).where(
                Bookmark.expires_at != None,
                Bookmark.expires_at < now
            )
        )
        await session.commit()
        logger.info(f"Expired {count} bookmarks")

    return count


async def expire_old_feed_items(session: AsyncSession) -> int:
    """Delete feed items older than 7 days. Returns count deleted."""
    cutoff = datetime.utcnow() - timedelta(days=7)

    count_query = select(func.count()).select_from(FeedItem).where(
        FeedItem.published_at < cutoff
    )
    result = await session.execute(count_query)
    count = result.scalar()

    if count > 0:
        await session.execute(
            delete(FeedItem).where(FeedItem.published_at < cutoff)
        )
        await session.commit()
        logger.info(f"Expired {count} feed items")

    return count
