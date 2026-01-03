# src/services/feed_service.py
import feedparser
import httpx
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import Feed, FeedItem

logger = logging.getLogger(__name__)


class FeedService:
    def __init__(self):
        self.timeout = 30.0

    async def fetch_and_parse(self, url: str) -> Optional[dict]:
        """Fetch RSS feed and parse it"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=self.timeout, follow_redirects=True)
                response.raise_for_status()
                content = response.text
        except Exception as e:
            logger.error(f"Failed to fetch feed {url}: {e}")
            return None

        parsed = feedparser.parse(content)
        if parsed.bozo and not parsed.entries:
            logger.error(f"Failed to parse feed {url}: {parsed.bozo_exception}")
            return None

        return parsed

    async def refresh_feed(self, feed: Feed, session: AsyncSession) -> int:
        """Refresh a single feed, returns count of new items"""
        parsed = await self.fetch_and_parse(feed.url)

        if parsed is None:
            feed.error_count += 1
            await session.commit()
            return 0

        # Reset error count on success
        feed.error_count = 0
        feed.last_fetched_at = datetime.utcnow()

        # Update feed title if not set
        if not feed.title and parsed.feed.get('title'):
            feed.title = parsed.feed.get('title')

        new_count = 0
        for entry in parsed.entries:
            guid = entry.get('id') or entry.get('link') or entry.get('title')
            if not guid:
                continue

            # Check if item already exists
            existing = await session.execute(
                select(FeedItem).where(
                    FeedItem.feed_id == feed.id,
                    FeedItem.guid == guid
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Parse published date
            published_at = None
            if entry.get('published_parsed'):
                try:
                    published_at = datetime(*entry.published_parsed[:6])
                except Exception:
                    pass

            item = FeedItem(
                feed_id=feed.id,
                guid=guid,
                url=entry.get('link', ''),
                title=entry.get('title'),
                description=entry.get('summary') or entry.get('description'),
                published_at=published_at
            )
            session.add(item)
            new_count += 1

        await session.commit()
        return new_count

    async def refresh_all_feeds(self, session: AsyncSession) -> dict:
        """Refresh all feeds that haven't errored out"""
        result = await session.execute(
            select(Feed).where(Feed.error_count < 3)
        )
        feeds = result.scalars().all()

        stats = {"refreshed": 0, "new_items": 0, "errors": 0}
        for feed in feeds:
            try:
                new_count = await self.refresh_feed(feed, session)
                stats["refreshed"] += 1
                stats["new_items"] += new_count
            except Exception as e:
                logger.error(f"Error refreshing feed {feed.url}: {e}")
                stats["errors"] += 1

        return stats
