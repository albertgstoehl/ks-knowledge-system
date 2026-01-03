# Canvas Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a thinking tool with Draft mode (free-form writing + quotes from bookmark-manager) and Workspace mode (arrange km notes into connected arguments with vis.js graph).

**Architecture:** FastAPI backend with async SQLAlchemy + SQLite. Jinja2 templates + htmx for Draft mode. vis.js for Workspace infinite canvas with zoom/pan. Auto-save with debounced 300ms + localStorage.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy, aiosqlite, Jinja2, htmx, vis.js, Playwright

---

## Phase 1: Project Setup

### Task 1: Initialize Project Structure

**Files:**
- Create: `canvas/pyproject.toml`
- Create: `canvas/src/__init__.py`
- Create: `canvas/tests/__init__.py`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "canvas"
version = "0.1.0"
description = "Thinking tool: draft with quotes, workspace for arguments"
requires-python = ">=3.10"

[project.optional-dependencies]
server = [
    "fastapi==0.115.0",
    "uvicorn[standard]==0.31.0",
    "pydantic==2.9.2",
    "sqlalchemy==2.0.35",
    "aiosqlite==0.20.0",
    "jinja2==3.1.4",
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

**Step 2: Create empty __init__.py files**

```bash
mkdir -p canvas/src/routers canvas/src/templates canvas/static canvas/tests
touch canvas/src/__init__.py canvas/src/routers/__init__.py canvas/tests/__init__.py
```

**Step 3: Commit**

```bash
git add -A && git commit -m "chore: initialize canvas project structure"
```

---

### Task 2: Database Setup

**Files:**
- Create: `canvas/src/database.py`
- Test: `canvas/tests/test_database.py`

**Step 1: Write the failing test**

```python
# canvas/tests/test_database.py
import pytest
from src.database import init_db, get_db

@pytest.mark.asyncio
async def test_init_db_creates_tables():
    await init_db("sqlite+aiosqlite:///:memory:")
    async for session in get_db():
        result = await session.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in result.fetchall()]
        assert "canvas_state" in tables
        break
```

**Step 2: Run test to verify it fails**

Run: `cd canvas && python -m pytest tests/test_database.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write database.py**

```python
# canvas/src/database.py
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
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/canvas.db")

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

Run: `cd canvas && python -m pytest tests/test_database.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add -A && git commit -m "feat: add database setup with async SQLAlchemy"
```

---

### Task 3: Data Models

**Files:**
- Create: `canvas/src/models.py`
- Modify: `canvas/tests/test_database.py`

**Step 1: Write the failing test**

```python
# canvas/tests/test_database.py (add to existing)
@pytest.mark.asyncio
async def test_canvas_state_model():
    await init_db("sqlite+aiosqlite:///:memory:")
    from src.models import CanvasState
    async for session in get_db():
        state = CanvasState(content="test content")
        session.add(state)
        await session.commit()
        await session.refresh(state)
        assert state.id == 1
        assert state.content == "test content"
        assert state.updated_at is not None
        break

@pytest.mark.asyncio
async def test_workspace_note_model():
    await init_db("sqlite+aiosqlite:///:memory:")
    from src.models import WorkspaceNote
    async for session in get_db():
        note = WorkspaceNote(km_note_id="abc123", content="Note content", x=100.0, y=200.0)
        session.add(note)
        await session.commit()
        await session.refresh(note)
        assert note.id is not None
        assert note.km_note_id == "abc123"
        break

@pytest.mark.asyncio
async def test_workspace_connection_model():
    await init_db("sqlite+aiosqlite:///:memory:")
    from src.models import WorkspaceNote, WorkspaceConnection
    async for session in get_db():
        note1 = WorkspaceNote(km_note_id="a", content="A", x=0, y=0)
        note2 = WorkspaceNote(km_note_id="b", content="B", x=100, y=0)
        session.add_all([note1, note2])
        await session.commit()

        conn = WorkspaceConnection(from_note_id=note1.id, to_note_id=note2.id, label="therefore")
        session.add(conn)
        await session.commit()
        assert conn.id is not None
        assert conn.label == "therefore"
        break
```

**Step 2: Run test to verify it fails**

Run: `cd canvas && python -m pytest tests/test_database.py -v`
Expected: FAIL - ImportError

**Step 3: Write models.py**

```python
# canvas/src/models.py
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from src.database import Base

class CanvasState(Base):
    """Single draft canvas - only one row with id=1"""
    __tablename__ = "canvas_state"

    id = Column(Integer, primary_key=True, default=1)
    content = Column(Text, default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class WorkspaceNote(Base):
    """Note pulled from km into workspace"""
    __tablename__ = "workspace_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    km_note_id = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    x = Column(Float, default=0.0)
    y = Column(Float, default=0.0)

class WorkspaceConnection(Base):
    """Labeled edge between notes"""
    __tablename__ = "workspace_connections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_note_id = Column(Integer, ForeignKey("workspace_notes.id"), nullable=False)
    to_note_id = Column(Integer, ForeignKey("workspace_notes.id"), nullable=False)
    label = Column(String(255), default="")
```

**Step 4: Run test to verify it passes**

Run: `cd canvas && python -m pytest tests/test_database.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add -A && git commit -m "feat: add CanvasState, WorkspaceNote, WorkspaceConnection models"
```

---

## Phase 2: Draft Mode API

### Task 4: Canvas API Endpoints

**Files:**
- Create: `canvas/src/routers/canvas.py`
- Create: `canvas/src/schemas.py`
- Test: `canvas/tests/test_api.py`

**Step 1: Write the failing test**

```python
# canvas/tests/test_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import init_db

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db("sqlite+aiosqlite:///:memory:")

@pytest.mark.asyncio
async def test_get_canvas_empty():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/canvas")
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert data["content"] == ""

@pytest.mark.asyncio
async def test_put_canvas():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put("/api/canvas", json={"content": "Hello world"})
        assert response.status_code == 200

        response = await client.get("/api/canvas")
        assert response.json()["content"] == "Hello world"

@pytest.mark.asyncio
async def test_post_quote():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/quotes", json={
            "quote": "Test quote",
            "source_url": "https://example.com",
            "source_title": "Example"
        })
        assert response.status_code == 201

        response = await client.get("/api/canvas")
        content = response.json()["content"]
        assert '> "Test quote"' in content
        assert "Example" in content
```

**Step 2: Run test to verify it fails**

Run: `cd canvas && python -m pytest tests/test_api.py -v`
Expected: FAIL - ModuleNotFoundError (main.py doesn't exist)

**Step 3: Write schemas.py**

```python
# canvas/src/schemas.py
from pydantic import BaseModel
from datetime import datetime

class CanvasContent(BaseModel):
    content: str

class CanvasResponse(BaseModel):
    content: str
    updated_at: datetime | None

class QuoteRequest(BaseModel):
    quote: str
    source_url: str
    source_title: str
```

**Step 4: Write canvas router**

```python
# canvas/src/routers/canvas.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database import get_db
from src.models import CanvasState
from src.schemas import CanvasContent, CanvasResponse, QuoteRequest

router = APIRouter(prefix="/api", tags=["canvas"])

async def get_or_create_canvas(session: AsyncSession) -> CanvasState:
    result = await session.execute(select(CanvasState).where(CanvasState.id == 1))
    canvas = result.scalar_one_or_none()
    if not canvas:
        canvas = CanvasState(id=1, content="")
        session.add(canvas)
        await session.commit()
        await session.refresh(canvas)
    return canvas

@router.get("/canvas", response_model=CanvasResponse)
async def get_canvas(session: AsyncSession = Depends(get_db)):
    canvas = await get_or_create_canvas(session)
    return CanvasResponse(content=canvas.content, updated_at=canvas.updated_at)

@router.put("/canvas", response_model=CanvasResponse)
async def update_canvas(data: CanvasContent, session: AsyncSession = Depends(get_db)):
    canvas = await get_or_create_canvas(session)
    canvas.content = data.content
    await session.commit()
    await session.refresh(canvas)
    return CanvasResponse(content=canvas.content, updated_at=canvas.updated_at)

@router.post("/quotes", status_code=201)
async def receive_quote(data: QuoteRequest, session: AsyncSession = Depends(get_db)):
    canvas = await get_or_create_canvas(session)

    quote_block = f'\n\n> "{data.quote}"\n> — {data.source_title} ({data.source_url})\n'
    canvas.content = canvas.content + quote_block

    await session.commit()
    return {"status": "ok"}
```

**Step 5: Write main.py**

```python
# canvas/src/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.routers import canvas

app = FastAPI(title="Canvas", version="0.1.0")

@app.on_event("startup")
async def startup():
    from src.database import init_db
    await init_db()

@app.get("/health")
async def health():
    return {"status": "healthy"}

app.include_router(canvas.router)
```

**Step 6: Run test to verify it passes**

Run: `cd canvas && python -m pytest tests/test_api.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add -A && git commit -m "feat: add canvas API endpoints (GET/PUT canvas, POST quotes)"
```

---

## Phase 3: Draft Mode UI

### Task 5: Base Template with Styling

**Files:**
- Create: `canvas/src/templates/base.html`
- Create: `canvas/src/routers/ui.py`
- Modify: `canvas/src/main.py`

**Step 1: Create base.html**

Reference: `/home/ags/knowledge-system/bookmark-manager/docs/style.md`

```html
<!-- canvas/src/templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>{% block title %}Canvas{% endblock %}</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
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

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #000;
        }
        .header h1 { font-size: 1.25rem; font-weight: normal; }

        .tabs { display: flex; gap: 1rem; }
        .tab {
            padding: 0.5rem 1rem;
            border: 1px solid #000;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .tab:hover { background: #f5f5f5; }
        .tab.active { background: #000; color: #fff; }

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

        .save-status {
            font-size: 0.875rem;
            color: #666;
        }

        {% block extra_styles %}{% endblock %}
    </style>
</head>
<body>
    <header class="header">
        <h1>CANVAS</h1>
        <nav class="tabs">
            <a href="/draft" class="tab {% if active_tab == 'draft' %}active{% endif %}">Draft</a>
            <a href="/workspace" class="tab {% if active_tab == 'workspace' %}active{% endif %}">Workspace</a>
        </nav>
    </header>

    {% block content %}{% endblock %}

    {% block scripts %}{% endblock %}
</body>
</html>
```

**Step 2: Create ui router**

```python
# canvas/src/routers/ui.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.routers.canvas import get_or_create_canvas

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory="src/templates")

@router.get("/")
async def root():
    return RedirectResponse(url="/draft")

@router.get("/draft")
async def draft_page(request: Request, session: AsyncSession = Depends(get_db)):
    canvas = await get_or_create_canvas(session)
    return templates.TemplateResponse("draft.html", {
        "request": request,
        "active_tab": "draft",
        "content": canvas.content
    })
```

**Step 3: Update main.py to include ui router and templates**

```python
# canvas/src/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.routers import canvas, ui

app = FastAPI(title="Canvas", version="0.1.0")

@app.on_event("startup")
async def startup():
    from src.database import init_db
    await init_db()

@app.get("/health")
async def health():
    return {"status": "healthy"}

app.include_router(canvas.router)
app.include_router(ui.router)
```

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: add base template with brutalist styling and ui router"
```

---

### Task 6: Draft Page with Auto-Save

**Files:**
- Create: `canvas/src/templates/draft.html`

**Step 1: Create draft.html with textarea and auto-save**

```html
<!-- canvas/src/templates/draft.html -->
{% extends "base.html" %}

{% block title %}Draft - Canvas{% endblock %}

{% block extra_styles %}
.draft-container {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 120px);
}
.canvas-editor {
    width: 100%;
    flex: 1;
    padding: 1rem;
    border: 2px solid #000;
    font-family: inherit;
    font-size: 1rem;
    line-height: 1.6;
    resize: none;
}
.canvas-editor:focus {
    outline: none;
    border-color: #000;
}
.status-bar {
    display: flex;
    justify-content: flex-end;
    padding: 0.5rem 0;
}
{% endblock %}

{% block content %}
<div class="draft-container">
    <div class="status-bar">
        <span class="save-status" id="save-status">Saved</span>
    </div>
    <textarea
        class="canvas-editor"
        id="canvas-editor"
        placeholder="Start writing... Quotes from bookmark-manager will appear here."
    >{{ content }}</textarea>
</div>
{% endblock %}

{% block scripts %}
<script>
(function() {
    const editor = document.getElementById('canvas-editor');
    const status = document.getElementById('save-status');
    let saveTimeout = null;
    let lastSaved = editor.value;

    // Load from localStorage if available (offline support)
    const cached = localStorage.getItem('canvas-draft');
    if (cached && cached !== editor.value) {
        const cachedTime = localStorage.getItem('canvas-draft-time');
        if (cachedTime) {
            // Use cached if newer (basic conflict handling)
            editor.value = cached;
        }
    }

    function save() {
        const content = editor.value;
        if (content === lastSaved) return;

        status.textContent = 'Saving...';

        // Save to localStorage immediately
        localStorage.setItem('canvas-draft', content);
        localStorage.setItem('canvas-draft-time', Date.now().toString());

        // Save to server
        fetch('/api/canvas', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: content })
        })
        .then(response => {
            if (response.ok) {
                lastSaved = content;
                status.textContent = 'Saved';
            } else {
                status.textContent = 'Error saving';
            }
        })
        .catch(() => {
            status.textContent = 'Offline (saved locally)';
        });
    }

    editor.addEventListener('input', function() {
        status.textContent = 'Unsaved';
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(save, 300);
    });

    // Save on page leave
    window.addEventListener('beforeunload', save);
})();
</script>
{% endblock %}
```

**Step 2: Test manually**

Run: `cd canvas && uvicorn src.main:app --reload`
Visit: `http://localhost:8000/draft`
Expected: Textarea appears, typing triggers auto-save after 300ms

