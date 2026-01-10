# src/routers/ui.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta
from typing import Optional
from src.database import get_db
from src.models import Bookmark, BookmarkState, Feed, FeedItem
from pathlib import Path
from urllib.parse import urlparse
import os
from src.utils.paths import find_shared_dir
from src.utils.sanitize import safe_html

CANVAS_EXTERNAL_URL = os.getenv("CANVAS_EXTERNAL_URL", "http://localhost:8002")
BASE_PATH = os.getenv("BASE_PATH", "").rstrip("/")

router = APIRouter(prefix="/ui", tags=["ui"])

templates_dir = Path(__file__).parent.parent / "templates"
shared_templates_dir = find_shared_dir(Path(__file__)) / "templates"
templates = Jinja2Templates(directory=[str(templates_dir), str(shared_templates_dir)])


def domain_filter(url: str) -> str:
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
    except Exception:
        return url


templates.env.filters["domain"] = domain_filter
templates.env.filters["safe_html"] = safe_html


def expiry_filter(expires_at: datetime) -> str:
    """Format expiry as '5d left' or 'expires today'"""
    if expires_at is None:
        return ""
    now = datetime.utcnow()
    delta = expires_at - now
    days = delta.days
    if days > 1:
        return f"{days}d left"
    elif days == 1:
        return "1d left"
    elif delta.total_seconds() > 0:
        hours = int(delta.total_seconds() // 3600)
        return f"{hours}h left" if hours > 0 else "expires soon"
    return "expired"


templates.env.filters["expiry"] = expiry_filter


@router.get("/", response_class=HTMLResponse)
async def ui_index(
    request: Request,
    view: str = "inbox",
    q: str = None,
    filter: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
):
    """Main UI page"""
    # Handle feeds view
    if view == "feeds":
        cutoff = datetime.utcnow() - timedelta(days=7)  # Changed from 24h to 7 days
        result = await session.execute(select(Feed).order_by(Feed.title))
        feeds_list = result.scalars().all()

        feeds_with_items = []
        for feed in feeds_list:
            items_result = await session.execute(
                select(FeedItem)
                .where(FeedItem.feed_id == feed.id)
                .where(FeedItem.published_at >= cutoff)
                .order_by(FeedItem.published_at.desc().nullslast(), FeedItem.fetched_at.desc())
            )
            items = items_result.scalars().all()
            feeds_with_items.append({
                "id": feed.id,
                "url": feed.url,
                "title": feed.title,
                "error_count": feed.error_count,
                "feed_items": items
            })

        context = {"request": request, "feeds": feeds_with_items, "view": view, "base_path": BASE_PATH}

        # htmx request → return partial
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse("_content_feeds.html", context)

        return templates.TemplateResponse("feeds.html", context)

    # Build query based on view
    query = select(Bookmark)

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

    # Inbox: show items closest to expiring first (conveyor belt)
    # Pins/Thesis: show newest first
    if view == "inbox":
        query = query.order_by(Bookmark.expires_at.asc()).limit(100)
    else:
        query = query.order_by(Bookmark.added_at.desc()).limit(100)
    result = await session.execute(query)
    bookmarks = result.scalars().all()

    # Get counts for display
    inbox_query = select(Bookmark).where(
        Bookmark.state == BookmarkState.inbox,
        Bookmark.is_thesis == False,
        Bookmark.pinned == False
    )
    inbox_result = await session.execute(inbox_query)
    inbox_count = len(inbox_result.scalars().all())

    context = {
        "request": request,
        "bookmarks": bookmarks,
        "view": view,
        "query": q,
        "filter": filter,
        "inbox_count": inbox_count,
        "canvas_url": CANVAS_EXTERNAL_URL,
        "base_path": BASE_PATH
    }

    # htmx request → return partial
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("_content_index.html", context)

    return templates.TemplateResponse("index.html", context)
