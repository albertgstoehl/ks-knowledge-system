# RSS Feeds Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add RSS feed subscriptions with auto-expiring items and promotion to bookmarks.

**Architecture:** New Feed/FeedItem models, feeds router for API, feed service for RSS parsing, cron jobs for refresh (2h) and cleanup (1h), new Feeds tab in UI with collapsible feed sections.

**Tech Stack:** feedparser for RSS parsing, SQLAlchemy models, FastAPI router, Jinja2 templates.

---

## Task 1: Add feedparser Dependency

**Files:**
- Modify: `pyproject.toml:16-27`
- Modify: `requirements.txt`

**Step 1: Add feedparser to pyproject.toml**

```toml
server = [
    "fastapi==0.115.0",
    "uvicorn[standard]==0.31.0",
    "pydantic==2.9.2",
    "pydantic-settings==2.5.2",
    "sqlalchemy==2.0.35",
    "aiosqlite==0.20.0",
    "sqlite-vss==0.1.2",
    "sentence-transformers==3.2.0",
    "httpx==0.27.2",
    "jinja2==3.1.4",
    "feedparser==6.0.11",
]
```

**Step 2: Add to requirements.txt**

Add line: `feedparser==6.0.11`

**Step 3: Commit**

```bash
git add pyproject.toml requirements.txt
git commit -m "feat: add feedparser dependency for RSS support"
```

---

## Task 2: Create Feed and FeedItem Models

**Files:**
- Modify: `src/models.py`

**Step 1: Add Feed and FeedItem models**

Add after the Embedding class:

```python
class Feed(Base):
    __tablename__ = "feeds"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=True)
    last_fetched_at = Column(DateTime, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)


class FeedItem(Base):
    __tablename__ = "feed_items"

    id = Column(Integer, primary_key=True, index=True)
    feed_id = Column(Integer, ForeignKey("feeds.id", ondelete="CASCADE"), nullable=False, index=True)
    guid = Column(String, nullable=False)
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('feed_id', 'guid', name='uq_feed_item_guid'),
    )
```

**Step 2: Add UniqueConstraint import**

Update the import line at top:

```python
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Text, ForeignKey, UniqueConstraint
```

**Step 3: Commit**

```bash
git add src/models.py
git commit -m "feat: add Feed and FeedItem models"
```

---

## Task 3: Create Feed Schemas

**Files:**
- Modify: `src/schemas.py`

**Step 1: Add feed schemas**

Add at end of file:

```python
class FeedCreate(BaseModel):
    url: HttpUrl


class FeedUpdate(BaseModel):
    title: str


class FeedItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    feed_id: int
    guid: str
    url: str
    title: Optional[str]
    description: Optional[str]
    published_at: Optional[datetime]
    fetched_at: datetime


class FeedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: Optional[str]
    last_fetched_at: Optional[datetime]
    error_count: int
    created_at: datetime


class FeedWithItemsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: Optional[str]
    last_fetched_at: Optional[datetime]
    error_count: int
    created_at: datetime
    items: list[FeedItemResponse]
```

**Step 2: Commit**

```bash
git add src/schemas.py
git commit -m "feat: add feed schemas"
```

---

## Task 4: Create Feed Service

**Files:**
- Create: `src/services/feed_service.py`

**Step 1: Create feed service**

```python
# src/services/feed_service.py
import feedparser
import httpx
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
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
```

**Step 2: Commit**

```bash
git add src/services/feed_service.py
git commit -m "feat: add feed service for RSS parsing"
```

---

## Task 5: Create Feeds Router

**Files:**
- Create: `src/routers/feeds.py`
- Modify: `src/main.py`

**Step 1: Create feeds router**

```python
# src/routers/feeds.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
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
            .where(FeedItem.fetched_at >= cutoff)
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
    from src.main import background_job_service
    from fastapi import BackgroundTasks

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
```

**Step 2: Register router in main.py**

Update imports in `src/main.py`:

```python
from src.routers import bookmarks, search, backup, ui, feeds
```

Add after other router registrations:

```python
app.include_router(feeds.router)
```

**Step 3: Commit**

```bash
git add src/routers/feeds.py src/main.py
git commit -m "feat: add feeds router with CRUD and save endpoints"
```

---

## Task 6: Create Cron Scripts

**Files:**
- Create: `scripts/feed_refresh.py`
- Create: `scripts/feed_cleanup.py`

**Step 1: Create feed refresh script**

```python
#!/usr/bin/env python3
# scripts/feed_refresh.py
"""Refresh all RSS feeds - run every 2 hours via cron"""
import asyncio
import sys
import os

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
```

**Step 2: Create feed cleanup script**

```python
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
```

**Step 3: Make scripts executable**

```bash
chmod +x scripts/feed_refresh.py scripts/feed_cleanup.py
```

**Step 4: Commit**

