from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from src.models import Bookmark, BookmarkState
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class SearchService:
    async def keyword_search(
        self,
        query: str,
        session: AsyncSession,
        state_filter: Optional[str] = None,
        limit: int = 20
    ) -> List[Bookmark]:
        """Simple keyword search on title and description"""
        stmt = select(Bookmark).where(
            or_(
                Bookmark.title.ilike(f"%{query}%"),
                Bookmark.description.ilike(f"%{query}%"),
                Bookmark.url.ilike(f"%{query}%")
            )
        )

        if state_filter:
            state_enum = BookmarkState(state_filter)
            stmt = stmt.where(Bookmark.state == state_enum)

        stmt = stmt.order_by(Bookmark.added_at.desc()).limit(limit)

        result = await session.execute(stmt)
        return result.scalars().all()
