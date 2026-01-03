# src/routers/feeds.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, timedelta
from src.database import get_db
from src.models import Feed, FeedItem, Bookmark, BookmarkState
from src.schemas import (
    FeedCreate, FeedUpdate, FeedResponse, FeedWithItemsResponse, FeedItemResponse,
    BookmarkResponse
)
from src.services.feed_service import FeedService
from typing import List

router = APIRouter(prefix="/feeds", tags=["feeds"])
feed_service = FeedService()


@router.post("", response_model=FeedResponse, status_code=status.HTTP_201_CREATED)
async def create_feed(
    feed_data: FeedCreate,
    session: AsyncSession = Depends(get_db)
):
    """Subscribe to a new RSS feed"""
    url = str(feed_data.url)

    # Check for duplicate
    result = await session.execute(
        select(Feed).where(Feed.url == url)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already subscribed to this feed"
        )

    # Validate it's a valid RSS feed
    parsed = await feed_service.fetch_and_parse(url)
    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not fetch or parse RSS feed"
        )

    # Create feed
    feed = Feed(
        url=url,
        title=parsed.feed.get('title')
    )
    session.add(feed)
    await session.commit()
    await session.refresh(feed)

    # Fetch initial items
    await feed_service.refresh_feed(feed, session)

    return feed


@router.get("", response_model=List[FeedWithItemsResponse])
async def list_feeds(
    session: AsyncSession = Depends(get_db)
):
    """List all feeds with their items"""
    # Get items from last 24 hours only
    cutoff = datetime.utcnow() - timedelta(hours=24)

    result = await session.execute(
        select(Feed).order_by(Feed.title)
    )
    feeds = result.scalars().all()

    response = []
    for feed in feeds:
        items_result = await session.execute(
            select(FeedItem)
            .where(FeedItem.feed_id == feed.id)
            .where(FeedItem.published_at >= cutoff)
            .order_by(FeedItem.published_at.desc().nullslast(), FeedItem.fetched_at.desc())
        )
        items = items_result.scalars().all()

        response.append(FeedWithItemsResponse(
            id=feed.id,
            url=feed.url,
            title=feed.title,
            last_fetched_at=feed.last_fetched_at,
            error_count=feed.error_count,
            created_at=feed.created_at,
            items=[FeedItemResponse.model_validate(item) for item in items]
        ))

    return response


@router.patch("/{feed_id}", response_model=FeedResponse)
async def update_feed(
    feed_id: int,
    update_data: FeedUpdate,
    session: AsyncSession = Depends(get_db)
):
    """Update feed (rename)"""
    feed = await session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found"
        )

    feed.title = update_data.title
    await session.commit()
    await session.refresh(feed)
    return feed


@router.delete("/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed(
    feed_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Unsubscribe from feed"""
    feed = await session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found"
        )

    await session.delete(feed)
    await session.commit()


@router.post("/{feed_id}/items/{item_id}/save", response_model=BookmarkResponse)
async def save_feed_item(
    feed_id: int,
    item_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Promote feed item to bookmark"""
    item = await session.get(FeedItem, item_id)
    if not item or item.feed_id != feed_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed item not found"
        )

    # Check if bookmark already exists
    result = await session.execute(
        select(Bookmark).where(Bookmark.url == item.url)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # Create bookmark
    bookmark = Bookmark(
        url=item.url,
        title=item.title,
        description=item.description,
        state=BookmarkState.inbox
    )
    session.add(bookmark)
    await session.commit()
    await session.refresh(bookmark)

    return bookmark


@router.delete("/{feed_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_feed_item(
    feed_id: int,
    item_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Dismiss feed item early"""
    item = await session.get(FeedItem, item_id)
    if not item or item.feed_id != feed_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed item not found"
        )

    await session.delete(item)
    await session.commit()


@router.post("/{feed_id}/refresh", response_model=FeedResponse)
async def refresh_feed(
    feed_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Manually refresh a feed"""
    feed = await session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found"
        )

    # Reset error count to allow retry
    feed.error_count = 0
    await feed_service.refresh_feed(feed, session)
    await session.refresh(feed)
    return feed
