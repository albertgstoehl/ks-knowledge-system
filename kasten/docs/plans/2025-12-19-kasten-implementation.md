# Kasten Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a minimal Zettelkasten browser with no search - navigate by following links, view notes with node visualization, push to Canvas workspace.

**Architecture:** FastAPI backend with SQLite for link indexing. Markdown files are source of truth. Scanner parses files to build link graph. Simple SVG for node visualization. htmx for navigation.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy, aiosqlite, Jinja2, htmx, SVG, Playwright

---

## Phase 1: Project Setup

### Task 1: Initialize Project Structure

**Files:**
- Create: `kasten/pyproject.toml`
- Create: `kasten/src/__init__.py`
- Create: `kasten/src/routers/__init__.py`
- Create: `kasten/tests/__init__.py`
- Create: `kasten/static/.gitkeep`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "kasten"
version = "0.1.0"
description = "Minimal Zettelkasten browser - navigate by links"
requires-python = ">=3.10"

[project.optional-dependencies]
server = [
    "fastapi==0.115.0",
    "uvicorn[standard]==0.31.0",
    "pydantic==2.9.2",
    "sqlalchemy==2.0.35",
    "aiosqlite==0.20.0",
    "jinja2==3.1.4",
    "httpx==0.27.2",
]
dev = [
    "pytest==8.3.3",
    "pytest-asyncio==0.24.0",
    "playwright==1.40.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"
```

**Step 2: Create directory structure**

```bash
cd /home/ags/knowledge-system
mkdir -p kasten/src/routers kasten/src/templates kasten/static kasten/tests
touch kasten/src/__init__.py kasten/src/routers/__init__.py kasten/tests/__init__.py
touch kasten/static/.gitkeep
```

**Step 3: Commit**

```bash
cd kasten && git init && git add -A && git commit -m "chore: initialize kasten project structure"
```

---

### Task 2: Database Setup

**Files:**
- Create: `kasten/src/database.py`
- Test: `kasten/tests/test_database.py`

**Step 1: Write the failing test**

```python
# kasten/tests/test_database.py
import pytest
from src.database import init_db, get_db

@pytest.mark.asyncio
async def test_init_db_creates_tables():
    await init_db("sqlite+aiosqlite:///:memory:")
    async for session in get_db():
        result = await session.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in result.fetchall()]
        assert "notes" in tables
        assert "links" in tables
        break
```

**Step 2: Run test to verify it fails**

Run: `cd kasten && python -m pytest tests/test_database.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write database.py**

```python
# kasten/src/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from typing import AsyncGenerator
import os

class Base(DeclarativeBase):
    pass

engine = None
async_session_maker = None

async def init_db(database_url: str = None) -> None:
    global engine, async_session_maker

    if database_url is None:
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/kasten.db")

    if database_url.startswith("sqlite:///"):
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

    if database_url.startswith("sqlite+aiosqlite:///") and not database_url.endswith(":memory:"):
        db_path = database_url.replace("sqlite+aiosqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    engine = create_async_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    from src import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
```

**Step 4: Run test to verify it passes**

Run: `cd kasten && python -m pytest tests/test_database.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add -A && git commit -m "feat: add database setup"
```

---

### Task 3: Data Models

**Files:**
- Create: `kasten/src/models.py`
- Modify: `kasten/tests/test_database.py`

**Step 1: Write the failing test**

```python
# kasten/tests/test_database.py (add to existing)
@pytest.mark.asyncio
async def test_note_model():
    await init_db("sqlite+aiosqlite:///:memory:")
    from src.models import Note
    async for session in get_db():
        note = Note(id="1219a", title="Test note", file_path="1219a.md")
        session.add(note)
        await session.commit()
        await session.refresh(note)
        assert note.id == "1219a"
        assert note.title == "Test note"
        break

@pytest.mark.asyncio
async def test_link_model():
    await init_db("sqlite+aiosqlite:///:memory:")
    from src.models import Note, Link
    async for session in get_db():
        note1 = Note(id="1219a", title="Note A", file_path="1219a.md")
        note2 = Note(id="1219b", title="Note B", file_path="1219b.md")
        session.add_all([note1, note2])
        await session.commit()

        link = Link(from_note_id="1219a", to_note_id="1219b")
        session.add(link)
        await session.commit()
        assert link.id is not None
        break
```

