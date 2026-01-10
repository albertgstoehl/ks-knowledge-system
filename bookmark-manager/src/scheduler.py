# bookmark-manager/src/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

from src import database
from src.services.expiry_service import expire_old_bookmarks, expire_old_feed_items

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_expiry_jobs():
    """Run all expiry jobs."""
    try:
        if database.async_session_maker is None:
            logger.warning("Database not initialized, skipping expiry check")
            return
        async with database.async_session_maker() as session:
            bookmark_count = await expire_old_bookmarks(session)
            feed_count = await expire_old_feed_items(session)
            if bookmark_count > 0 or feed_count > 0:
                logger.info(f"Expiry job: {bookmark_count} bookmarks, {feed_count} feed items deleted")
    except Exception as e:
        logger.error(f"Error running expiry jobs: {e}")


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(
        run_expiry_jobs,
        IntervalTrigger(minutes=5),
        id="expiry_check",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started with expiry check (5m interval)")


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")