**Step 3: Commit**

```bash
git add -A && git commit -m "feat: add draft page with auto-save (debounced 300ms + localStorage)"
```

---

## Phase 4: Workspace Mode API

### Task 7: Workspace API Endpoints

**Files:**
- Create: `canvas/src/routers/workspace.py`
- Modify: `canvas/src/schemas.py`
- Modify: `canvas/src/main.py`
- Test: `canvas/tests/test_workspace_api.py`

**Step 1: Write the failing test**

```python
# canvas/tests/test_workspace_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import init_db

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db("sqlite+aiosqlite:///:memory:")

@pytest.mark.asyncio
async def test_get_workspace_empty():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/workspace")
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == []
        assert data["connections"] == []

@pytest.mark.asyncio
async def test_add_note_to_workspace():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/workspace/notes", json={
            "km_note_id": "abc123",
            "content": "Test note content"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["km_note_id"] == "abc123"
        assert "id" in data

@pytest.mark.asyncio
async def test_add_connection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Add two notes
        r1 = await client.post("/api/workspace/notes", json={"km_note_id": "a", "content": "A"})
        r2 = await client.post("/api/workspace/notes", json={"km_note_id": "b", "content": "B"})
        note1_id = r1.json()["id"]
        note2_id = r2.json()["id"]

        # Add connection
        response = await client.post("/api/workspace/connections", json={
            "from_note_id": note1_id,
            "to_note_id": note2_id,
            "label": "therefore"
        })
        assert response.status_code == 201
        assert response.json()["label"] == "therefore"

@pytest.mark.asyncio
async def test_delete_note():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/workspace/notes", json={"km_note_id": "a", "content": "A"})
        note_id = r.json()["id"]

        response = await client.delete(f"/api/workspace/notes/{note_id}")
        assert response.status_code == 200

        workspace = await client.get("/api/workspace")
        assert len(workspace.json()["notes"]) == 0
```