**Step 2: Run test to verify it fails**

Run: `cd kasten && python -m pytest tests/test_database.py -v`
Expected: FAIL - ImportError

**Step 3: Write models.py**

```python
# kasten/src/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from src.database import Base

class Note(Base):
    """Note metadata - content lives in markdown files"""
    __tablename__ = "notes"

    id = Column(String(10), primary_key=True)  # e.g., "1219a"
    title = Column(String(255))
    file_path = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())

class Link(Base):
    """Links between notes"""
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_note_id = Column(String(10), ForeignKey("notes.id"), nullable=False)
    to_note_id = Column(String(10), ForeignKey("notes.id"), nullable=False)
```

**Step 4: Run test to verify it passes**

Run: `cd kasten && python -m pytest tests/test_database.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add -A && git commit -m "feat: add Note and Link models"
```

---

### Task 4: Markdown Scanner

**Files:**
- Create: `kasten/src/scanner.py`
- Test: `kasten/tests/test_scanner.py`

**Step 1: Write the failing test**

```python
# kasten/tests/test_scanner.py
import pytest
import tempfile
import os
from src.scanner import parse_note, extract_links, scan_notes_directory

def test_extract_links():
    content = "This links to [[1219a]] and [[1219b]] notes."
    links = extract_links(content)
    assert links == ["1219a", "1219b"]

def test_extract_links_empty():
    content = "No links here."
    links = extract_links(content)
    assert links == []

def test_parse_note():
    content = "First line is title\n\nMore content [[1219b]] here."
    note_id, title, links = parse_note("1219a.md", content)
    assert note_id == "1219a"
    assert title == "First line is title"
    assert links == ["1219b"]

def test_scan_notes_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        with open(os.path.join(tmpdir, "1219a.md"), "w") as f:
            f.write("Note A title\n\nLinks to [[1219b]]")
        with open(os.path.join(tmpdir, "1219b.md"), "w") as f:
            f.write("Note B title\n\nNo links here")

        notes, links = scan_notes_directory(tmpdir)

        assert len(notes) == 2
        assert notes[0]["id"] == "1219a"
        assert notes[0]["title"] == "Note A title"
        assert len(links) == 1
        assert links[0] == ("1219a", "1219b")
```

**Step 2: Run test to verify it fails**

Run: `cd kasten && python -m pytest tests/test_scanner.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write scanner.py**

```python
# kasten/src/scanner.py
import re
import os
from pathlib import Path

LINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')
NOTE_ID_PATTERN = re.compile(r'^(\d{4}[a-z]+)\.md$')

def extract_links(content: str) -> list[str]:
    """Extract all [[id]] links from content."""
    return LINK_PATTERN.findall(content)

def parse_note(filename: str, content: str) -> tuple[str, str, list[str]]:
    """Parse a note file, return (id, title, links)."""
    match = NOTE_ID_PATTERN.match(filename)
    if not match:
        return None, None, []

    note_id = match.group(1)
    lines = content.strip().split('\n')
    title = lines[0].strip() if lines else ""
    links = extract_links(content)

    return note_id, title, links

def scan_notes_directory(directory: str) -> tuple[list[dict], list[tuple[str, str]]]:
    """Scan directory for markdown notes, return notes and links."""
    notes = []
    links = []

    for filename in os.listdir(directory):
        if not filename.endswith('.md'):
            continue

        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        note_id, title, note_links = parse_note(filename, content)
        if note_id is None:
            continue

        notes.append({
            "id": note_id,
            "title": title,
            "file_path": filename
        })

        for target_id in note_links:
            links.append((note_id, target_id))

    # Sort by id
    notes.sort(key=lambda n: n["id"])
    return notes, links
