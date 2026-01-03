# Bookmark Manager UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a minimal web UI for browsing bookmarks and a Telegram bot for adding them.

**Architecture:** Server-rendered HTML using Jinja2 templates with minimal vanilla JavaScript. Telegram bot runs as a separate container posting to the existing API.

**Tech Stack:** FastAPI + Jinja2 templates, HTMX for interactivity, python-telegram-bot library.

---

## Part 1: Web UI Foundation

### Task 1: Add Jinja2 Dependency

**Files:**
- Modify: `pyproject.toml:19` (add to server dependencies)

**Step 1: Add jinja2 to pyproject.toml**

Add `jinja2` and `python-multipart` to server dependencies:

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
]
```

**Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add jinja2 dependency for web UI"
```

---

### Task 2: Create Base HTML Template

**Files:**
- Create: `src/templates/base.html`

**Step 1: Create templates directory and base template**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Bookmarks{% endblock %}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, Consolas, monospace;
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem;
            background: #fff;
            color: #000;
        }
        a { color: inherit; text-decoration: none; }

        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #000;
        }
        .header h1 { font-size: 1.25rem; font-weight: normal; }

        /* Tabs */
        .tabs { display: flex; gap: 1rem; }
        .tab {
            padding: 0.5rem 1rem;
            border: 1px solid #000;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .tab:hover { background: #f5f5f5; }
        .tab.active { background: #000; color: #fff; }

        /* Search */
        .search-box {
            margin-bottom: 1rem;
        }
        .search-box input {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #000;
            font-family: inherit;
            font-size: 1rem;
        }
        .search-box input:focus { outline: 2px solid #000; outline-offset: 2px; }

        /* Layout */
        .layout {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            min-height: 70vh;
        }
        @media (max-width: 768px) {
            .layout { grid-template-columns: 1fr; }
            .detail-panel { display: none; }
            .detail-panel.active { display: block; }
        }

        /* List */
        .bookmark-list { border: 1px solid #000; }
        .bookmark-item {
            padding: 0.75rem;
            cursor: pointer;
            transition: all 0.15s ease;
            border-bottom: 1px solid #eee;
        }
        .bookmark-item:last-child { border-bottom: none; }
        .bookmark-item:hover {
            background: #f5f5f5;
            box-shadow: 3px 3px 0 #000;
        }
        .bookmark-item.selected { background: #f5f5f5; }
        .bookmark-title { font-weight: 500; }
        .bookmark-domain { color: #666; font-size: 0.875rem; }

        /* Detail Panel */
        .detail-panel {
            border: 1px solid #000;
            padding: 1.5rem;
        }
        .detail-title { font-size: 1.25rem; margin-bottom: 0.5rem; }
        .detail-domain { color: #666; margin-bottom: 1rem; }
        .detail-description {
            line-height: 1.6;
            margin-bottom: 1.5rem;
            white-space: pre-wrap;
        }
        .detail-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
        .btn {
            padding: 0.5rem 1rem;
            border: 1px solid #000;
            background: #fff;
            cursor: pointer;
            font-family: inherit;
            transition: all 0.15s ease;
        }
        .btn:hover { background: #f5f5f5; }
        .btn-primary { background: #000; color: #fff; }
        .btn-primary:hover { background: #333; }
        .btn-danger { border-color: #c00; color: #c00; }
        .btn-danger:hover { background: #fee; }

        /* Empty state */
        .empty-state {
            padding: 2rem;
            text-align: center;
            color: #666;
        }

        /* Mobile back button */
        .back-btn {
            display: none;
            margin-bottom: 1rem;
        }
        @media (max-width: 768px) {
            .back-btn { display: inline-block; }
        }
    </style>
</head>
<body>
    {% block content %}{% endblock %}
    {% block scripts %}{% endblock %}
</body>
</html>
```

**Step 2: Commit**

```bash
git add src/templates/base.html
git commit -m "feat: add base HTML template with monospace styling"
```

---

### Task 3: Create Main UI Template

**Files:**
- Create: `src/templates/index.html`

**Step 1: Create the main UI template**

```html
{% extends "base.html" %}

{% block content %}
<header class="header">
    <h1>Bookmarks</h1>
    <nav class="tabs">
        <a href="/ui/?view=inbox" class="tab {% if view == 'inbox' %}active{% endif %}">Inbox</a>
        <a href="/ui/?view=archive" class="tab {% if view == 'archive' %}active{% endif %}">Archive</a>
    </nav>
</header>

{% if view == 'archive' %}
<div class="search-box">
    <input type="text"
           id="search-input"
           placeholder="Search bookmarks..."
           value="{{ query or '' }}"
           autocomplete="off">
</div>
{% endif %}

<main class="layout">
    <section class="bookmark-list" id="bookmark-list">
        {% if bookmarks %}
            {% for bookmark in bookmarks %}
            <div class="bookmark-item"
                 data-id="{{ bookmark.id }}"
                 data-url="{{ bookmark.url }}"
                 data-title="{{ bookmark.title or 'Untitled' }}"
                 data-description="{{ bookmark.description or '' }}"
                 data-state="{{ bookmark.state }}">
                <div class="bookmark-title">{{ bookmark.title or 'Untitled' }}</div>
                <div class="bookmark-domain">{{ bookmark.url | domain }}</div>
            </div>
            {% endfor %}
        {% else %}
            <div class="empty-state">
                {% if view == 'inbox' %}
                    No unread bookmarks
                {% else %}
                    No bookmarks found
                {% endif %}
            </div>
        {% endif %}
    </section>

    <aside class="detail-panel" id="detail-panel">
        <div class="empty-state">Select a bookmark to view details</div>
    </aside>
</main>
{% endblock %}

{% block scripts %}
<script>
(function() {
    const API_BASE = '/bookmarks';
    let selectedId = null;

    // Domain extraction helper
    function getDomain(url) {
        try {
            return new URL(url).hostname.replace('www.', '');
        } catch {
            return url;
        }
    }

    // Render detail panel
    function renderDetail(item) {
        const panel = document.getElementById('detail-panel');
        const data = item.dataset;
        const isRead = data.state === 'read';

        panel.innerHTML = `
            <button class="btn back-btn" onclick="closeDetail()">← Back</button>
            <h2 class="detail-title">${data.title}</h2>
            <div class="detail-domain">${getDomain(data.url)}</div>
            <p class="detail-description">${data.description || 'No description'}</p>
            <div class="detail-actions">
                <a href="${data.url}" target="_blank" class="btn btn-primary">Open</a>
                <button class="btn" onclick="toggleState(${data.id}, '${isRead ? 'inbox' : 'read'}')">
                    ${isRead ? 'Move to Inbox' : 'Mark Read'}
                </button>
                <button class="btn btn-danger" onclick="deleteBookmark(${data.id})">Delete</button>
            </div>
        `;
        panel.classList.add('active');
    }

    // Select bookmark
    function selectBookmark(item) {
        document.querySelectorAll('.bookmark-item').forEach(el => el.classList.remove('selected'));
        item.classList.add('selected');
        selectedId = item.dataset.id;
        renderDetail(item);
    }

    // Close detail (mobile)
    window.closeDetail = function() {
        document.getElementById('detail-panel').classList.remove('active');
        document.querySelectorAll('.bookmark-item').forEach(el => el.classList.remove('selected'));
        selectedId = null;
    };

    // Toggle read/inbox state
    window.toggleState = async function(id, newState) {
        try {
            const res = await fetch(`${API_BASE}/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state: newState })
            });
            if (res.ok) {
                // Remove from list and refresh
                const item = document.querySelector(`[data-id="${id}"]`);
                if (item) item.remove();
                document.getElementById('detail-panel').innerHTML =
                    '<div class="empty-state">Select a bookmark to view details</div>';
            }
        } catch (err) {
            console.error('Failed to update:', err);
        }
    };

    // Delete bookmark
    window.deleteBookmark = async function(id) {
        if (!confirm('Delete this bookmark?')) return;
        try {
            const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
            if (res.ok) {
                const item = document.querySelector(`[data-id="${id}"]`);
                if (item) item.remove();
                document.getElementById('detail-panel').innerHTML =
                    '<div class="empty-state">Select a bookmark to view details</div>';
            }
        } catch (err) {
            console.error('Failed to delete:', err);
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

    // Click handlers
    document.getElementById('bookmark-list').addEventListener('click', function(e) {
        const item = e.target.closest('.bookmark-item');
        if (item) selectBookmark(item);
    });
})();
</script>
{% endblock %}
```

**Step 2: Commit**

```bash
git add src/templates/index.html
git commit -m "feat: add main UI template with list and detail views"
```

---

### Task 4: Create UI Router

**Files:**
- Create: `src/routers/ui.py`
- Create: `tests/test_ui.py`

**Step 1: Write failing test for UI routes**

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
    """Inbox view should show inbox bookmarks"""
    response = client.get("/ui/?view=inbox")
    assert response.status_code == 200
    assert 'class="tab active"' in response.text
    assert "Inbox" in response.text


def test_ui_archive_view_has_search():
    """Archive view should have search box"""
    response = client.get("/ui/?view=archive")
    assert response.status_code == 200
    assert 'id="search-input"' in response.text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui.py -v`
Expected: FAIL - no module or 404

**Step 3: Create UI router**

```python
# src/routers/ui.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database import get_db
from src.models import Bookmark, BookmarkState
from pathlib import Path
from urllib.parse import urlparse

router = APIRouter(prefix="/ui", tags=["ui"])

# Setup templates
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# Custom filter for domain extraction
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
    session: AsyncSession = Depends(get_db)
):
    """Main UI page"""
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

**Step 4: Register router in main.py**

Add to `src/main.py`:

```python
from src.routers import bookmarks, search, backup, ui

# ... existing code ...

# Register routers
app.include_router(bookmarks.router)
app.include_router(search.router)
app.include_router(backup.router)
app.include_router(ui.router)
```

**Step 5: Add root redirect**

Add to `src/main.py` after the health check:

```python
from fastapi.responses import RedirectResponse

@app.get("/")
async def root():
    return RedirectResponse(url="/ui/")
```

**Step 6: Run tests to verify they pass**

Run: `pytest tests/test_ui.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/routers/ui.py tests/test_ui.py src/main.py
git commit -m "feat: add UI router with inbox/archive views"
```

---

### Task 5: Add Edit Title Functionality

**Files:**
- Modify: `src/templates/index.html`
- Modify: `src/routers/bookmarks.py`
- Create: `src/schemas.py` (add BookmarkTitleUpdate)

**Step 1: Add title update schema**

Add to `src/schemas.py`:

```python
class BookmarkTitleUpdate(BaseModel):
    title: str
```

**Step 2: Add title update endpoint**

Add to `src/routers/bookmarks.py`:

```python
from src.schemas import BookmarkCreate, BookmarkUpdate, BookmarkDescriptionUpdate, BookmarkTitleUpdate, BookmarkResponse

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
```

**Step 3: Add edit functionality to JavaScript**

Add to the JavaScript in `src/templates/index.html`, inside the IIFE:

```javascript
    // Edit title
    window.editTitle = async function(id, currentTitle) {
        const newTitle = prompt('Edit title:', currentTitle);
        if (newTitle === null || newTitle === currentTitle) return;

        try {
            const res = await fetch(`${API_BASE}/${id}/title`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            });
            if (res.ok) {
                // Update the item in the list
                const item = document.querySelector(`[data-id="${id}"]`);
                if (item) {
                    item.dataset.title = newTitle;
                    item.querySelector('.bookmark-title').textContent = newTitle;
                    renderDetail(item);
                }
            }
        } catch (err) {
            console.error('Failed to update title:', err);
        }
    };
```

Update the `renderDetail` function to include Edit button:

```javascript
            <div class="detail-actions">
                <a href="${data.url}" target="_blank" class="btn btn-primary">Open</a>
                <button class="btn" onclick="editTitle(${data.id}, '${data.title.replace(/'/g, "\\'")}')">Edit</button>
                <button class="btn" onclick="toggleState(${data.id}, '${isRead ? 'inbox' : 'read'}')">
                    ${isRead ? 'Move to Inbox' : 'Mark Read'}
                </button>
                <button class="btn btn-danger" onclick="deleteBookmark(${data.id})">Delete</button>
            </div>
```

**Step 4: Commit**

```bash
git add src/schemas.py src/routers/bookmarks.py src/templates/index.html
git commit -m "feat: add edit title functionality"
```

---

## Part 2: Telegram Bot

### Task 6: Add Telegram Bot Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add bot optional dependency group**

```toml
bot = [
    "python-telegram-bot==21.7",
    "httpx==0.27.2",
]
```

**Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add python-telegram-bot dependency"
```

---

### Task 7: Create Telegram Bot

**Files:**
- Create: `bot/__init__.py`
- Create: `bot/main.py`

**Step 1: Create bot module**

```python
# bot/__init__.py
```

```python
# bot/main.py
import os
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://localhost:8000")
ALLOWED_USERS = os.getenv("ALLOWED_TELEGRAM_USERS", "").split(",")


def is_authorized(user_id: int) -> bool:
    """Check if user is authorized"""
    if not ALLOWED_USERS or ALLOWED_USERS == [""]:
        return True  # No restrictions if not configured
    return str(user_id) in ALLOWED_USERS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Not authorized.")
        return

    await update.message.reply_text(
        "Send me a URL to save it as a bookmark.\n\n"
        "I'll fetch the title and generate a summary automatically."
    )


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle URL messages"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Not authorized.")
        return

    text = update.message.text.strip()

    # Extract URL from text (handle shared URLs with titles)
    url = None
    for word in text.split():
        if word.startswith(("http://", "https://")):
            url = word
            break

    if not url:
        await update.message.reply_text("Please send a valid URL starting with http:// or https://")
        return

    # Send to API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/bookmarks",
                json={"url": url},
                timeout=30.0
            )

        if response.status_code == 201:
            data = response.json()
            title = data.get("title") or "Untitled"
            domain = url.split("/")[2].replace("www.", "")
            await update.message.reply_text(f"✓ Saved: {title} — {domain}")
        elif response.status_code == 409:
            await update.message.reply_text("Already saved!")
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")
            await update.message.reply_text("Failed to save bookmark. Try again later.")
    except Exception as e:
        logger.error(f"Error saving bookmark: {e}")
        await update.message.reply_text("Failed to save bookmark. Try again later.")


def main() -> None:
    """Start the bot"""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return

    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    # Run bot
    logger.info("Starting Telegram bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add bot/__init__.py bot/main.py
git commit -m "feat: add Telegram bot for bookmark submission"
```

---

### Task 8: Create Bot Dockerfile

**Files:**
- Create: `bot/Dockerfile`
- Create: `bot/requirements.txt`

**Step 1: Create requirements.txt**

```
python-telegram-bot==21.7
httpx==0.27.2
```

**Step 2: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

**Step 3: Commit**

```bash
git add bot/Dockerfile bot/requirements.txt
git commit -m "feat: add Dockerfile for Telegram bot"
```

---

### Task 9: Add Bot to Docker Compose

**Files:**
- Modify: `docker-compose.yml`
- Modify: `docker-compose.dev.yml`

**Step 1: Add telegram-bot service to docker-compose.yml**

```yaml
  telegram-bot:
    build: ./bot
    container_name: bookmark-manager-bot
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - API_URL=http://api:8000
      - ALLOWED_TELEGRAM_USERS=${ALLOWED_TELEGRAM_USERS:-}
    depends_on:
      - api
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**Step 2: Add to docker-compose.dev.yml**

Add the same service but with build context and volume mount for development:

```yaml
  telegram-bot:
    build: ./bot
    container_name: bookmark-manager-bot-dev
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - API_URL=http://api:8000
      - ALLOWED_TELEGRAM_USERS=${ALLOWED_TELEGRAM_USERS:-}
    depends_on:
      - api
    volumes:
      - ./bot:/app
```

**Step 3: Commit**

```bash
git add docker-compose.yml docker-compose.dev.yml
git commit -m "feat: add Telegram bot to docker-compose"
```

---

### Task 10: Add Bot Tests

**Files:**
- Create: `tests/test_telegram_bot.py`

**Step 1: Write unit tests for bot**

```python
# tests/test_telegram_bot.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add bot to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update"""
    update = MagicMock()
    update.effective_user.id = 123456
    update.message.text = "https://example.com/article"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create a mock context"""
    return MagicMock()


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Test /start command responds with help text"""
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test", "ALLOWED_TELEGRAM_USERS": ""}):
        from bot.main import start
        await start(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "URL" in call_args


@pytest.mark.asyncio
async def test_handle_url_success(mock_update, mock_context):
    """Test successful URL submission"""
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test", "ALLOWED_TELEGRAM_USERS": ""}):
        # Reload module to pick up env vars
        import importlib
        import bot.main
        importlib.reload(bot.main)
        from bot.main import handle_url

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"title": "Example Article"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            await handle_url(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "✓ Saved" in call_args


@pytest.mark.asyncio
async def test_handle_url_duplicate(mock_update, mock_context):
    """Test duplicate URL returns 'Already saved'"""
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test", "ALLOWED_TELEGRAM_USERS": ""}):
        import importlib
        import bot.main
        importlib.reload(bot.main)
        from bot.main import handle_url

        mock_response = MagicMock()
        mock_response.status_code = 409

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            await handle_url(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Already saved" in call_args


@pytest.mark.asyncio
async def test_unauthorized_user(mock_update, mock_context):
    """Test unauthorized user is rejected"""
    mock_update.effective_user.id = 999999

    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test", "ALLOWED_TELEGRAM_USERS": "123456"}):
        import importlib
        import bot.main
        importlib.reload(bot.main)
        from bot.main import start

        await start(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Not authorized" in call_args
```

**Step 2: Run tests**

Run: `pytest tests/test_telegram_bot.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_telegram_bot.py
git commit -m "test: add unit tests for Telegram bot"
```

---

### Task 11: Run Full Test Suite

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 2: Final commit if any cleanup needed**

```bash
git status
# If clean, we're done
```

---

## Summary

| Component | Files | Lines (est) |
|-----------|-------|-------------|
| Templates | 2 | ~200 |
| UI Router | 1 | ~60 |
| Telegram Bot | 2 | ~100 |
| Docker | 3 | ~40 |
| Tests | 2 | ~100 |

**Total: ~500 lines**

## Post-Implementation

1. Set `TELEGRAM_BOT_TOKEN` environment variable
2. Optionally set `ALLOWED_TELEGRAM_USERS` (comma-separated user IDs)
3. Deploy with `docker-compose up -d`
4. Message @YourBot on Telegram to test