**Step 2: Run test to verify it fails**

Run: `cd canvas && python -m pytest tests/test_workspace_api.py -v`
Expected: FAIL

**Step 3: Add workspace schemas**

```python
# canvas/src/schemas.py (add to existing)

class WorkspaceNoteCreate(BaseModel):
    km_note_id: str
    content: str

class WorkspaceNoteResponse(BaseModel):
    id: int
    km_note_id: str
    content: str
    x: float
    y: float

class ConnectionCreate(BaseModel):
    from_note_id: int
    to_note_id: int
    label: str

class ConnectionUpdate(BaseModel):
    label: str

class ConnectionResponse(BaseModel):
    id: int
    from_note_id: int
    to_note_id: int
    label: str

class WorkspaceResponse(BaseModel):
    notes: list[WorkspaceNoteResponse]
    connections: list[ConnectionResponse]
```

**Step 4: Write workspace router**

```python
# canvas/src/routers/workspace.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from src.database import get_db
from src.models import WorkspaceNote, WorkspaceConnection
from src.schemas import (
    WorkspaceNoteCreate, WorkspaceNoteResponse,
    ConnectionCreate, ConnectionUpdate, ConnectionResponse,
    WorkspaceResponse
)

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

def calculate_position(existing_count: int) -> tuple[float, float]:
    """Simple grid layout for auto-positioning"""
    cols = 3
    row = existing_count // cols
    col = existing_count % cols
    return (col * 350.0, row * 250.0)

@router.get("", response_model=WorkspaceResponse)
async def get_workspace(session: AsyncSession = Depends(get_db)):
    notes_result = await session.execute(select(WorkspaceNote))
    notes = notes_result.scalars().all()

    conns_result = await session.execute(select(WorkspaceConnection))
    connections = conns_result.scalars().all()

    return WorkspaceResponse(
        notes=[WorkspaceNoteResponse(
            id=n.id, km_note_id=n.km_note_id, content=n.content, x=n.x, y=n.y
        ) for n in notes],
        connections=[ConnectionResponse(
            id=c.id, from_note_id=c.from_note_id, to_note_id=c.to_note_id, label=c.label
        ) for c in connections]
    )

@router.post("/notes", status_code=201, response_model=WorkspaceNoteResponse)
async def add_note(data: WorkspaceNoteCreate, session: AsyncSession = Depends(get_db)):
    # Count existing notes for positioning
    result = await session.execute(select(WorkspaceNote))
    existing = len(result.scalars().all())
    x, y = calculate_position(existing)

    note = WorkspaceNote(
        km_note_id=data.km_note_id,
        content=data.content,
        x=x,
        y=y
    )
    session.add(note)
    await session.commit()
    await session.refresh(note)

    return WorkspaceNoteResponse(
        id=note.id, km_note_id=note.km_note_id, content=note.content, x=note.x, y=note.y
    )

@router.delete("/notes/{note_id}")
async def delete_note(note_id: int, session: AsyncSession = Depends(get_db)):
    # Delete connections involving this note
    await session.execute(
        delete(WorkspaceConnection).where(
            (WorkspaceConnection.from_note_id == note_id) |
            (WorkspaceConnection.to_note_id == note_id)
        )
    )

    result = await session.execute(select(WorkspaceNote).where(WorkspaceNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    await session.delete(note)
    await session.commit()
    return {"status": "deleted"}

@router.post("/connections", status_code=201, response_model=ConnectionResponse)
async def add_connection(data: ConnectionCreate, session: AsyncSession = Depends(get_db)):
    conn = WorkspaceConnection(
        from_note_id=data.from_note_id,
        to_note_id=data.to_note_id,
        label=data.label
    )
    session.add(conn)
    await session.commit()
    await session.refresh(conn)

    return ConnectionResponse(
        id=conn.id, from_note_id=conn.from_note_id,
        to_note_id=conn.to_note_id, label=conn.label
    )

@router.put("/connections/{conn_id}", response_model=ConnectionResponse)
async def update_connection(conn_id: int, data: ConnectionUpdate, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(WorkspaceConnection).where(WorkspaceConnection.id == conn_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    conn.label = data.label
    await session.commit()
    await session.refresh(conn)

    return ConnectionResponse(
        id=conn.id, from_note_id=conn.from_note_id,
        to_note_id=conn.to_note_id, label=conn.label
    )

@router.delete("/connections/{conn_id}")
async def delete_connection(conn_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(WorkspaceConnection).where(WorkspaceConnection.id == conn_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    await session.delete(conn)
    await session.commit()
    return {"status": "deleted"}
```