```

**Step 4: Run test to verify it passes**

Run: `cd kasten && python -m pytest tests/test_scanner.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add -A && git commit -m "feat: add markdown scanner with link extraction"
```

---

## Phase 2: API Endpoints

### Task 5: Notes API

**Files:**
- Create: `kasten/src/routers/api.py`
- Create: `kasten/src/main.py`
- Test: `kasten/tests/test_api.py`

**Step 1: Write the failing test**

```python
# kasten/tests/test_api.py
import pytest
import tempfile
import os
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import init_db

@pytest.fixture
def notes_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "1219a.md"), "w") as f:
            f.write("Note A title\n\nLinks to [[1219b]]")
        with open(os.path.join(tmpdir, "1219b.md"), "w") as f:
            f.write("Note B title\n\nNo outgoing links")
        os.environ["NOTES_PATH"] = tmpdir
        yield tmpdir

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db("sqlite+aiosqlite:///:memory:")

@pytest.mark.asyncio
async def test_get_notes(notes_dir):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First reindex
        await client.post("/api/reindex")

        response = await client.get("/api/notes")
        assert response.status_code == 200
        notes = response.json()
        assert len(notes) == 2

@pytest.mark.asyncio
async def test_get_note(notes_dir):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/reindex")

        response = await client.get("/api/notes/1219a")
        assert response.status_code == 200
        note = response.json()
        assert note["id"] == "1219a"
        assert "content" in note

@pytest.mark.asyncio
async def test_get_entry_points(notes_dir):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/reindex")

        response = await client.get("/api/notes/entry-points")
        assert response.status_code == 200
        entries = response.json()
        # 1219a has outgoing link but 1219b has backlink, so 1219a is entry point
        assert any(e["id"] == "1219a" for e in entries)

@pytest.mark.asyncio
async def test_get_random(notes_dir):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/reindex")

        response = await client.get("/api/notes/random")
        assert response.status_code == 200
        note = response.json()
        assert note["id"] in ["1219a", "1219b"]

@pytest.mark.asyncio
async def test_get_links(notes_dir):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/reindex")

        response = await client.get("/api/notes/1219a/links")
        assert response.status_code == 200
        links = response.json()
        assert "forward" in links
        assert "back" in links
        assert "1219b" in [l["id"] for l in links["forward"]]
```

**Step 2: Run test to verify it fails**

Run: `cd kasten && python -m pytest tests/test_api.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write api router**

```python
# kasten/src/routers/api.py
import os
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.database import get_db
from src.models import Note, Link
from src.scanner import scan_notes_directory

router = APIRouter(prefix="/api", tags=["api"])

def get_notes_path():
    return os.getenv("NOTES_PATH", "/app/notes")

@router.post("/reindex")
async def reindex(session: AsyncSession = Depends(get_db)):
    """Rescan notes directory and rebuild index."""
    notes_path = get_notes_path()

    # Clear existing data
    await session.execute(Link.__table__.delete())
    await session.execute(Note.__table__.delete())

    # Scan and insert
    notes, links = scan_notes_directory(notes_path)

    for note_data in notes:
        note = Note(**note_data)
        session.add(note)

    await session.commit()

    # Add links (only for notes that exist)
    note_ids = {n["id"] for n in notes}
    for from_id, to_id in links:
        if from_id in note_ids and to_id in note_ids:
            link = Link(from_note_id=from_id, to_note_id=to_id)
            session.add(link)

    await session.commit()
    return {"status": "ok", "notes": len(notes), "links": len(links)}

@router.get("/notes")
async def list_notes(session: AsyncSession = Depends(get_db)):
    """List all notes."""
    result = await session.execute(select(Note).order_by(Note.id.desc()))
    notes = result.scalars().all()
    return [{"id": n.id, "title": n.title} for n in notes]

@router.get("/notes/entry-points")
async def get_entry_points(session: AsyncSession = Depends(get_db)):
    """Get notes with only outgoing links (no backlinks)."""
    # Notes that have outgoing links but no incoming links
    has_outgoing = select(Link.from_note_id).distinct()
    has_incoming = select(Link.to_note_id).distinct()

    result = await session.execute(
        select(Note).where(
            Note.id.in_(has_outgoing),
            Note.id.notin_(has_incoming)
        )
    )
    notes = result.scalars().all()
    return [{"id": n.id, "title": n.title} for n in notes]

@router.get("/notes/random")
async def get_random_note(session: AsyncSession = Depends(get_db)):
    """Get a random note."""
    result = await session.execute(select(Note))
    notes = result.scalars().all()
    if not notes:
        raise HTTPException(status_code=404, detail="No notes found")
    note = random.choice(notes)
    return {"id": note.id, "title": note.title}

@router.get("/notes/{note_id}")
async def get_note(note_id: str, session: AsyncSession = Depends(get_db)):
    """Get a specific note with content."""
    result = await session.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Read content from file
    notes_path = get_notes_path()
    filepath = os.path.join(notes_path, note.file_path)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    return {"id": note.id, "title": note.title, "content": content}

@router.get("/notes/{note_id}/links")
async def get_note_links(note_id: str, session: AsyncSession = Depends(get_db)):
    """Get forward and back links for a note."""
    # Forward links (this note links to)
    forward_result = await session.execute(
        select(Note).join(Link, Note.id == Link.to_note_id).where(Link.from_note_id == note_id)
    )
    forward = forward_result.scalars().all()

    # Back links (notes that link to this)
    back_result = await session.execute(
        select(Note).join(Link, Note.id == Link.from_note_id).where(Link.to_note_id == note_id)
    )
    back = back_result.scalars().all()

    return {
        "forward": [{"id": n.id, "title": n.title} for n in forward],
        "back": [{"id": n.id, "title": n.title} for n in back]
    }
```

