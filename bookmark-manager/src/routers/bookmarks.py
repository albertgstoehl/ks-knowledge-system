from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database import get_db
from src.models import Bookmark, BookmarkState
from src.schemas import BookmarkCreate, BookmarkUpdate, BookmarkDescriptionUpdate, BookmarkTitleUpdate, BookmarkTimestampUpdate, BookmarkResponse, BookmarkContentResponse, BookmarkPinUpdate, BookmarkThesisUpdate, BookmarkExportResponse
from typing import List, Optional
from datetime import datetime, timedelta
import re


def calculate_expiry(pinned: bool, is_thesis: bool) -> Optional[datetime]:
    """Calculate expiry date. Returns None for protected items."""
    if pinned or is_thesis:
        return None
    return datetime.utcnow() + timedelta(days=7)


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL.

    Supports:
    - youtube.com/watch?v=VIDEO_ID
    - youtu.be/VIDEO_ID
    - youtube.com/embed/VIDEO_ID
    """
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])

@router.post("", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    bookmark_data: BookmarkCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    """Create a new bookmark"""
    # Import here to avoid circular import
    from src.main import background_job_service

    # Check for duplicate
    result = await session.execute(
        select(Bookmark).where(Bookmark.url == str(bookmark_data.url))
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bookmark with this URL already exists"
        )

    # Detect YouTube video
    url_str = str(bookmark_data.url)
    video_id = extract_video_id(url_str)

    # Detect academic paper -> thesis
    from src.services.paper_detection import is_academic_url
    is_thesis = is_academic_url(url_str)

    # Calculate expiry
    expires_at = calculate_expiry(pinned=False, is_thesis=is_thesis)

    # Create bookmark
    bookmark = Bookmark(
        url=url_str,
        state=BookmarkState.inbox,
        video_id=video_id,
        is_thesis=is_thesis,
        expires_at=expires_at
    )
    session.add(bookmark)
    await session.commit()
    await session.refresh(bookmark)

    # Queue background processing
    background_tasks.add_task(
        background_job_service.process_new_bookmark,
        bookmark.id,
        session
    )

    return bookmark

@router.get("", response_model=List[BookmarkResponse])
async def list_bookmarks(
    state: Optional[str] = None,
    view: Optional[str] = None,  # inbox|thesis|pins
    is_thesis: Optional[bool] = None,  # Renamed from is_paper
    pinned: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db)
):
    """List bookmarks with optional filters"""
    query = select(Bookmark)

    # View-based filtering (mutually exclusive with individual filters)
    if view:
        if view == "inbox":
            # Regular inbox: not thesis, not pinned
            query = query.where(
                Bookmark.state == BookmarkState.inbox,
                Bookmark.is_thesis == False,
                Bookmark.pinned == False
            )
        elif view == "thesis":
            # Thesis items in inbox
            query = query.where(
                Bookmark.state == BookmarkState.inbox,
                Bookmark.is_thesis == True
            )
        elif view == "pins":
            # Pinned items in inbox
            query = query.where(
                Bookmark.state == BookmarkState.inbox,
                Bookmark.pinned == True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid view. Must be 'inbox', 'thesis', or 'pins'"
            )
    else:
        # Individual filters
        if state:
            try:
                state_enum = BookmarkState(state)
                query = query.where(Bookmark.state == state_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid state. Must be 'inbox' or 'read'"
                )

        if is_thesis is not None:
            query = query.where(Bookmark.is_thesis == is_thesis)

        if pinned is not None:
            query = query.where(Bookmark.pinned == pinned)

    query = query.order_by(Bookmark.added_at.desc()).limit(limit).offset(offset)

    result = await session.execute(query)
    bookmarks = result.scalars().all()

    return bookmarks


@router.get("/recently-archived", response_model=list[BookmarkResponse])
async def get_recently_archived(
    limit: int = 5,
    session: AsyncSession = Depends(get_db)
):
    """Get recently archived bookmarks"""
    query = (
        select(Bookmark)
        .where(Bookmark.state == BookmarkState.read)
        .order_by(Bookmark.read_at.desc().nullslast(), Bookmark.added_at.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/expiring", response_model=List[BookmarkResponse])
async def get_expiring_bookmarks(
    hours: int = 24,
    session: AsyncSession = Depends(get_db)
):
    """Get bookmarks expiring within the next N hours (default 24)"""
    now = datetime.utcnow()
    cutoff = now + timedelta(hours=hours)

    query = (
        select(Bookmark)
        .where(
            Bookmark.expires_at != None,
            Bookmark.expires_at > now,
            Bookmark.expires_at <= cutoff
        )
        .order_by(Bookmark.expires_at.asc())
    )

    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{bookmark_id}", response_model=BookmarkResponse)
async def get_bookmark(
    bookmark_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Get a single bookmark by ID"""
    bookmark = await session.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    return bookmark