```bash
git add scripts/feed_refresh.py scripts/feed_cleanup.py
git commit -m "feat: add cron scripts for feed refresh and cleanup"
```

---

## Task 7: Update Dockerfile with Cron Jobs

**Files:**
- Modify: `Dockerfile:36-37`

**Step 1: Update cron setup in Dockerfile**

Replace the existing cron setup line:

```dockerfile
# Setup cron for daily backups and feed jobs
RUN (echo "0 2 * * * /app/scripts/backup_cron.sh"; \
     echo "0 */2 * * * cd /app && /usr/local/bin/python scripts/feed_refresh.py >> /var/log/feed_refresh.log 2>&1"; \
     echo "0 * * * * cd /app && /usr/local/bin/python scripts/feed_cleanup.py >> /var/log/feed_cleanup.log 2>&1") | crontab -
```

**Step 2: Commit**

```bash
git add Dockerfile
git commit -m "feat: add feed refresh and cleanup cron jobs"
```

---

## Task 8: Create Feeds Template

**Files:**
- Create: `src/templates/feeds.html`

**Step 1: Create feeds template**

```html
{% extends "base.html" %}

{% block content %}
<header class="header">
    <h1>Bookmarks</h1>
    <nav class="tabs">
        <a href="/ui/?view=inbox" class="tab">Inbox</a>
        <a href="/ui/?view=archive" class="tab">Archive</a>
        <a href="/ui/?view=feeds" class="tab active">Feeds</a>
    </nav>
</header>

<div class="add-feed-box">
    <input type="text"
           id="feed-url-input"
           placeholder="Paste RSS feed URL..."
           autocomplete="off">
    <button id="add-feed-btn" class="btn btn-primary">Add</button>
</div>

<main class="layout">
    <section class="feed-list" id="feed-list">
        {% if feeds %}
            {% for feed in feeds %}
            <div class="feed-section" data-feed-id="{{ feed.id }}">
                <div class="feed-header" onclick="toggleFeed({{ feed.id }})">
                    <span class="feed-toggle">▼</span>
                    <span class="feed-title">{{ feed.title or feed.url | domain }}</span>
                    <span class="feed-count">({{ feed.items | length }})</span>
                    <button class="feed-menu-btn" onclick="event.stopPropagation(); showFeedMenu({{ feed.id }}, '{{ feed.title | e }}')"">...</button>
                </div>
                <div class="feed-items" id="feed-items-{{ feed.id }}">
                    {% for item in feed.items %}
                    <div class="feed-item"
                         data-item-id="{{ item.id }}"
                         data-feed-id="{{ feed.id }}"
                         data-url="{{ item.url }}"
                         data-title="{{ item.title or 'Untitled' }}"
                         data-description="{{ item.description or '' }}">
                        <div class="feed-item-title">{{ item.title or 'Untitled' }}</div>
                        <div class="feed-item-meta">
                            {% if item.published_at %}
                                {{ item.published_at.strftime('%b %d, %H:%M') }}
                            {% else %}
                                {{ item.fetched_at.strftime('%b %d, %H:%M') }}
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                    {% if not feed.items %}
                    <div class="empty-state">No items</div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div class="empty-state">
                No feeds yet. Add an RSS feed URL above.
            </div>
        {% endif %}
    </section>

    <aside class="detail-panel" id="detail-panel">
        <div class="empty-state">Select an item to view details</div>
    </aside>
</main>
{% endblock %}

{% block scripts %}
<script>
(function() {
    const API_BASE = '/feeds';

    // Toggle feed section
    window.toggleFeed = function(feedId) {
        const items = document.getElementById('feed-items-' + feedId);
        const section = items.closest('.feed-section');
        const toggle = section.querySelector('.feed-toggle');

        if (items.style.display === 'none') {
            items.style.display = 'block';
            toggle.textContent = '▼';
        } else {
            items.style.display = 'none';
            toggle.textContent = '▶';
        }
    };

    // Show feed menu
    window.showFeedMenu = function(feedId, currentTitle) {
        const action = prompt('Enter action:\n1. Rename\n2. Unsubscribe\n\nOr press Cancel');
        if (action === '1') {
            const newTitle = prompt('New name:', currentTitle);
            if (newTitle && newTitle !== currentTitle) {
                renameFeed(feedId, newTitle);
            }
        } else if (action === '2') {
            if (confirm('Unsubscribe from this feed?')) {
                deleteFeed(feedId);
            }
        }
    };

    // Rename feed
    async function renameFeed(feedId, newTitle) {
        try {
            const res = await fetch(`${API_BASE}/${feedId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            });
            if (res.ok) {
                location.reload();
            }
        } catch (err) {
            console.error('Failed to rename feed:', err);
        }
    }

    // Delete feed
    async function deleteFeed(feedId) {
        try {
            const res = await fetch(`${API_BASE}/${feedId}`, { method: 'DELETE' });
            if (res.ok) {
                document.querySelector(`[data-feed-id="${feedId}"]`).remove();
            }
        } catch (err) {
            console.error('Failed to delete feed:', err);
        }
    }

    // Add feed
    document.getElementById('add-feed-btn').addEventListener('click', async function() {
        const input = document.getElementById('feed-url-input');
        const url = input.value.trim();
        if (!url) return;

        try {
            const res = await fetch(API_BASE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });
            if (res.ok) {
                location.reload();
            } else {
                const data = await res.json();
                alert(data.detail || 'Failed to add feed');
            }
        } catch (err) {
            console.error('Failed to add feed:', err);
            alert('Failed to add feed');
        }
    });

    // Enter key to add feed
    document.getElementById('feed-url-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            document.getElementById('add-feed-btn').click();
        }
    });

    // Render detail panel for feed item
    function renderFeedItemDetail(item) {
        const panel = document.getElementById('detail-panel');
        const data = item.dataset;

        panel.innerHTML = `
            <button class="btn back-btn" onclick="closeDetail()">← Back</button>
            <h2 class="detail-title">${data.title}</h2>
            <p class="detail-description">${data.description || 'No description'}</p>
            <div class="detail-actions">
                <a href="${data.url}" target="_blank" class="btn btn-primary">Open</a>
                <button class="btn" onclick="saveItem(${data.feedId}, ${data.itemId})">Save to Bookmarks</button>
                <button class="btn btn-danger" onclick="dismissItem(${data.feedId}, ${data.itemId})">Dismiss</button>
            </div>
        `;
        panel.classList.add('active');
    }

    // Close detail
    window.closeDetail = function() {
        document.getElementById('detail-panel').classList.remove('active');
        document.querySelectorAll('.feed-item').forEach(el => el.classList.remove('selected'));
    };

    // Save item to bookmarks
    window.saveItem = async function(feedId, itemId) {
        try {
            const res = await fetch(`${API_BASE}/${feedId}/items/${itemId}/save`, {
                method: 'POST'
            });
            if (res.ok) {
                alert('Saved to bookmarks!');
                closeDetail();
            }
        } catch (err) {
            console.error('Failed to save item:', err);
        }
    };

    // Dismiss item
    window.dismissItem = async function(feedId, itemId) {
        try {
            const res = await fetch(`${API_BASE}/${feedId}/items/${itemId}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                document.querySelector(`[data-item-id="${itemId}"]`).remove();
                closeDetail();
            }
        } catch (err) {
            console.error('Failed to dismiss item:', err);
        }
    };

    // Click handler for feed items
    document.getElementById('feed-list').addEventListener('click', function(e) {
        const item = e.target.closest('.feed-item');
        if (item) {
            document.querySelectorAll('.feed-item').forEach(el => el.classList.remove('selected'));
            item.classList.add('selected');
            renderFeedItemDetail(item);
        }
    });
})();
</script>
{% endblock %}
```

**Step 2: Commit**

```bash
git add src/templates/feeds.html
git commit -m "feat: add feeds template with collapsible sections"
```

---

## Task 9: Update Base Template with Feed Styles

**Files:**
- Modify: `src/templates/base.html`

**Step 1: Add feed-specific styles**

Add before `</style>` closing tag:

```css
        /* Feed specific styles */
        .add-feed-box {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }
        .add-feed-box input {
            flex: 1;
            padding: 0.75rem;
            border: 1px solid #000;
            font-family: inherit;
            font-size: 1rem;
        }
        .feed-section {
            border: 1px solid #000;
            margin-bottom: 0.5rem;
        }
        .feed-header {
            display: flex;
            align-items: center;
            padding: 0.75rem;
            cursor: pointer;
            background: #f5f5f5;
            gap: 0.5rem;
        }
        .feed-header:hover { background: #eee; }
        .feed-toggle { font-size: 0.75rem; }
        .feed-title { flex: 1; font-weight: 500; }
        .feed-count { color: #666; font-size: 0.875rem; }
        .feed-menu-btn {
            background: none;
            border: none;
            cursor: pointer;
            padding: 0.25rem 0.5rem;
            font-size: 1rem;
        }
        .feed-items { }
        .feed-item {
            padding: 0.75rem;
            cursor: pointer;
            border-top: 1px solid #eee;
        }
        .feed-item:hover { background: #f9f9f9; }
        .feed-item.selected { background: #f5f5f5; }
        .feed-item-title { font-weight: 500; }
        .feed-item-meta { color: #666; font-size: 0.875rem; }
        .feed-list { }
```

**Step 2: Commit**

```bash
git add src/templates/base.html
git commit -m "feat: add feed-specific styles to base template"
```

---

## Task 10: Update UI Router for Feeds View

**Files:**
- Modify: `src/routers/ui.py`

**Step 1: Add feeds view handling**

Update the `ui_index` function to handle feeds view:

```python
@router.get("/", response_class=HTMLResponse)
async def ui_index(
    request: Request,
    view: str = "inbox",
    q: str = None,
    session: AsyncSession = Depends(get_db)
):
    """Main UI page"""
    from src.models import Feed, FeedItem
    from datetime import datetime, timedelta

    # Handle feeds view
    if view == "feeds":
        cutoff = datetime.utcnow() - timedelta(hours=24)

        result = await session.execute(
            select(Feed).order_by(Feed.title)
        )
        feeds_list = result.scalars().all()

        feeds_with_items = []
        for feed in feeds_list:
            items_result = await session.execute(
                select(FeedItem)
                .where(FeedItem.feed_id == feed.id)
                .where(FeedItem.fetched_at >= cutoff)
                .order_by(FeedItem.published_at.desc().nullslast(), FeedItem.fetched_at.desc())
            )
            items = items_result.scalars().all()
            feeds_with_items.append({
                "id": feed.id,
                "url": feed.url,
                "title": feed.title,
                "error_count": feed.error_count,
                "items": items
            })

        return templates.TemplateResponse(
            "feeds.html",
            {
                "request": request,
                "feeds": feeds_with_items,
                "view": view
            }
        )

    # Map view to state
    state = BookmarkState.read if view == "archive" else BookmarkState.inbox

    # Build query
    query = select(Bookmark).where(Bookmark.state == state)

    # Search in archive view
    if view == "archive" and q:
        search_term = f"%{q}%"
        query = query.where(
            (Bookmark.title.ilike(search_term)) |
            (Bookmark.description.ilike(search_term)) |
            (Bookmark.url.ilike(search_term))
        )

    query = query.order_by(Bookmark.added_at.desc()).limit(100)

    result = await session.execute(query)
    bookmarks = result.scalars().all()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "bookmarks": bookmarks,
            "view": view,
            "query": q
        }
    )
```

**Step 2: Add imports at top**

```python
from datetime import datetime, timedelta
```

**Step 3: Commit**

```bash
git add src/routers/ui.py
git commit -m "feat: add feeds view to UI router"
```

---

## Task 11: Update Index Template with Feeds Tab

**Files:**
- Modify: `src/templates/index.html`

**Step 1: Add Feeds tab to navigation**

Update the nav section:

```html
    <nav class="tabs">
        <a href="/ui/?view=inbox" class="tab {% if view == 'inbox' %}active{% endif %}">Inbox</a>
        <a href="/ui/?view=archive" class="tab {% if view == 'archive' %}active{% endif %}">Archive</a>
        <a href="/ui/?view=feeds" class="tab {% if view == 'feeds' %}active{% endif %}">Feeds</a>
    </nav>
```

**Step 2: Commit**

```bash
git add src/templates/index.html
git commit -m "feat: add Feeds tab to navigation"
```

---

## Task 12: Add Tests for Feeds

**Files:**
- Create: `tests/test_feeds.py`

**Step 1: Create feed tests**

```python
# tests/test_feeds.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_feeds_ui_returns_html():
    """Feeds view should return HTML page"""
    response = client.get("/ui/?view=feeds")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Feeds" in response.text


def test_list_feeds_empty():
    """List feeds should return empty list initially"""
    response = client.get("/feeds")
    assert response.status_code == 200
    assert response.json() == []


def test_create_feed_invalid_url():
    """Creating feed with invalid RSS should fail"""
    response = client.post("/feeds", json={"url": "https://example.com/not-a-feed"})
    assert response.status_code == 400
```

**Step 2: Run tests**

```bash
pytest tests/test_feeds.py -v
```

**Step 3: Commit**

```bash
git add tests/test_feeds.py
git commit -m "test: add basic feed tests"
```

---

## Task 13: Run Full Test Suite

**Step 1: Run all tests**

```bash
pytest tests/ -v
```

**Step 2: Fix any issues if needed**

**Step 3: Final commit if any cleanup**

```bash
git status
# If clean, we're done
```

---

## Summary

| Task | Files | Description |
|------|-------|-------------|
| 1 | pyproject.toml, requirements.txt | Add feedparser |
| 2 | models.py | Feed, FeedItem models |
| 3 | schemas.py | Feed schemas |
| 4 | feed_service.py | RSS parsing service |
| 5 | feeds.py, main.py | Feeds API router |
| 6 | scripts/*.py | Cron scripts |
| 7 | Dockerfile | Cron job setup |
| 8 | feeds.html | Feeds template |
| 9 | base.html | Feed styles |
| 10 | ui.py | Feeds view handler |
| 11 | index.html | Feeds tab |
| 12 | test_feeds.py | Tests |
| 13 | - | Full test run |