**Step 4: Write main.py**

```python
# kasten/src/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.routers import api

app = FastAPI(title="Kasten", version="0.1.0")

@app.on_event("startup")
async def startup():
    from src.database import init_db
    await init_db()

@app.get("/health")
async def health():
    return {"status": "healthy"}

app.include_router(api.router)
```

**Step 5: Run test to verify it passes**

Run: `cd kasten && python -m pytest tests/test_api.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add -A && git commit -m "feat: add notes API (list, get, entry-points, random, links)"
```

---

## Phase 3: UI

### Task 6: Base Template

**Files:**
- Create: `kasten/src/templates/base.html`

**Step 1: Create base.html**

```html
<!-- kasten/src/templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Kasten{% endblock %}</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, Consolas, monospace;
            max-width: 800px;
            margin: 0 auto;
            padding: 1rem;
            background: #fff;
            color: #000;
        }
        a { color: inherit; }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #000;
        }
        .header h1 { font-size: 1.25rem; font-weight: normal; }

        .btn {
            padding: 0.5rem 1rem;
            border: 1px solid #000;
            background: #fff;
            cursor: pointer;
            font-family: inherit;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { background: #f5f5f5; }
        .btn-primary { background: #000; color: #fff; }
        .btn-primary:hover { background: #333; }

        .nav-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid #000;
            margin-bottom: 1rem;
        }
        .nav-btn {
            padding: 0.5rem 1rem;
            border: 1px solid #000;
            background: #fff;
            cursor: pointer;
            font-family: inherit;
            text-decoration: none;
        }
        .nav-btn:hover { background: #f5f5f5; }
        .nav-btn:disabled { opacity: 0.3; cursor: not-allowed; }

        .note-content {
            line-height: 1.6;
            padding: 1rem 0;
            border-bottom: 1px solid #000;
            margin-bottom: 1rem;
        }
        .note-content a { color: #000; text-decoration: underline; }

        .entry-list { list-style: none; }
        .entry-item {
            padding: 0.75rem;
            border: 1px solid #000;
            margin-bottom: 0.5rem;
            cursor: pointer;
        }
        .entry-item:hover { background: #f5f5f5; }
        .entry-item a { text-decoration: none; display: block; }
        .entry-id { color: #666; font-size: 0.875rem; }

        .graph-container {
            display: flex;
            justify-content: center;
            padding: 1rem 0;
        }
        .graph-container svg { max-width: 100%; }

        {% block extra_styles %}{% endblock %}
    </style>
</head>
<body>
    <header class="header">
        <h1><a href="/" style="text-decoration:none">KASTEN</a></h1>
    </header>

    {% block content %}{% endblock %}

    {% block scripts %}{% endblock %}
</body>
</html>
```

