from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


async def expire_old_bookmarks(session: AsyncSession) -> int:
    """Delete bookmarks past their expiry date. Returns count deleted."""
    # Use ISO format string for SQLite text comparison compatibility
    # SQLite stores dates as TEXT, so we need consistent format
    now_iso = datetime.utcnow().isoformat()

    # Count before delete using raw SQL for reliable text comparison
    count_result = await session.execute(
        text("SELECT COUNT(*) FROM bookmarks WHERE expires_at IS NOT NULL AND expires_at < :now"),
        {"now": now_iso}
    )
    count = count_result.scalar()

    if count > 0:
        await session.execute(
            text("DELETE FROM bookmarks WHERE expires_at IS NOT NULL AND expires_at < :now"),
            {"now": now_iso}
        )
        await session.commit()
        # Expire session cache since raw SQL bypasses ORM identity map
        session.expire_all()
        logger.info(f"Expired {count} bookmarks")

    return count


async def expire_old_feed_items(session: AsyncSession) -> int:
    """Delete feed items older than 7 days. Returns count deleted."""
    # Use ISO format string for SQLite text comparison compatibility
    cutoff_iso = (datetime.utcnow() - timedelta(days=7)).isoformat()

    count_result = await session.execute(
        text("SELECT COUNT(*) FROM feed_items WHERE published_at IS NOT NULL AND published_at < :cutoff"),
        {"cutoff": cutoff_iso}
    )
    count = count_result.scalar()

    if count > 0:
        await session.execute(
            text("DELETE FROM feed_items WHERE published_at IS NOT NULL AND published_at < :cutoff"),
            {"cutoff": cutoff_iso}
        )
        await session.commit()
        session.expire_all()
        logger.info(f"Expired {count} feed items")

    return count