**Step 5: Update main.py**

```python
# canvas/src/main.py
from fastapi import FastAPI
from src.routers import canvas, ui, workspace

app = FastAPI(title="Canvas", version="0.1.0")

@app.on_event("startup")
async def startup():
    from src.database import init_db
    await init_db()

@app.get("/health")
async def health():
    return {"status": "healthy"}

app.include_router(canvas.router)
app.include_router(workspace.router)
app.include_router(ui.router)
```

**Step 6: Run test to verify it passes**

Run: `cd canvas && python -m pytest tests/test_workspace_api.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add -A && git commit -m "feat: add workspace API (notes CRUD, connections CRUD)"
```

---

## Phase 5: Workspace UI with vis.js

### Task 8: Workspace Page with Graph

**Files:**
- Create: `canvas/src/templates/workspace.html`
- Create: `canvas/static/workspace.js`
- Modify: `canvas/src/routers/ui.py`

**Step 1: Add workspace route to ui.py**

```python
# canvas/src/routers/ui.py (add to existing)

@router.get("/workspace")
async def workspace_page(request: Request, session: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse("workspace.html", {
        "request": request,
        "active_tab": "workspace"
    })
```

**Step 2: Create workspace.html**

```html
<!-- canvas/src/templates/workspace.html -->
{% extends "base.html" %}

{% block title %}Workspace - Canvas{% endblock %}

{% block extra_styles %}
.workspace-container {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 120px);
}
.workspace-toolbar {
    display: flex;
    gap: 0.5rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid #000;
    margin-bottom: 0.5rem;
}
.workspace-canvas {
    flex: 1;
    border: 2px solid #000;
    position: relative;
}
#graph {
    width: 100%;
    height: 100%;
}
.zoom-controls {
    position: absolute;
    bottom: 1rem;
    right: 1rem;
    display: flex;
    gap: 0.25rem;
}
.zoom-btn {
    width: 32px;
    height: 32px;
    border: 1px solid #000;
    background: #fff;
    cursor: pointer;
    font-size: 1.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
}
.zoom-btn:hover { background: #f5f5f5; }

/* Connection modal */
.modal {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 100;
}
.modal.active { display: flex; align-items: center; justify-content: center; }
.modal-content {
    background: #fff;
    border: 2px solid #000;
    padding: 1.5rem;
    min-width: 300px;
}
.modal-content h3 { margin-bottom: 1rem; }
.modal-content input {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #000;
    font-family: inherit;
    margin-bottom: 1rem;
}
.modal-actions { display: flex; gap: 0.5rem; justify-content: flex-end; }
{% endblock %}

{% block content %}
<div class="workspace-container">
    <div class="workspace-toolbar">
        <button class="btn" id="connect-btn" disabled>+ Connect</button>
        <button class="btn" id="export-btn">Export</button>
        <span style="flex:1"></span>
        <span id="selection-info" style="color:#666;font-size:0.875rem;"></span>
    </div>
    <div class="workspace-canvas">
        <div id="graph"></div>
        <div class="zoom-controls">
            <button class="zoom-btn" id="zoom-out">−</button>
            <button class="zoom-btn" id="zoom-in">+</button>
            <button class="zoom-btn" id="zoom-fit">⊡</button>
        </div>
    </div>
</div>

<!-- Connection Modal -->
<div class="modal" id="connection-modal">
    <div class="modal-content">
        <h3>Add Connection</h3>
        <input type="text" id="connection-label" placeholder="Label (e.g., therefore, however)" />
        <div class="modal-actions">
            <button class="btn" onclick="closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="createConnection()">Connect</button>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<script src="/static/workspace.js"></script>
{% endblock %}
```