**Step 2: Commit**

```bash
git add -A && git commit -m "feat: add base template with brutalist styling"
```

---

### Task 7: Landing Page

**Files:**
- Create: `kasten/src/templates/landing.html`
- Create: `kasten/src/routers/ui.py`
- Modify: `kasten/src/main.py`

**Step 1: Create landing.html**

```html
<!-- kasten/src/templates/landing.html -->
{% extends "base.html" %}

{% block content %}
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
    <h2 style="font-weight: normal;">Entry Points</h2>
    <a href="/random" class="btn">Feeling Lucky</a>
</div>

{% if entry_points %}
<ul class="entry-list">
    {% for note in entry_points %}
    <li class="entry-item">
        <a href="/note/{{ note.id }}">
            <span class="entry-id">{{ note.id }}</span>
            <span>{{ note.title }}</span>
        </a>
    </li>
    {% endfor %}
</ul>
{% else %}
<p style="color: #666;">No entry points found. Notes with only outgoing links appear here.</p>
{% endif %}
{% endblock %}
```

**Step 2: Create ui router**

```python
# kasten/src/routers/ui.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database import get_db
from src.models import Note, Link
from src.routers.api import get_entry_points, get_random_note, get_note, get_note_links
import os
import re

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory="src/templates")

def render_links(content: str) -> str:
    """Convert [[id]] to clickable links."""
    def replace_link(match):
        note_id = match.group(1)
        return f'<a href="/note/{note_id}">{note_id}</a>'
    return re.sub(r'\[\[([^\]]+)\]\]', replace_link, content)

@router.get("/")
async def landing(request: Request, session: AsyncSession = Depends(get_db)):
    # Get entry points
    has_outgoing = select(Link.from_note_id).distinct()
    has_incoming = select(Link.to_note_id).distinct()

    result = await session.execute(
        select(Note).where(
            Note.id.in_(has_outgoing),
            Note.id.notin_(has_incoming)
        ).order_by(Note.id.desc())
    )
    entry_points = [{"id": n.id, "title": n.title} for n in result.scalars().all()]

    return templates.TemplateResponse("landing.html", {
        "request": request,
        "entry_points": entry_points
    })

@router.get("/random")
async def random_redirect(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Note))
    notes = result.scalars().all()
    if not notes:
        return RedirectResponse(url="/")
    import random
    note = random.choice(notes)
    return RedirectResponse(url=f"/note/{note.id}")

@router.get("/note/{note_id}")
async def note_view(request: Request, note_id: str, session: AsyncSession = Depends(get_db)):
    # Get note
    result = await session.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        return RedirectResponse(url="/")

    # Read content
    notes_path = os.getenv("NOTES_PATH", "/app/notes")
    filepath = os.path.join(notes_path, note.file_path)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        content = "(Note file not found)"

    # Render links
    content_html = render_links(content)

    # Get links
    forward_result = await session.execute(
        select(Note).join(Link, Note.id == Link.to_note_id).where(Link.from_note_id == note_id)
    )
    forward = [{"id": n.id, "title": n.title} for n in forward_result.scalars().all()]

    back_result = await session.execute(
        select(Note).join(Link, Note.id == Link.from_note_id).where(Link.to_note_id == note_id)
    )
    back = [{"id": n.id, "title": n.title} for n in back_result.scalars().all()]

    return templates.TemplateResponse("note.html", {
        "request": request,
        "note": {"id": note.id, "title": note.title},
        "content": content_html,
        "forward": forward,
        "back": back
    })
```

**Step 3: Update main.py**

```python
# kasten/src/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.routers import api, ui

app = FastAPI(title="Kasten", version="0.1.0")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup():
    from src.database import init_db
    await init_db()

@app.get("/health")
async def health():
    return {"status": "healthy"}

app.include_router(api.router)
app.include_router(ui.router)
```

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: add landing page with entry points"
```

---

### Task 8: Note View with Graph

**Files:**
- Create: `kasten/src/templates/note.html`
- Create: `kasten/static/graph.js`

**Step 1: Create note.html**

```html
<!-- kasten/src/templates/note.html -->
{% extends "base.html" %}

