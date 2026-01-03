# UI Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate UI to 3 tabs (Inbox/Archive/Feeds) with filter icons, conveyor belt inbox, and search-first archive.

**Architecture:** Remove separate Papers/Pins views, add toggle filter icons. Inbox shows focused single-item view with action panel. Archive shows empty state until search, with recently archived section.

**Tech Stack:** FastAPI, Jinja2, vanilla JS, CSS (brutalist style per docs/style.md)

**Reference:** Design doc at `docs/plans/2025-12-22-ui-redesign.md`

---

### Task 1: Update UI Router - Remove Separate Views, Add Filter Param

**Files:**
- Modify: `src/routers/ui.py:33-128`
- Modify: `tests/test_ui.py`

**Step 1: Write test for filter param**

Add to `tests/test_ui.py`:

```python
def test_ui_inbox_with_paper_filter():
    """Inbox with paper filter should work"""
    response = client.get("/ui/?view=inbox&filter=paper")
    assert response.status_code == 200


def test_ui_inbox_with_pin_filter():
    """Inbox with pin filter should work"""
    response = client.get("/ui/?view=inbox&filter=pin")
    assert response.status_code == 200


def test_ui_archive_with_filter():
    """Archive with filter should work"""
    response = client.get("/ui/?view=archive&filter=paper")
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

```bash
cd /home/ags/knowledge-system/bookmark-manager && python -m pytest tests/test_ui.py -v
```

Expected: PASS (routes exist but filter not yet applied)

**Step 3: Update ui.py to handle filter param**

Replace `src/routers/ui.py` content:

```python
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

router = APIRouter(prefix="/ui", tags=["ui"])

templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


def domain_filter(url: str) -> str:
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
    except Exception:
        return url


templates.env.filters["domain"] = domain_filter


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
        cutoff = datetime.utcnow() - timedelta(hours=24)
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

        return templates.TemplateResponse(
            "feeds.html",
            {"request": request, "feeds": feeds_with_items, "view": view}
        )

    # Build query based on view
    query = select(Bookmark)

    if view == "inbox":
        query = query.where(Bookmark.state == BookmarkState.inbox)
        # Apply filter
        if filter == "paper":
            query = query.where(Bookmark.is_paper == True)
        elif filter == "pin":
            query = query.where(Bookmark.pinned == True)
        else:
            # Default: exclude papers and pins from regular inbox
            query = query.where(Bookmark.pinned == False, Bookmark.is_paper == False)
    elif view == "archive":
        query = query.where(Bookmark.state == BookmarkState.read)
        # Apply filter
        if filter == "paper":
            query = query.where(Bookmark.is_paper == True)
        elif filter == "pin":
            query = query.where(Bookmark.pinned == True)
        # Apply search
        if q:
            search_term = f"%{q}%"
            query = query.where(
                (Bookmark.title.ilike(search_term)) |
                (Bookmark.description.ilike(search_term)) |
                (Bookmark.url.ilike(search_term))
            )

    query = query.order_by(Bookmark.added_at.desc()).limit(100)
    result = await session.execute(query)
    bookmarks = result.scalars().all()

    # Get total inbox count for progress bar
    count_query = select(Bookmark).where(Bookmark.state == BookmarkState.inbox)
    count_result = await session.execute(count_query)
    inbox_count = len(count_result.scalars().all())

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "bookmarks": bookmarks,
            "view": view,
            "query": q,
            "filter": filter,
            "inbox_count": inbox_count
        }
    )
```

**Step 4: Run tests**

```bash
cd /home/ags/knowledge-system/bookmark-manager && python -m pytest tests/test_ui.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add src/routers/ui.py tests/test_ui.py
git commit -m "feat(ui): add filter param, remove separate views"
```

---

### Task 2: Add Recently Archived API Endpoint

**Files:**
- Modify: `src/routers/bookmarks.py`
- Modify: `tests/test_bookmarks_api.py`

**Step 1: Write test**

Add to `tests/test_bookmarks_api.py`:

```python
def test_get_recently_archived(client, test_db):
    """Should return recently archived bookmarks"""
    response = client.get("/bookmarks/recently-archived")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

