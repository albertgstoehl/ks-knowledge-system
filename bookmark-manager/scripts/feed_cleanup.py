#!/usr/bin/env python3
# scripts/feed_cleanup.py
"""Clean up expired feed items - run every hour via cron"""
import asyncio
import sys
from datetime import datetime, timedelta

sys.path.insert(0, '/app')

from src.database import init_db, get_db
from src.models import FeedItem
from sqlalchemy import delete


async def main():
    await init_db()

    async for session in get_db():
        cutoff = datetime.utcnow() - timedelta(hours=24)

        result = await session.execute(
            delete(FeedItem).where(FeedItem.fetched_at < cutoff)
        )
        await session.commit()

        print(f"Feed cleanup complete: deleted {result.rowcount} expired items")
        break


if __name__ == "__main__":
    asyncio.run(main())