{% block title %}{{ note.id }} - Kasten{% endblock %}

{% block content %}
<nav class="nav-bar">
    <button class="nav-btn" onclick="history.back()" title="Back">←</button>
    <a href="javascript:void(0)" class="btn btn-primary" onclick="pushToWorkspace()">Push to Workspace</a>
    <button class="nav-btn" onclick="history.forward()" title="Forward">→</button>
</nav>

<article class="note-content">
    {{ content | safe }}
</article>

<div class="graph-container">
    <svg id="note-graph" width="300" height="200"></svg>
</div>
{% endblock %}

{% block scripts %}
<script>
const noteId = "{{ note.id }}";
const forward = {{ forward | tojson }};
const back = {{ back | tojson }};

function pushToWorkspace() {
    fetch('/api/notes/{{ note.id }}')
        .then(r => r.json())
        .then(note => {
            return fetch('https://canvas.gstoehl.dev/api/workspace/notes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    km_note_id: note.id,
                    content: note.content
                })
            });
        })
        .then(r => {
            if (r.ok) alert('Pushed to workspace!');
            else alert('Failed to push');
        })
        .catch(() => alert('Failed to connect to Canvas'));
}

// Simple SVG graph
(function() {
    const svg = document.getElementById('note-graph');
    const width = 300, height = 200;
    const cx = width / 2, cy = height / 2;
    const radius = 60;

    // Current node (center, filled)
    const current = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    current.setAttribute('cx', cx);
    current.setAttribute('cy', cy);
    current.setAttribute('r', 20);
    current.setAttribute('fill', '#000');
    svg.appendChild(current);

    // Label for current
    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    label.setAttribute('x', cx);
    label.setAttribute('y', cy + 35);
    label.setAttribute('text-anchor', 'middle');
    label.setAttribute('font-size', '10');
    label.setAttribute('font-family', 'monospace');
    label.textContent = noteId;
    svg.appendChild(label);

    // Back links (top)
    back.forEach((note, i) => {
        const angle = Math.PI + (Math.PI / (back.length + 1)) * (i + 1);
        const x = cx + Math.cos(angle) * radius;
        const y = cy + Math.sin(angle) * radius;

        // Line
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', cx);
        line.setAttribute('y1', cy);
        line.setAttribute('x2', x);
        line.setAttribute('y2', y);
        line.setAttribute('stroke', '#000');
        svg.appendChild(line);

        // Circle
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', x);
        circle.setAttribute('cy', y);
        circle.setAttribute('r', 15);
        circle.setAttribute('fill', '#fff');
        circle.setAttribute('stroke', '#000');
        circle.setAttribute('stroke-width', '2');
        circle.style.cursor = 'pointer';
        circle.onclick = () => window.location.href = '/note/' + note.id;

        // Hover title
        const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
        title.textContent = note.id + ': ' + note.title;
        circle.appendChild(title);

        svg.appendChild(circle);
    });

    // Forward links (bottom)
    forward.forEach((note, i) => {
        const angle = (Math.PI / (forward.length + 1)) * (i + 1);
        const x = cx + Math.cos(angle) * radius;
        const y = cy + Math.sin(angle) * radius;

        // Line
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', cx);
        line.setAttribute('y1', cy);
        line.setAttribute('x2', x);
        line.setAttribute('y2', y);
        line.setAttribute('stroke', '#000');
        svg.appendChild(line);

        // Circle
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', x);
        circle.setAttribute('cy', y);
        circle.setAttribute('r', 15);
        circle.setAttribute('fill', '#fff');
        circle.setAttribute('stroke', '#000');
        circle.setAttribute('stroke-width', '2');
        circle.style.cursor = 'pointer';
        circle.onclick = () => window.location.href = '/note/' + note.id;

        const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
        title.textContent = note.id + ': ' + note.title;
        circle.appendChild(title);

        svg.appendChild(circle);
    });
})();
</script>
{% endblock %}
```

**Step 2: Commit**

```bash
git add -A && git commit -m "feat: add note view with SVG graph visualization"
```

---

## Phase 4: Deployment

### Task 9: Docker Setup

**Files:**
- Create: `kasten/Dockerfile`
- Create: `kasten/docker-compose.yml`
- Create: `kasten/Caddyfile`
- Create: `kasten/requirements.txt`

**Step 1: Create requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.31.0
pydantic==2.9.2
sqlalchemy==2.0.35
aiosqlite==0.20.0
jinja2==3.1.4
httpx==0.27.2
```