**Step 3: Create workspace.js**

```javascript
// canvas/static/workspace.js
(function() {
    let network = null;
    let nodes = new vis.DataSet([]);
    let edges = new vis.DataSet([]);
    let selectedNodes = [];

    // Load workspace data
    async function loadWorkspace() {
        const response = await fetch('/api/workspace');
        const data = await response.json();

        nodes.clear();
        edges.clear();

        data.notes.forEach(note => {
            nodes.add({
                id: note.id,
                label: note.content.substring(0, 100) + (note.content.length > 100 ? '...' : ''),
                title: note.content,
                x: note.x,
                y: note.y,
                shape: 'box',
                font: { face: 'monospace', size: 12, align: 'left' },
                margin: 10,
                widthConstraint: { minimum: 150, maximum: 300 }
            });
        });

        data.connections.forEach(conn => {
            edges.add({
                id: conn.id,
                from: conn.from_note_id,
                to: conn.to_note_id,
                label: conn.label,
                arrows: 'to',
                font: { face: 'monospace', size: 11 }
            });
        });
    }

    // Initialize network
    function initNetwork() {
        const container = document.getElementById('graph');
        const options = {
            physics: false,
            interaction: {
                multiselect: true,
                selectConnectedEdges: false
            },
            nodes: {
                color: {
                    background: '#fff',
                    border: '#000',
                    highlight: { background: '#f5f5f5', border: '#000' }
                },
                borderWidth: 2
            },
            edges: {
                color: '#000',
                width: 1,
                smooth: { type: 'cubicBezier' }
            }
        };

        network = new vis.Network(container, { nodes, edges }, options);

        network.on('select', function(params) {
            selectedNodes = params.nodes;
            updateSelectionUI();
        });

        network.on('deselectNode', function() {
            selectedNodes = network.getSelectedNodes();
            updateSelectionUI();
        });
    }

    function updateSelectionUI() {
        const connectBtn = document.getElementById('connect-btn');
        const info = document.getElementById('selection-info');

        if (selectedNodes.length === 2) {
            connectBtn.disabled = false;
            info.textContent = '2 notes selected - ready to connect';
        } else if (selectedNodes.length === 1) {
            connectBtn.disabled = true;
            info.textContent = '1 note selected - select another to connect';
        } else {
            connectBtn.disabled = true;
            info.textContent = selectedNodes.length > 0 ? `${selectedNodes.length} notes selected` : '';
        }
    }

    // Connection modal
    window.openConnectionModal = function() {
        document.getElementById('connection-modal').classList.add('active');
        document.getElementById('connection-label').focus();
    };

    window.closeModal = function() {
        document.getElementById('connection-modal').classList.remove('active');
        document.getElementById('connection-label').value = '';
    };

    window.createConnection = async function() {
        const label = document.getElementById('connection-label').value || 'relates to';

        const response = await fetch('/api/workspace/connections', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                from_note_id: selectedNodes[0],
                to_note_id: selectedNodes[1],
                label: label
            })
        });

        if (response.ok) {
            const conn = await response.json();
            edges.add({
                id: conn.id,
                from: conn.from_note_id,
                to: conn.to_note_id,
                label: conn.label,
                arrows: 'to',
                font: { face: 'monospace', size: 11 }
            });
        }

        closeModal();
        network.unselectAll();
    };

    // Export
    async function exportWorkspace() {
        const response = await fetch('/api/workspace');
        const data = await response.json();

        // Build adjacency for traversal
        const noteMap = {};
        data.notes.forEach(n => noteMap[n.id] = n);

        // Simple export: list notes with their connections
        let output = '';
        data.notes.forEach(note => {
            output += note.content + '\n\n';

            const outgoing = data.connections.filter(c => c.from_note_id === note.id);
            outgoing.forEach(conn => {
                output += `**${conn.label.charAt(0).toUpperCase() + conn.label.slice(1)}:**\n\n`;
            });
        });

        // Download as file
        const blob = new Blob([output], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'workspace-export.md';
        a.click();
    }

    // Zoom controls
    document.getElementById('zoom-in').addEventListener('click', () => {
        network.moveTo({ scale: network.getScale() * 1.2 });
    });
    document.getElementById('zoom-out').addEventListener('click', () => {
        network.moveTo({ scale: network.getScale() / 1.2 });
    });
    document.getElementById('zoom-fit').addEventListener('click', () => {
        network.fit();
    });

    // Button handlers
    document.getElementById('connect-btn').addEventListener('click', openConnectionModal);
    document.getElementById('export-btn').addEventListener('click', exportWorkspace);

    // Init
    loadWorkspace().then(initNetwork);
})();
```