@router.patch("/{bookmark_id}", response_model=BookmarkResponse)
async def update_bookmark(
    bookmark_id: int,
    update_data: BookmarkUpdate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    """Update bookmark (mark as read/inbox)"""
    bookmark = await session.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    if update_data.state:
        bookmark.state = BookmarkState(update_data.state)
        if update_data.state == "read":
            from datetime import datetime
            bookmark.read_at = datetime.utcnow()

            # Trigger Zotero sync for thesis papers
            if bookmark.is_thesis and not bookmark.zotero_key:
                background_tasks.add_task(
                    sync_paper_to_zotero,
                    bookmark.id,
                    session
                )
        else:
            bookmark.read_at = None

    await session.commit()
    await session.refresh(bookmark)

    return bookmark

@router.patch("/{bookmark_id}/description", response_model=BookmarkResponse)
async def update_bookmark_description(
    bookmark_id: int,
    update_data: BookmarkDescriptionUpdate,
    session: AsyncSession = Depends(get_db)
):
    """Update bookmark description and regenerate embedding"""
    from src.main import background_job_service

    bookmark = await session.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    # Update description
    bookmark.description = update_data.description

    # Regenerate embedding
    embedding_service = background_job_service._get_embedding_service()
    search_text = f"{bookmark.title or ''} {bookmark.description or ''}".strip()

    if search_text:
        embedding = embedding_service.generate_embedding(search_text)
        bookmark.embedding = embedding

    await session.commit()
    await session.refresh(bookmark)

    return bookmark

@router.patch("/{bookmark_id}/title", response_model=BookmarkResponse)
async def update_bookmark_title(
    bookmark_id: int,
    update_data: BookmarkTitleUpdate,
    session: AsyncSession = Depends(get_db)
):
    """Update bookmark title"""
    bookmark = await session.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    bookmark.title = update_data.title
    await session.commit()
    await session.refresh(bookmark)

    return bookmark

@router.patch("/{bookmark_id}/timestamp", response_model=BookmarkResponse)
async def update_bookmark_timestamp(
    bookmark_id: int,
    update_data: BookmarkTimestampUpdate,
    session: AsyncSession = Depends(get_db)
):
    """Update video timestamp for resume playback"""
    bookmark = await session.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    if not bookmark.video_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bookmark is not a video"
        )

    bookmark.video_timestamp = update_data.timestamp
    await session.commit()
    await session.refresh(bookmark)

    return bookmark


@router.post("/{bookmark_id}/retry")
async def retry_scrape(
    bookmark_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Retry scraping for a failed bookmark with SSE progress updates"""
    from fastapi.responses import StreamingResponse
    from src.main import background_job_service

    bookmark = await session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    async def event_stream():
        async for progress in background_job_service.process_bookmark_with_progress(bookmark_id, session):
            yield f"data: {progress}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.patch("/{bookmark_id}/pin", response_model=BookmarkResponse)
async def toggle_pin(
    bookmark_id: int,
    update_data: BookmarkPinUpdate,
    session: AsyncSession = Depends(get_db)
):
    """Toggle bookmark pinned status"""
    bookmark = await session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    bookmark.pinned = update_data.pinned
    # Recalculate expiry
    bookmark.expires_at = calculate_expiry(bookmark.pinned, bookmark.is_thesis)

    await session.commit()
    await session.refresh(bookmark)
    return bookmark


@router.patch("/{bookmark_id}/thesis", response_model=BookmarkResponse)
async def toggle_thesis(
    bookmark_id: int,
    update_data: BookmarkThesisUpdate,
    session: AsyncSession = Depends(get_db)
):
    """Toggle bookmark thesis status"""
    bookmark = await session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    bookmark.is_thesis = update_data.is_thesis
    # Recalculate expiry
    bookmark.expires_at = calculate_expiry(bookmark.pinned, bookmark.is_thesis)

    await session.commit()
    await session.refresh(bookmark)
    return bookmark


@router.get("/{bookmark_id}/content", response_model=BookmarkContentResponse)
async def get_bookmark_content(
    bookmark_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Get bookmark with full content for note creation"""
    bookmark = await session.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    return bookmark


@router.get("/{bookmark_id}/export", response_model=BookmarkExportResponse)
async def export_bookmark(
    bookmark_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Export full bookmark data for archiving to Kasten"""
    bookmark = await session.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    return bookmark


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Delete a bookmark"""
    bookmark = await session.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    await session.delete(bookmark)
    await session.commit()


async def sync_paper_to_zotero(bookmark_id: int, session: AsyncSession):
    """Background task to sync paper to Zotero."""
    import os
    from src.services.zotero_service import ZoteroService
    from src.services.paper_detection import extract_doi

    bookmark = await session.get(Bookmark, bookmark_id)
    if not bookmark or not bookmark.is_thesis:
        return

    zotero = ZoteroService()
    if not zotero.api_key:
        return

    doi = extract_doi(bookmark.url)
    result = await zotero.sync_paper(
        url=bookmark.url,
        title=bookmark.title or "Untitled",
        doi=doi
    )

    if result.get("zotero_key"):
        bookmark.zotero_key = result["zotero_key"]
        await session.commit()