**Step 2: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY static/ static/

RUN mkdir -p data

ENV NOTES_PATH=/app/notes

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 3: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  kasten:
    build: .
    container_name: kasten
    restart: unless-stopped
    networks:
      - app-network
    volumes:
      - ./data:/app/data
      - /home/ags/notes:/app/notes:ro
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./data/kasten.db
      - NOTES_PATH=/app/notes

  caddy:
    image: caddy:2
    container_name: kasten-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - app-network

networks:
  app-network:
    external: true

volumes:
  caddy_data:
  caddy_config:
```

**Step 4: Create Caddyfile**

```
kasten.gstoehl.dev {
    reverse_proxy kasten:8000
}
```

**Step 5: Commit**

```bash
git add -A && git commit -m "chore: add Docker and Caddy configuration"
```

---

### Task 10: Playwright Tests

**Files:**
- Create: `kasten/tests/test_ui.py`

**Step 1: Write Playwright tests**

```python
# kasten/tests/test_ui.py
import pytest
from playwright.async_api import async_playwright
import subprocess
import time
import tempfile
import os

@pytest.fixture(scope="module")
def server():
    """Start the server for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test notes
        with open(os.path.join(tmpdir, "1219a.md"), "w") as f:
            f.write("Test Note A\n\nLinks to [[1219b]]")
        with open(os.path.join(tmpdir, "1219b.md"), "w") as f:
            f.write("Test Note B\n\nNo links")

        os.environ["NOTES_PATH"] = tmpdir

        proc = subprocess.Popen(
            ["uvicorn", "src.main:app", "--port", "8765"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2)
        yield "http://localhost:8765"
        proc.terminate()

@pytest.mark.asyncio
async def test_landing_page(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(server)
        title = await page.title()
        assert "Kasten" in title

        # Check feeling lucky button exists
        lucky = page.locator('a:has-text("Feeling Lucky")')
        assert await lucky.is_visible()

        await browser.close()

@pytest.mark.asyncio
async def test_note_navigation(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Reindex first
        await page.goto(f"{server}/api/reindex", wait_until="networkidle")

        # Go to note
        await page.goto(f"{server}/note/1219a")

        # Check content visible
        content = page.locator(".note-content")
        assert await content.is_visible()

        # Check graph visible
        graph = page.locator("#note-graph")
        assert await graph.is_visible()

        await browser.close()

@pytest.mark.asyncio
async def test_graph_click_navigation(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(f"{server}/api/reindex", wait_until="networkidle")
        await page.goto(f"{server}/note/1219a")

        # Click on a graph node (forward link)
        # This is tricky with SVG, might need to adjust
        circles = page.locator("#note-graph circle[fill='#fff']")
        if await circles.count() > 0:
            await circles.first.click()
            await page.wait_for_url("**/note/**")

        await browser.close()
```

**Step 2: Install playwright**

```bash
cd kasten && pip install playwright && playwright install chromium
```

**Step 3: Run tests**

Run: `cd kasten && python -m pytest tests/test_ui.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add -A && git commit -m "test: add Playwright UI tests"
```

---

## Summary

**Tasks completed:**
1. Project structure setup
2. Database with async SQLAlchemy
3. Note and Link models
4. Markdown scanner with link extraction
5. Notes API (list, get, entry-points, random, links)
6. Base template with brutalist styling
7. Landing page with entry points
8. Note view with SVG graph visualization
9. Docker + Caddy deployment
10. Playwright tests

**Total commits:** 10

**The Kasten philosophy:**
- No search - navigate by following links
- Simple rules: notes are files, notes link to notes
- Structure emerges from connections
- Entry points + Feeling Lucky to enter the graph
- Push to Canvas workspace for arranging arguments