**Step 4: Add static files mount to main.py**

```python
# canvas/src/main.py (update)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.routers import canvas, ui, workspace

app = FastAPI(title="Canvas", version="0.1.0")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup():
    from src.database import init_db
    await init_db()

@app.get("/health")
async def health():
    return {"status": "healthy"}

app.include_router(canvas.router)
app.include_router(workspace.router)
app.include_router(ui.router)
```

**Step 5: Test manually**

Run: `cd canvas && uvicorn src.main:app --reload`
Visit: `http://localhost:8000/workspace`
Expected: Empty graph canvas, zoom controls work

**Step 6: Commit**

```bash
git add -A && git commit -m "feat: add workspace UI with vis.js graph (zoom/pan, connections)"
```

---

## Phase 6: Playwright Tests

### Task 9: UI Tests

**Files:**
- Create: `canvas/tests/test_ui.py`
- Create: `canvas/playwright.config.py`

**Step 1: Write Playwright tests**

```python
# canvas/tests/test_ui.py
import pytest
from playwright.async_api import async_playwright
import asyncio
import subprocess
import time

@pytest.fixture(scope="module")
def server():
    """Start the server for testing"""
    proc = subprocess.Popen(
        ["uvicorn", "src.main:app", "--port", "8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)  # Wait for server to start
    yield "http://localhost:8765"
    proc.terminate()

@pytest.mark.asyncio
async def test_draft_page_loads(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(f"{server}/draft")

        # Check title
        title = await page.title()
        assert "Draft" in title

        # Check textarea exists
        editor = page.locator("#canvas-editor")
        assert await editor.is_visible()

        await browser.close()

@pytest.mark.asyncio
async def test_draft_autosave(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(f"{server}/draft")

        editor = page.locator("#canvas-editor")
        await editor.fill("Test content for autosave")

        # Wait for debounce + save
        await page.wait_for_timeout(500)

        status = page.locator("#save-status")
        status_text = await status.text_content()
        assert status_text in ["Saved", "Saving..."]

        # Reload and verify content persisted
        await page.reload()
        editor = page.locator("#canvas-editor")
        content = await editor.input_value()
        assert "Test content" in content

        await browser.close()

@pytest.mark.asyncio
async def test_workspace_page_loads(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(f"{server}/workspace")

        title = await page.title()
        assert "Workspace" in title

        # Check graph container exists
        graph = page.locator("#graph")
        assert await graph.is_visible()

        await browser.close()

@pytest.mark.asyncio
async def test_tab_navigation(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(f"{server}/draft")

        # Click workspace tab
        await page.click('a.tab:has-text("Workspace")')
        await page.wait_for_url("**/workspace")

        # Click draft tab
        await page.click('a.tab:has-text("Draft")')
        await page.wait_for_url("**/draft")

        await browser.close()
```