**Step 2: Run test**

```bash
cd /home/ags/knowledge-system/bookmark-manager && python -m pytest tests/test_bookmarks_api.py::test_get_recently_archived -v
```

Expected: FAIL (endpoint doesn't exist)

**Step 3: Implement endpoint**

Add to `src/routers/bookmarks.py` (before other routes):

```python
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
```

**Step 4: Run test**

```bash
cd /home/ags/knowledge-system/bookmark-manager && python -m pytest tests/test_bookmarks_api.py::test_get_recently_archived -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/routers/bookmarks.py tests/test_bookmarks_api.py
git commit -m "feat(api): add recently-archived endpoint"
```

---

### Task 3: Update Navigation - Remove Papers/Pins Tabs

**Files:**
- Modify: `src/templates/index.html:6-12`
- Modify: `src/templates/base.html:398-406`

**Step 1: Update header tabs in index.html**

Replace lines 6-12:

```html
    <nav class="tabs">
        <a href="/ui/?view=inbox" class="tab {% if view == 'inbox' %}active{% endif %}">Inbox</a>
        <a href="/ui/?view=archive" class="tab {% if view == 'archive' %}active{% endif %}">Archive</a>
        <a href="/ui/?view=feeds" class="tab {% if view == 'feeds' %}active{% endif %}">Feeds</a>
    </nav>
```

**Step 2: Update bottom nav in base.html**

Replace lines 398-406:

```html
    <nav class="bottom-nav">
        <div class="bottom-nav-links">
            <a href="/ui/?view=inbox" class="bottom-nav-link" data-view="inbox">Inbox</a>
            <a href="/ui/?view=archive" class="bottom-nav-link" data-view="archive">Archive</a>
            <a href="/ui/?view=feeds" class="bottom-nav-link" data-view="feeds">Feeds</a>
        </div>
    </nav>
```

**Step 3: Run UI test**

```bash
cd /home/ags/knowledge-system/bookmark-manager && python -m pytest tests/test_ui.py -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add src/templates/index.html src/templates/base.html
git commit -m "feat(ui): consolidate to 3 tabs (inbox/archive/feeds)"
```

---

### Task 4: Add Filter Icons CSS to base.html

**Files:**
- Modify: `src/templates/base.html` (add to style block)

**Step 1: Add CSS for filter icons**

Add after `.pin-icon, .paper-icon { margin-right: 0.25rem; }` (around line 95):

```css
        /* Filter Icons */
        .filter-icons {
            display: flex;
            gap: 0.5rem;
        }
        .filter-icon {
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid #000;
            background: #fff;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.15s ease;
            text-decoration: none;
        }
        .filter-icon:hover { background: #f5f5f5; }
        .filter-icon.active { background: #000; filter: invert(1); }

        /* Progress Bar */
        .progress-bar-container { margin-top: 1rem; }
        .progress-bar {
            height: 4px;
            background: #eee;
            border: 1px solid #000;
        }
        .progress-bar-fill {
            height: 100%;
            background: #000;
            transition: width 0.3s ease;
        }
        .progress-text {
            font-size: 0.75rem;
            color: #666;
            text-align: right;
            margin-top: 0.25rem;
        }

        /* Conveyor Belt Layout */
        .conveyor-layout {
            display: grid;
            grid-template-columns: 1fr 250px;
            gap: 1rem;
            min-height: 60vh;
        }
        @media (max-width: 768px) {
            .conveyor-layout { grid-template-columns: 1fr; }
        }
        .current-item {
            border: 1px solid #000;
            padding: 1.5rem;
        }
        .current-item-title {
            font-size: 1.25rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }
        .current-item-domain {
            color: #666;
            margin-bottom: 1rem;
        }
        .current-item-description {
            line-height: 1.6;
            margin-bottom: 1.5rem;
        }
        .next-up {
            margin-top: 1.5rem;
            padding-top: 1rem;
            border-top: 1px solid #eee;
        }
        .next-up-header {
            font-size: 0.625rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 0.5rem;
            color: #666;
        }
        .next-up-item {
            padding: 0.5rem 0;
            font-size: 0.875rem;
            color: #666;
            cursor: pointer;
        }
        .next-up-item:hover { color: #000; }
        .action-panel {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        .action-btn {
            padding: 1rem;
            border: 1px solid #000;
            background: #fff;
            font-family: inherit;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .action-btn:hover { background: #f5f5f5; }
        .action-btn-primary { background: #000; color: #fff; }
        .action-btn-primary:hover { background: #333; }

        /* Archive Void Layout */
        .archive-void {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 50vh;
            text-align: center;
        }
        .archive-void-message {
            color: #666;
            margin-bottom: 2rem;
        }
        .recently-archived {
            border: 1px solid #000;
            width: 100%;
            max-width: 400px;
        }
        .recently-archived-header {
            padding: 0.75rem;
            background: #f5f5f5;
            font-size: 0.625rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            border-bottom: 1px solid #000;
        }
        .recently-archived-item {
            display: flex;
            justify-content: space-between;
            padding: 0.75rem;
            border-bottom: 1px solid #eee;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .recently-archived-item:last-child { border-bottom: none; }
        .recently-archived-item:hover { background: #f5f5f5; }
        .recently-archived-time {
            color: #999;
            font-size: 0.75rem;
        }

        /* Inbox Header */
        .inbox-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        .inbox-count {
            font-size: 1rem;
            font-weight: 500;
        }

        /* Archive Search Bar */
        .archive-search-bar {
            display: flex;
            gap: 0.5rem;
            align-items: center;
            margin-bottom: 1rem;
        }
        .archive-search-bar input {
            flex: 1;
            padding: 0.75rem;
            border: 1px solid #000;
            font-family: inherit;
            font-size: 1rem;
        }
        .archive-search-bar input:focus {
            outline: 2px solid #000;
            outline-offset: 2px;
        }
        .clear-btn {
            padding: 0.75rem 1rem;
            border: 1px solid #000;
            background: #fff;
            cursor: pointer;
            font-family: inherit;
        }
        .clear-btn:hover { background: #f5f5f5; }
```

**Step 2: Commit**

```bash
git add src/templates/base.html
git commit -m "style: add CSS for filter icons, conveyor belt, archive void"
```

---

### Task 5: Implement Conveyor Belt Inbox Template

**Files:**
- Modify: `src/templates/index.html`

**Step 1: Replace index.html with new conveyor belt layout**

Replace entire `src/templates/index.html`:

```html
{% extends "base.html" %}

{% block content %}
<header class="header">
    <h1>Bookmarks</h1>
    <nav class="tabs">
        <a href="/ui/?view=inbox" class="tab {% if view == 'inbox' %}active{% endif %}">Inbox</a>
        <a href="/ui/?view=archive" class="tab {% if view == 'archive' %}active{% endif %}">Archive</a>
        <a href="/ui/?view=feeds" class="tab {% if view == 'feeds' %}active{% endif %}">Feeds</a>
    </nav>
</header>

{% if view == 'inbox' %}
<!-- INBOX: Conveyor Belt -->
<div class="inbox-header">
    <span class="inbox-count">INBOX ({{ bookmarks|length }})</span>
    <div class="filter-icons">
        <a href="/ui/?view=inbox{% if filter != 'pin' %}&filter=pin{% endif %}"
           class="filter-icon {% if filter == 'pin' %}active{% endif %}" title="Filter pins">&#128204;</a>
        <a href="/ui/?view=inbox{% if filter != 'paper' %}&filter=paper{% endif %}"
           class="filter-icon {% if filter == 'paper' %}active{% endif %}" title="Filter papers">&#128196;</a>
    </div>
</div>

{% if bookmarks %}
<main class="conveyor-layout">
    <section class="current-item" id="current-item">
        {% set current = bookmarks[0] %}
        <div class="current-item-title" data-id="{{ current.id }}">
            {% if current.pinned %}&#128204; {% endif %}
            {% if current.is_paper %}&#128196; {% endif %}
            {{ current.title or 'Untitled' }}
        </div>
        <div class="current-item-domain">{{ current.url | domain }}</div>
        <div class="current-item-description">{{ current.description or 'No description' }}</div>

        {% if bookmarks|length > 1 %}
        <div class="next-up">
            <div class="next-up-header">Next Up</div>
            {% for bookmark in bookmarks[1:5] %}
            <div class="next-up-item" data-id="{{ bookmark.id }}">
                {% if bookmark.pinned %}&#128204; {% endif %}
                {% if bookmark.is_paper %}&#128196; {% endif %}
                {{ bookmark.title or 'Untitled' }}
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </section>

    <aside class="action-panel" id="action-panel">
        <button class="action-btn action-btn-primary" onclick="archiveItem({{ current.id }})">Archive</button>
        {% if not current.is_paper %}
        <button class="action-btn" onclick="markAsPaper({{ current.id }})">Mark as Paper</button>
        {% endif %}
        {% if not current.pinned %}
        <button class="action-btn" onclick="pinItem({{ current.id }})">Pin for Later</button>
        {% endif %}
        <hr style="border: none; border-top: 1px solid #eee; margin: 0.5rem 0;">
        <a href="{{ current.url }}" target="_blank" class="action-btn" style="text-align: center;">Open</a>
        <button class="action-btn" onclick="openCiteModal({{ current.id }})">Cite</button>
        <button class="action-btn" onclick="deleteItem({{ current.id }})" style="color: #c00; border-color: #c00;">Delete</button>
    </aside>
</main>

<div class="progress-bar-container">
    <div class="progress-bar">
        <div class="progress-bar-fill" style="width: {{ ((inbox_count - bookmarks|length) / inbox_count * 100) if inbox_count > 0 else 0 }}%"></div>
    </div>
    <div class="progress-text">{{ bookmarks|length }}/{{ inbox_count }} remaining</div>
</div>

{% else %}
<!-- Empty Inbox -->
<div class="archive-void">
    <div class="archive-void-message">INBOX ZERO</div>
    <p style="color: #666;">All bookmarks processed</p>
</div>
{% endif %}

{% elif view == 'archive' %}
<!-- ARCHIVE: Void -->
<div class="archive-search-bar">
    <div class="filter-icons">
        <a href="/ui/?view=archive{% if filter != 'pin' %}&filter=pin{% endif %}{% if query %}&q={{ query }}{% endif %}"
           class="filter-icon {% if filter == 'pin' %}active{% endif %}" title="Filter pins">&#128204;</a>
        <a href="/ui/?view=archive{% if filter != 'paper' %}&filter=paper{% endif %}{% if query %}&q={{ query }}{% endif %}"
           class="filter-icon {% if filter == 'paper' %}active{% endif %}" title="Filter papers">&#128196;</a>
    </div>
    <input type="text" id="search-input" placeholder="Search archive..." value="{{ query or '' }}" autocomplete="off">
    {% if query %}
    <a href="/ui/?view=archive{% if filter %}&filter={{ filter }}{% endif %}" class="clear-btn">Clear</a>
    {% endif %}
</div>

{% if query %}
<!-- Search Results -->
<main class="layout">
    <section class="bookmark-list" id="bookmark-list">
        {% if bookmarks %}
            {% for bookmark in bookmarks %}
            <div class="bookmark-item"
                 data-id="{{ bookmark.id }}"
                 data-url="{{ bookmark.url }}"
                 data-title="{{ bookmark.title or 'Untitled' }}"
                 data-description="{{ bookmark.description or '' }}"
                 data-state="{{ bookmark.state }}"
                 data-is-paper="{{ bookmark.is_paper | lower }}"
                 data-pinned="{{ bookmark.pinned | lower }}">
                <div class="bookmark-title">
                    {% if bookmark.pinned %}<span class="pin-icon">&#128204;</span>{% endif %}
                    {% if bookmark.is_paper %}<span class="paper-icon">&#128196;</span>{% endif %}
                    {{ bookmark.title or 'Untitled' }}
                </div>
                <div class="bookmark-domain">{{ bookmark.url | domain }}</div>
            </div>
            {% endfor %}
        {% else %}
            <div class="empty-state">No results found</div>
        {% endif %}
    </section>

    <aside class="detail-panel" id="detail-panel">
        <div class="empty-state">Select a bookmark to view details</div>
    </aside>
</main>

{% else %}
<!-- Empty Archive State -->
<div class="archive-void">
    <div class="archive-void-message">Search to begin</div>

    <div class="recently-archived" id="recently-archived">
        <div class="recently-archived-header">Recently Archived</div>
        <div id="recently-archived-list">Loading...</div>
    </div>
</div>
{% endif %}

{% endif %}
{% endblock %}

{% block scripts %}
<script>
(function() {
    const API_BASE = '/bookmarks';
    const currentView = '{{ view }}';

    // Archive item (mark as read)
    window.archiveItem = async function(id) {
        try {
            await fetch(`${API_BASE}/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state: 'read' })
            });
            window.location.reload();
        } catch (err) {
            console.error('Failed to archive:', err);
        }
    };

    // Mark as paper
    window.markAsPaper = async function(id) {
        try {
            await fetch(`${API_BASE}/${id}/paper`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_paper: true })
            });
            window.location.reload();
        } catch (err) {
            console.error('Failed to mark as paper:', err);
        }
    };

    // Pin item
    window.pinItem = async function(id) {
        try {
            await fetch(`${API_BASE}/${id}/pin`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pinned: true })
            });
            window.location.reload();
        } catch (err) {
            console.error('Failed to pin:', err);
        }
    };

    // Delete item
    window.deleteItem = async function(id) {
        if (!confirm('Delete this bookmark?')) return;
        try {
            await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
            window.location.reload();
        } catch (err) {
            console.error('Failed to delete:', err);
        }
    };

    // Restore item (move back to inbox)
    window.restoreItem = async function(id) {
        try {
            await fetch(`${API_BASE}/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state: 'inbox' })
            });
            window.location.reload();
        } catch (err) {
            console.error('Failed to restore:', err);
        }
    };

    // Search (debounced)
    let searchTimeout;
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const query = this.value.trim();
                const url = new URL(window.location);
                if (query) {
                    url.searchParams.set('q', query);
                } else {
                    url.searchParams.delete('q');
                }
                window.location = url;
            }, 500);
        });
    }

    // Load recently archived for archive view
    if (currentView === 'archive' && !('{{ query }}')) {
        fetch(`${API_BASE}/recently-archived?limit=5`)
            .then(res => res.json())
            .then(items => {
                const container = document.getElementById('recently-archived-list');
                if (!container) return;

                if (items.length === 0) {
                    container.innerHTML = '<div style="padding: 0.75rem; color: #666;">No archived items yet</div>';
                    return;
                }

                container.innerHTML = items.map(item => {
                    const time = item.read_at ? formatRelativeTime(new Date(item.read_at)) : '';
                    return `
                        <div class="recently-archived-item" onclick="searchFor('${(item.title || '').replace(/'/g, "\\'")}')">
                            <span>${item.title || 'Untitled'}</span>
                            <span class="recently-archived-time">${time}</span>
                        </div>
                    `;
                }).join('');
            })
            .catch(err => {
                console.error('Failed to load recently archived:', err);
                const container = document.getElementById('recently-archived-list');
                if (container) container.innerHTML = '<div style="padding: 0.75rem; color: #666;">Failed to load</div>';
            });
    }

    window.searchFor = function(query) {
        const url = new URL(window.location);
        url.searchParams.set('q', query);
        window.location = url;
    };

    function formatRelativeTime(date) {
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);

        if (diff < 3600) return Math.floor(diff / 60) + 'm';
        if (diff < 86400) return Math.floor(diff / 3600) + 'h';
        return Math.floor(diff / 86400) + 'd';
    }

    // Click handler for archive search results
    const bookmarkList = document.getElementById('bookmark-list');
    if (bookmarkList && currentView === 'archive') {
        bookmarkList.addEventListener('click', function(e) {
            const item = e.target.closest('.bookmark-item');
            if (item) selectArchiveItem(item);
        });
    }

    function selectArchiveItem(item) {
        document.querySelectorAll('.bookmark-item').forEach(el => el.classList.remove('selected'));
        item.classList.add('selected');

        const panel = document.getElementById('detail-panel');
        const data = item.dataset;
        const isPaper = data.isPaper === 'true';
        const isPinned = data.pinned === 'true';

        panel.innerHTML = `
            <button class="btn back-btn" onclick="closeDetail()">← Back</button>
            <h2 class="detail-title">${isPinned ? '&#128204; ' : ''}${isPaper ? '&#128196; ' : ''}${data.title}</h2>
            <div class="detail-domain">${getDomain(data.url)}</div>
            <p class="detail-description">${data.description || 'No description'}</p>
            <div class="detail-actions">
                <a href="${data.url}" target="_blank" class="btn btn-primary">Open</a>
                <button class="btn" onclick="openCiteModal(${data.id})">Cite</button>
                <button class="btn" onclick="restoreItem(${data.id})">Restore to Inbox</button>
                <button class="btn btn-danger" onclick="deleteItem(${data.id})">Delete</button>
            </div>
        `;
        panel.classList.add('active');
    }

    window.closeDetail = function() {
        document.getElementById('detail-panel').classList.remove('active');
        document.querySelectorAll('.bookmark-item').forEach(el => el.classList.remove('selected'));
    };

    function getDomain(url) {
        try {
            return new URL(url).hostname.replace('www.', '');
        } catch {
            return url;
        }
    }

    // Next up click handlers
    document.querySelectorAll('.next-up-item').forEach(item => {
        item.addEventListener('click', function() {
            const id = this.dataset.id;
            // For now, just reload with this item (would need backend support for proper ordering)
            window.location.reload();
        });
    });

    // Cite modal (reuse existing)
    let currentCiteBookmarkId = null;

    window.openCiteModal = async function(bookmarkId) {
        currentCiteBookmarkId = bookmarkId;
        const modal = document.getElementById('cite-modal');
        const contentDiv = document.getElementById('cite-source-content');
        const citeBtn = document.getElementById('cite-btn');

        if (!modal) return;

        modal.style.display = 'flex';
        contentDiv.innerHTML = 'Loading content...';
        citeBtn.disabled = true;

        try {
            const res = await fetch(`${API_BASE}/${bookmarkId}/content`);
            const data = await res.json();
            contentDiv.innerHTML = data.content || 'No content available';
        } catch (err) {
            contentDiv.innerHTML = 'Failed to load content';
            console.error(err);
        }
    };

    window.closeCiteModal = function() {
        const modal = document.getElementById('cite-modal');
        if (modal) modal.style.display = 'none';
        currentCiteBookmarkId = null;
    };

    window.citeSelection = async function() {
        const selection = document.getSelection();
        const quote = selection.toString().trim();

        if (!quote || !currentCiteBookmarkId) return;

        const citeBtn = document.getElementById('cite-btn');
        citeBtn.disabled = true;
        citeBtn.textContent = 'Sending...';

        try {
            const res = await fetch('/canvas/quotes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    bookmark_id: currentCiteBookmarkId,
                    quote: quote
                })
            });

            if (res.ok) {
                citeBtn.textContent = 'Cited ✓';
                setTimeout(() => {
                    closeCiteModal();
                    citeBtn.textContent = 'Cite this';
                }, 1000);
            } else {
                const error = await res.json();
                alert(`Failed: ${error.detail}`);
                citeBtn.textContent = 'Cite this';
                citeBtn.disabled = false;
            }
        } catch (err) {
            alert('Failed to cite');
            console.error(err);
            citeBtn.textContent = 'Cite this';
            citeBtn.disabled = false;
        }
    };

    // Selection change handler for cite button
    document.addEventListener('selectionchange', () => {
        const modal = document.getElementById('cite-modal');
        const contentDiv = document.getElementById('cite-source-content');
        const citeBtn = document.getElementById('cite-btn');

        if (!modal || modal.style.display === 'none') return;

        const selection = document.getSelection();
        const selectedText = selection.toString().trim();

        if (selectedText && selection.anchorNode && contentDiv) {
            const isFromContent = contentDiv.contains(selection.anchorNode);
            citeBtn.disabled = !isFromContent;
        } else {
            citeBtn.disabled = true;
        }
    });
})();
</script>
{% endblock %}
```

**Step 2: Run tests**

```bash
cd /home/ags/knowledge-system/bookmark-manager && python -m pytest tests/test_ui.py -v
```

Expected: PASS

**Step 3: Commit**

```bash
git add src/templates/index.html
git commit -m "feat(ui): implement conveyor belt inbox and void archive"
```

---

### Task 6: Add Mobile Focus View Support

**Files:**
- Modify: `src/templates/index.html` (add mobile-specific JS)

**Step 1: Add mobile detection and focus view JS**

Add to the script block in index.html, inside the IIFE:

```javascript
    // Mobile focus view for inbox
    if (currentView === 'inbox' && window.innerWidth <= 768) {
        const currentItem = document.querySelector('.current-item');
        const actionPanel = document.querySelector('.action-panel');

        if (currentItem && actionPanel) {
            // On mobile, clicking current item shows action panel overlay
            currentItem.addEventListener('click', function(e) {
                if (e.target.closest('.next-up-item')) return;
                actionPanel.classList.toggle('mobile-visible');
            });
        }
    }
```

**Step 2: Add mobile CSS for action panel**

Add to base.html CSS:

```css
        @media (max-width: 768px) {
            .action-panel {
                display: none;
                position: fixed;
                bottom: 56px;
                left: 0;
                right: 0;
                background: #fff;
                border-top: 2px solid #000;
                padding: 1rem;
                z-index: 99;
            }
            .action-panel.mobile-visible {
                display: flex;
            }
            .conveyor-layout .current-item {
                cursor: pointer;
            }
        }
```

**Step 3: Commit**

```bash
git add src/templates/index.html src/templates/base.html
git commit -m "feat(ui): add mobile support for conveyor belt inbox"
```

---

### Task 7: Update Style Guide

**Files:**
- Modify: `docs/style.md`

**Step 1: Add new components to style guide**

Append to `docs/style.md`:

```markdown

## Filter Icons

Toggle buttons for filtering by category (paper/pin).

```css
.filter-icon {
    width: 40px;
    height: 40px;
    border: 1px solid #000;
    background: #fff;
}
.filter-icon.active {
    background: #000;
    filter: invert(1);
}
```

- Default: White background, black border
- Active: Inverted (black bg, white icon via filter)
- Only one active at a time

## Progress Bar

Shows processing progress in inbox.

```css
.progress-bar {
    height: 4px;
    background: #eee;
    border: 1px solid #000;
}
.progress-bar-fill {
    background: #000;
}
```

## Conveyor Belt Layout

Inbox single-item focus view.

- Desktop: 2-column grid (content | actions)
- Mobile: Stacked, tap to show action panel
- Shows "Next Up" queue below current item
- Progress bar at bottom

## Archive Void Layout

Search-first archive design.

- Empty state: "Search to begin" + recently archived list
- Search triggers standard two-column result layout
- Filter icons work on search results
```

**Step 2: Commit**

```bash
git add docs/style.md
git commit -m "docs: update style guide with new UI components"
```

---

### Task 8: Update Tests for New UI Structure

**Files:**
- Modify: `tests/test_ui.py`

**Step 1: Update existing tests, add new ones**

Replace `tests/test_ui.py`:

```python
# tests/test_ui.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_ui_index_returns_html():
    """UI index should return HTML page"""
    response = client.get("/ui/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Bookmarks" in response.text


def test_ui_inbox_view():
    """Inbox view should show inbox header"""
    response = client.get("/ui/?view=inbox")
    assert response.status_code == 200
    assert "INBOX" in response.text


def test_ui_archive_view_has_search():
    """Archive view should have search box"""
    response = client.get("/ui/?view=archive")
    assert response.status_code == 200
    assert 'id="search-input"' in response.text


def test_ui_inbox_with_paper_filter():
    """Inbox with paper filter should work"""
    response = client.get("/ui/?view=inbox&filter=paper")
    assert response.status_code == 200


def test_ui_inbox_with_pin_filter():
    """Inbox with pin filter should work"""
    response = client.get("/ui/?view=inbox&filter=pin")
    assert response.status_code == 200


def test_ui_archive_with_filter():
    """Archive with filter should work"""
    response = client.get("/ui/?view=archive&filter=paper")
    assert response.status_code == 200


def test_ui_has_three_tabs():
    """UI should have exactly 3 tabs: Inbox, Archive, Feeds"""
    response = client.get("/ui/")
    assert response.status_code == 200
    assert 'href="/ui/?view=inbox"' in response.text
    assert 'href="/ui/?view=archive"' in response.text
    assert 'href="/ui/?view=feeds"' in response.text
    # Should NOT have papers or pinboard tabs
    assert 'view=papers' not in response.text
    assert 'view=pinboard' not in response.text


def test_ui_archive_empty_state():
    """Archive without search should show empty state"""
    response = client.get("/ui/?view=archive")
    assert response.status_code == 200
    assert "Search to begin" in response.text
    assert "Recently Archived" in response.text


def test_ui_filter_icons_present():
    """Filter icons should be present in inbox and archive"""
    inbox = client.get("/ui/?view=inbox")
    assert "filter-icon" in inbox.text

    archive = client.get("/ui/?view=archive")
    assert "filter-icon" in archive.text
```

**Step 2: Run all tests**

```bash
cd /home/ags/knowledge-system/bookmark-manager && python -m pytest tests/test_ui.py -v
```

Expected: All PASS

**Step 3: Commit**

```bash
git add tests/test_ui.py
git commit -m "test: update UI tests for new layout"
```

---

### Task 9: Deploy and Test

**Step 1: Build Docker image**

```bash
cd /home/ags/knowledge-system/bookmark-manager && docker build -t bookmark-manager:latest .
```

**Step 2: Import to k3s (requires sudo)**

```bash
docker save bookmark-manager:latest | sudo k3s ctr images import -
```

**Step 3: Restart deployment**

```bash
kubectl rollout restart deploy/bookmark-manager -n knowledge-system
kubectl rollout status deploy/bookmark-manager -n knowledge-system
```

**Step 4: Verify deployment**

```bash
kubectl logs deploy/bookmark-manager -n knowledge-system --tail=10
curl -s https://bookmark.gstoehl.dev/ui/ | grep -o 'INBOX\|Search to begin'
```

**Step 5: Manual testing checklist**

- [ ] Inbox shows conveyor belt layout with current item large
- [ ] Progress bar shows at bottom of inbox
- [ ] Filter icons toggle correctly (inverted when active)
- [ ] Archive shows "Search to begin" empty state
- [ ] Recently archived section loads
- [ ] Search in archive shows results
- [ ] Mobile: tap item shows action panel
- [ ] Mobile: bottom nav has 3 tabs only
