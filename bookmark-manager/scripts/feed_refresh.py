#!/usr/bin/env python3
# scripts/feed_refresh.py
"""Refresh all RSS feeds - run every 2 hours via cron"""
import asyncio
import sys

sys.path.insert(0, '/app')

from src.database import init_db, get_db
from src.services.feed_service import FeedService


async def main():
    await init_db()

    async for session in get_db():
        service = FeedService()
        stats = await service.refresh_all_feeds(session)
        print(f"Feed refresh complete: {stats}")
        break


if __name__ == "__main__":
    asyncio.run(main())