**Step 2: Install playwright browsers**

```bash
cd canvas && pip install playwright && playwright install chromium
```

**Step 3: Run tests**

Run: `cd canvas && python -m pytest tests/test_ui.py -v`
Expected: PASS (may need server running separately for first run)

**Step 4: Commit**

```bash
git add -A && git commit -m "test: add Playwright UI tests for draft and workspace pages"
```

---

## Phase 7: Docker & Deployment

### Task 10: Docker Setup

**Files:**
- Create: `canvas/Dockerfile`
- Create: `canvas/docker-compose.yml`
- Create: `canvas/Caddyfile`
- Create: `canvas/requirements.txt`

**Step 1: Create requirements.txt**

```
# canvas/requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.31.0
pydantic==2.9.2
sqlalchemy==2.0.35
aiosqlite==0.20.0
jinja2==3.1.4
```

**Step 2: Create Dockerfile**

```dockerfile
# canvas/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY static/ static/

RUN mkdir -p data

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 3: Create docker-compose.yml**

```yaml
# canvas/docker-compose.yml
version: '3.8'

services:
  canvas:
    build: .
    container_name: canvas
    restart: unless-stopped
    networks:
      - app-network
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./data/canvas.db

  caddy:
    image: caddy:2
    container_name: canvas-caddy
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
# canvas/Caddyfile
canvas.gstoehl.dev {
    reverse_proxy canvas:8000
}
```

**Step 5: Test Docker build**

```bash
cd canvas && docker build -t canvas:test .
```

**Step 6: Commit**

```bash
git add -A && git commit -m "chore: add Docker and Caddy configuration"
```

---

## Summary

**Tasks completed:**
1. Project structure setup
2. Database with async SQLAlchemy
3. Data models (CanvasState, WorkspaceNote, WorkspaceConnection)
4. Canvas API (GET/PUT canvas, POST quotes)
5. Base template with brutalist styling
6. Draft page with auto-save
7. Workspace API (notes/connections CRUD)
8. Workspace UI with vis.js
9. Playwright tests
10. Docker + Caddy deployment

**Total commits:** 10

**Next steps (not in this plan):**
- Add text selection + "Push to Canvas" button to bookmark-manager
- Add km web UI with "Push to Workspace" button
- Add note extraction with `---` markers
- Add km API for search/create notes
