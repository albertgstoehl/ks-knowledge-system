# Kasten Sources Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `sources` table to Kasten that stores archived bookmarks, with notes linking to their source via `source_id`. Sources display as collapsible headers on notes.

**Architecture:** New `Source` model with one-to-many relationship to `Note`. API endpoints for creating sources and linking notes. UI shows source as expandable header above note content when present.

**Tech Stack:** FastAPI, SQLAlchemy async, Jinja2 templates, vanilla JavaScript

---

## Phase 1: Data Model

### Task 1: Add Source model

**Files:**
- Modify: `kasten/src/models.py:1-23`
- Test: `kasten/tests/test_database.py`

**Step 1: Write failing test for Source model**

```python
# In kasten/tests/test_database.py - add at end
import pytest
from datetime import datetime

@pytest.mark.asyncio
async def test_source_model():
    """Test that Source model exists and can be created"""
    from src.models import Source
    from src.database import init_db, get_db

    await init_db("sqlite+aiosqlite:///:memory:")

    async for session in get_db():
        source = Source(
            url="https://example.com/article",
            title="Test Article",
            description="A test description"
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)

        assert source.id is not None
        assert source.url == "https://example.com/article"
        assert source.archived_at is not None
        break
```

**Step 2: Run test to verify it fails**

Run: `cd kasten && pytest tests/test_database.py::test_source_model -v`
Expected: FAIL with "cannot import name 'Source'"

**Step 3: Add Source model to models.py**

```python
# In kasten/src/models.py - add after imports, before Note class
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base


class Source(Base):
    """Archived bookmark sources from Bookmark Manager"""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2048), unique=True, nullable=False)
    title = Column(String(512))
    description = Column(Text)
    content = Column(Text)
    video_id = Column(String(64))
    archived_at = Column(DateTime, server_default=func.now())

    # Relationship
    notes = relationship("Note", back_populates="source")


class Note(Base):
    """Note metadata - content lives in markdown files"""
    __tablename__ = "notes"

    id = Column(String(10), primary_key=True)  # e.g., "1219a"
    title = Column(String(255))
    parent_id = Column(String(10), ForeignKey("notes.id"), nullable=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    file_path = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())

    # Relationship
    source = relationship("Source", back_populates="notes")


class Link(Base):
    """Links between notes"""
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_note_id = Column(String(10), ForeignKey("notes.id"), nullable=False)
    to_note_id = Column(String(10), ForeignKey("notes.id"), nullable=False)
```

**Step 4: Run test to verify it passes**

Run: `cd kasten && pytest tests/test_database.py::test_source_model -v`
Expected: PASS

**Step 5: Commit**

```bash
cd kasten && git add src/models.py tests/test_database.py && git commit -m "feat(models): add Source model with Note relationship"
```

---

### Task 2: Update database init to create sources table

**Files:**
- Modify: `kasten/src/database.py`

**Step 1: Verify database.py creates all tables**

```python
# In kasten/src/database.py - ensure init_db creates all tables
# The existing init_db should already do:
# async with engine.begin() as conn:
#     await conn.run_sync(Base.metadata.create_all)

# No code change needed if using Base.metadata.create_all
```

**Step 2: Write test that sources table exists after init**

```python
# In kasten/tests/test_database.py - add test
@pytest.mark.asyncio
async def test_sources_table_created():
    """Test that sources table is created on init"""
    from src.database import init_db, engine
    from sqlalchemy import inspect

    await init_db("sqlite+aiosqlite:///:memory:")

    async with engine.connect() as conn:
        def get_tables(connection):
            inspector = inspect(connection)
            return inspector.get_table_names()

        tables = await conn.run_sync(get_tables)
        assert "sources" in tables
        assert "notes" in tables
```

**Step 3: Run test**

Run: `cd kasten && pytest tests/test_database.py::test_sources_table_created -v`
Expected: PASS (if Base.metadata.create_all is used)

**Step 4: Commit**

```bash
cd kasten && git add tests/test_database.py && git commit -m "test(db): add test for sources table creation"
```

---

## Phase 2: API Endpoints

### Task 3: Add POST /api/sources endpoint

**Files:**
- Modify: `kasten/src/routers/api.py:1-50`
- Test: `kasten/tests/test_api.py`

**Step 1: Write failing test for create source**

```python
# In kasten/tests/test_api.py - add at end
@pytest.mark.asyncio
async def test_create_source():
    """Test POST /api/sources creates a source"""
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sources", json={
            "url": "https://example.com/article",
            "title": "Test Article",
            "description": "A fascinating article about testing"
        })
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["url"] == "https://example.com/article"
        assert data["title"] == "Test Article"
```

**Step 2: Run test to verify it fails**

Run: `cd kasten && pytest tests/test_api.py::test_create_source -v`
Expected: FAIL with 404 (endpoint not found)

**Step 3: Add SourceCreate schema and endpoint**

```python
# In kasten/src/routers/api.py - add after NoteCreateRequest class

class SourceCreateRequest(BaseModel):
    url: str
    title: str | None = None
    description: str | None = None
    content: str | None = None
    video_id: str | None = None


class SourceResponse(BaseModel):
    id: int
    url: str
    title: str | None
    description: str | None
    content: str | None
    video_id: str | None
    archived_at: datetime

    class Config:
        from_attributes = True
```

```python
# In kasten/src/routers/api.py - add import
from src.models import Note, Link, Source

# Add endpoint after /notes endpoints
@router.post("/sources", status_code=201, response_model=SourceResponse)
async def create_source(data: SourceCreateRequest, session: AsyncSession = Depends(get_db)):
    """Create a new source (archived bookmark)."""
    # Check for duplicate URL
    result = await session.execute(
        select(Source).where(Source.url == data.url)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Return existing source instead of error
        return existing

    source = Source(
        url=data.url,
        title=data.title,
        description=data.description,
        content=data.content,
        video_id=data.video_id
    )
    session.add(source)
    await session.commit()
    await session.refresh(source)

    return source
```

**Step 4: Run test to verify it passes**

Run: `cd kasten && pytest tests/test_api.py::test_create_source -v`
Expected: PASS

**Step 5: Commit**

```bash
cd kasten && git add src/routers/api.py tests/test_api.py && git commit -m "feat(api): add POST /api/sources endpoint"
```

---

### Task 4: Add GET /api/sources/{id} endpoint

**Files:**
- Modify: `kasten/src/routers/api.py`
- Test: `kasten/tests/test_api.py`

**Step 1: Write failing test**

```python
# In kasten/tests/test_api.py - add test
@pytest.mark.asyncio
async def test_get_source():
    """Test GET /api/sources/{id} returns source with note_ids"""
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create source
        create_resp = await client.post("/api/sources", json={
            "url": "https://example.com/get-test",
            "title": "Get Test"
        })
        source_id = create_resp.json()["id"]

        # Get source
        response = await client.get(f"/api/sources/{source_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == source_id
        assert data["url"] == "https://example.com/get-test"
        assert "note_ids" in data
```

**Step 2: Run test to verify it fails**

Run: `cd kasten && pytest tests/test_api.py::test_get_source -v`
Expected: FAIL with 404

**Step 3: Add endpoint**

```python
# In kasten/src/routers/api.py - add after create_source

class SourceDetailResponse(BaseModel):
    id: int
    url: str
    title: str | None
    description: str | None
    content: str | None
    video_id: str | None
    archived_at: datetime
    note_ids: list[str]

    class Config:
        from_attributes = True


@router.get("/sources/{source_id}", response_model=SourceDetailResponse)
async def get_source(source_id: int, session: AsyncSession = Depends(get_db)):
    """Get a source with linked note IDs."""
    result = await session.execute(
        select(Source).where(Source.id == source_id)
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Get linked notes
    notes_result = await session.execute(
        select(Note.id).where(Note.source_id == source_id)
    )
    note_ids = [n[0] for n in notes_result.all()]

    return SourceDetailResponse(
        id=source.id,
        url=source.url,
        title=source.title,
        description=source.description,
        content=source.content,
        video_id=source.video_id,
        archived_at=source.archived_at,
        note_ids=note_ids
    )
```

**Step 4: Run test to verify it passes**

Run: `cd kasten && pytest tests/test_api.py::test_get_source -v`
Expected: PASS

**Step 5: Commit**

```bash
cd kasten && git add src/routers/api.py tests/test_api.py && git commit -m "feat(api): add GET /api/sources/{id} endpoint"
```

---

### Task 5: Update POST /api/notes to accept source_id

**Files:**
- Modify: `kasten/src/routers/api.py:150-179`
- Test: `kasten/tests/test_api.py`

**Step 1: Write failing test**

```python
# In kasten/tests/test_api.py - add test
@pytest.mark.asyncio
async def test_create_note_with_source():
    """Test creating a note linked to a source"""
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create source first
        source_resp = await client.post("/api/sources", json={
            "url": "https://example.com/note-source",
            "title": "Note Source"
        })
        source_id = source_resp.json()["id"]

        # Create note with source
        response = await client.post("/api/notes", json={
            "title": "Note from Source",
            "content": "This note came from a source",
            "source_id": source_id
        })
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
```

**Step 2: Run test to verify it fails**

Run: `cd kasten && pytest tests/test_api.py::test_create_note_with_source -v`
Expected: FAIL (source_id not recognized)

**Step 3: Update NoteCreateRequest and create_note**

```python
# In kasten/src/routers/api.py - update NoteCreateRequest
class NoteCreateRequest(BaseModel):
    title: str
    content: str
    parent: str | None = None
    source_id: int | None = None


# Update create_note function
@router.post("/notes", status_code=201)
async def create_note(data: NoteCreateRequest, session: AsyncSession = Depends(get_db)):
    """Create a new note file."""
    notes_path = get_notes_path()
    note_id = generate_note_id(notes_path)
    filename = f"{note_id}.md"
    filepath = os.path.join(notes_path, filename)

    # Verify source exists if provided
    if data.source_id:
        source_result = await session.execute(
            select(Source).where(Source.id == data.source_id)
        )
        if not source_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Source not found")

    # Build file content
    lines = []
    if data.parent:
        lines.append("---")
        lines.append(f"parent: {data.parent}")
        lines.append("---")
    lines.append(data.title)
    lines.append("")
    lines.append(data.content)

    file_content = "\n".join(lines)

    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(file_content)

    # Add to database with source_id
    note = Note(
        id=note_id,
        title=data.title,
        file_path=filename,
        parent_id=data.parent,
        source_id=data.source_id
    )
    session.add(note)
    await session.commit()

    return {"id": note_id, "title": data.title}
```

**Step 4: Run test to verify it passes**

Run: `cd kasten && pytest tests/test_api.py::test_create_note_with_source -v`
Expected: PASS

**Step 5: Commit**

```bash
cd kasten && git add src/routers/api.py tests/test_api.py && git commit -m "feat(api): add source_id support to POST /api/notes"
```

---

### Task 6: Update GET /api/notes/{id} to include source

**Files:**
- Modify: `kasten/src/routers/api.py:111-128`
- Test: `kasten/tests/test_api.py`

**Step 1: Write failing test**

```python
# In kasten/tests/test_api.py - add test
@pytest.mark.asyncio
async def test_get_note_with_source():
    """Test GET /api/notes/{id} includes source data"""
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create source
        source_resp = await client.post("/api/sources", json={
            "url": "https://example.com/full-test",
            "title": "Full Test Source",
            "description": "A test description"
        })
        source_id = source_resp.json()["id"]

        # Create note with source
        note_resp = await client.post("/api/notes", json={
            "title": "Note With Source",
            "content": "Content here",
            "source_id": source_id
        })
        note_id = note_resp.json()["id"]

        # Get note
        response = await client.get(f"/api/notes/{note_id}")
        assert response.status_code == 200
        data = response.json()
        assert "source" in data
        assert data["source"]["url"] == "https://example.com/full-test"
        assert data["source"]["title"] == "Full Test Source"
```

**Step 2: Run test to verify it fails**

Run: `cd kasten && pytest tests/test_api.py::test_get_note_with_source -v`
Expected: FAIL - "source" not in response

**Step 3: Update get_note endpoint**

```python
# In kasten/src/routers/api.py - update get_note
@router.get("/notes/{note_id}")
async def get_note(note_id: str, session: AsyncSession = Depends(get_db)):
    """Get a specific note with content and source."""
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

    # Get source if linked
    source_data = None
    if note.source_id:
        source_result = await session.execute(
            select(Source).where(Source.id == note.source_id)
        )
        source = source_result.scalar_one_or_none()
        if source:
            source_data = {
                "id": source.id,
                "url": source.url,
                "title": source.title,
                "description": source.description,
                "content": source.content,
                "video_id": source.video_id,
                "archived_at": source.archived_at.isoformat() if source.archived_at else None
            }

    return {
        "id": note.id,
        "title": note.title,
        "content": content,
        "source": source_data
    }
```

**Step 4: Run test to verify it passes**

Run: `cd kasten && pytest tests/test_api.py::test_get_note_with_source -v`
Expected: PASS

**Step 5: Commit**

```bash
cd kasten && git add src/routers/api.py tests/test_api.py && git commit -m "feat(api): include source data in GET /api/notes/{id}"
```

---

## Phase 3: UI Changes

### Task 7: Update UI router to fetch source data

**Files:**
- Modify: `kasten/src/routers/ui.py:45-101`
- Test: `kasten/tests/test_ui.py`

**Step 1: Write failing test**

```python
# In kasten/tests/test_ui.py - add test
@pytest.mark.asyncio
async def test_note_view_with_source():
    """Test note view includes source in template context"""
    # Setup will need a source-linked note
    # For now, test that source is in template context (even if None)
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/reindex")
        response = await client.get("/note/1219a")
        assert response.status_code == 200
        # Source will be None for existing notes, but page should render
        assert b"note-content" in response.content
```

**Step 2: Run test to verify baseline**

Run: `cd kasten && pytest tests/test_ui.py::test_note_view_with_source -v`
Expected: Should PASS (baseline - source not shown yet)

**Step 3: Update note_view to fetch source**

```python
# In kasten/src/routers/ui.py - add import
from src.models import Note, Link, Source

# Update note_view function - add source fetching before template response
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

    # Get source if linked
    source = None
    if note.source_id:
        source_result = await session.execute(
            select(Source).where(Source.id == note.source_id)
        )
        source_obj = source_result.scalar_one_or_none()
        if source_obj:
            # Extract domain from URL
            from urllib.parse import urlparse
            domain = urlparse(source_obj.url).netloc.replace("www.", "")
            source = {
                "id": source_obj.id,
                "url": source_obj.url,
                "title": source_obj.title,
                "description": source_obj.description,
                "domain": domain,
                "archived_at": source_obj.archived_at
            }

    # Get parent (from parent_id field)
    parent = None
    if note.parent_id:
        parent_result = await session.execute(
            select(Note).where(Note.id == note.parent_id)
        )
        parent_note = parent_result.scalar_one_or_none()
        if parent_note:
            parent = {"id": parent_note.id, "title": parent_note.title}

    # Get children (notes that have this note as parent)
    children_result = await session.execute(
        select(Note).where(Note.parent_id == note_id).order_by(Note.created_at.asc())
    )
    children = [{"id": n.id, "title": n.title} for n in children_result.scalars().all()]

    # Get siblings (other notes with same parent)
    siblings = []
    if note.parent_id:
        siblings_result = await session.execute(
            select(Note).where(
                Note.parent_id == note.parent_id,
                Note.id != note_id
            ).order_by(Note.created_at.asc())
        )
        siblings = [{"id": n.id, "title": n.title} for n in siblings_result.scalars().all()]

    canvas_url = os.getenv("CANVAS_URL", "https://canvas.gstoehl.dev")
    return templates.TemplateResponse("note.html", {
        "request": request,
        "note": {"id": note.id, "title": note.title},
        "content": content_html,
        "source": source,
        "parent": parent,
        "children": children,
        "siblings": siblings,
        "canvas_url": canvas_url
    })
```

**Step 4: Run test to verify it passes**

Run: `cd kasten && pytest tests/test_ui.py::test_note_view_with_source -v`
Expected: PASS

**Step 5: Commit**

```bash
cd kasten && git add src/routers/ui.py tests/test_ui.py && git commit -m "feat(ui): fetch source data in note_view"
```

---

### Task 8: Add source header to note template

**Files:**
- Modify: `kasten/src/templates/note.html:1-20`

**Step 1: Update note.html template**

```html
<!-- kasten/src/templates/note.html -->
{% extends "base.html" %}

{% block title %}{{ note.id }} - Kasten{% endblock %}

{% block content %}
<nav class="nav-bar">
    <button class="nav-btn" onclick="history.back()" title="Back">&#8592;</button>
    <a href="javascript:void(0)" class="btn btn-primary" onclick="pushToWorkspace()">Push to Workspace</a>
    <button class="nav-btn" onclick="history.forward()" title="Forward">&#8594;</button>
</nav>

{% if source %}
<section class="source-header" id="source-header">
    <div class="source-title-row">
        <div class="source-info">
            <span class="source-label">Source:</span>
            <span class="source-title">{{ source.title or 'Untitled' }}</span>
        </div>
        <button class="source-toggle" onclick="toggleSource()" id="source-toggle">[+]</button>
    </div>
    <div class="source-meta">{{ source.domain }} · {{ source.archived_at.strftime('%b %d') if source.archived_at else '' }}</div>
    <div class="source-details" id="source-details" style="display: none;">
        {% if source.description %}
        <p class="source-description">{{ source.description }}</p>
        {% endif %}
        <a href="{{ source.url }}" target="_blank" class="source-link">Open original</a>
    </div>
</section>
{% endif %}

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
const parent = {{ parent | tojson }};
const children = {{ children | tojson }};
const siblings = {{ siblings | tojson }};
const canvasUrl = "{{ canvas_url }}";

function toggleSource() {
    const details = document.getElementById('source-details');
    const toggle = document.getElementById('source-toggle');
    if (details.style.display === 'none') {
        details.style.display = 'block';
        toggle.textContent = '[-]';
    } else {
        details.style.display = 'none';
        toggle.textContent = '[+]';
    }
}

function pushToWorkspace() {
    fetch('/api/notes/{{ note.id }}')
        .then(r => r.json())
        .then(note => {
            return fetch(canvasUrl + '/api/workspace/notes', {
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

// Navigation graph (unchanged)
(function() {
    const svg = document.getElementById('note-graph');
    const nodeRadius = 15;
    const currentRadius = 18;

    function drawLine(x1, y1, x2, y2) {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', x1);
        line.setAttribute('y1', y1);
        line.setAttribute('x2', x2);
        line.setAttribute('y2', y2);
        line.setAttribute('stroke', '#000');
        svg.appendChild(line);
    }

    function createNode(x, y, note, isCurrent) {
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', x);
        circle.setAttribute('cy', y);
        circle.setAttribute('r', isCurrent ? currentRadius : nodeRadius);
        circle.setAttribute('fill', isCurrent ? '#000' : '#fff');
        circle.setAttribute('stroke', '#000');
        circle.setAttribute('stroke-width', '2');
        if (!isCurrent) {
            circle.style.cursor = 'pointer';
            circle.onclick = () => window.location.href = '/note/' + note.id;
            circle.onmouseover = () => circle.setAttribute('fill', '#f5f5f5');
            circle.onmouseout = () => circle.setAttribute('fill', '#fff');
            const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
            title.textContent = note.id + ': ' + note.title;
            circle.appendChild(title);
        }
        svg.appendChild(circle);
        return circle;
    }

    function addLabel(x, y, text) {
        const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        label.setAttribute('x', x);
        label.setAttribute('y', y);
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('font-size', '10');
        label.setAttribute('font-family', 'monospace');
        label.textContent = text;
        svg.appendChild(label);
    }

    const hasSiblings = siblings.length > 0;
    const hasParent = parent !== null;

    if (hasParent && hasSiblings) {
        const parentX = 50, parentY = 80;
        const forkX = 100;
        const branchX = 200;
        const branchSpacing = 35;

        const allBranches = [...siblings, {id: noteId, title: '', isCurrent: true}];
        const currentIndex = allBranches.findIndex(b => b.isCurrent);

        createNode(parentX, parentY, parent, false);
        drawLine(parentX + nodeRadius, parentY, forkX, parentY);

        const topY = parentY - (currentIndex * branchSpacing);
        const bottomY = topY + ((allBranches.length - 1) * branchSpacing);
        drawLine(forkX, topY, forkX, bottomY);

        allBranches.forEach((branch, i) => {
            const y = topY + (i * branchSpacing);
            drawLine(forkX, y, branchX, y);
            createNode(branchX, y, branch, branch.isCurrent);
            if (branch.isCurrent) {
                addLabel(branchX, y + currentRadius + 12, noteId);
            }
        });

        if (children.length > 0) {
            const currentY = topY + (currentIndex * branchSpacing);
            const childX = 270;
            drawLine(branchX + currentRadius, currentY, childX - nodeRadius, currentY);
            createNode(childX, currentY, children[0], false);
        }
    } else {
        const parentX = 50, currentX = 150, childX = 250;
        const mainY = 50;
        const branchStartY = 95, branchSpacing = 40;

        createNode(currentX, mainY, {id: noteId}, true);
        addLabel(currentX, mainY + currentRadius + 12, noteId);

        if (parent) {
            drawLine(parentX + nodeRadius, mainY, currentX - currentRadius, mainY);
            createNode(parentX, mainY, parent, false);
        }

        if (children.length > 0) {
            drawLine(currentX + currentRadius, mainY, childX - nodeRadius, mainY);
            createNode(childX, mainY, children[0], false);
        }

        const forkX = 200;
        children.slice(1, 3).forEach((child, i) => {
            const y = branchStartY + (i * branchSpacing);
            drawLine(forkX, mainY, childX, y);
            createNode(childX, y, child, false);
        });

        if (children.length > 3) {
            addLabel(childX, branchStartY + (2 * branchSpacing) + 20, '+' + (children.length - 3) + ' more');
        }
    }
})();
</script>
{% endblock %}
```

**Step 2: Verify manually**

Run: `cd kasten && uvicorn src.main:app --reload`
Visit: https://kasten.gstoehl.dev/note/[note-with-source]
Expected: See source header if note has source

**Step 3: Commit**

```bash
cd kasten && git add src/templates/note.html && git commit -m "feat(ui): add source header to note template"
```

---

### Task 9: Add source header CSS styles

**Files:**
- Modify: `kasten/src/templates/base.html`

**Step 1: Add CSS for source header**

```css
/* Add to kasten/src/templates/base.html <style> section */
.source-header {
    padding: 1rem 0;
    border-bottom: 1px solid #000;
    margin-bottom: 1rem;
}

.source-title-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
}

.source-info {
    flex: 1;
}

.source-label {
    font-weight: normal;
}

.source-title {
    font-weight: bold;
}

.source-toggle {
    background: none;
    border: none;
    font-family: inherit;
    font-size: 1rem;
    cursor: pointer;
    padding: 0;
}

.source-toggle:hover {
    text-decoration: underline;
}

.source-meta {
    font-size: 0.875rem;
    color: #666;
    margin-top: 0.25rem;
}

.source-details {
    margin-top: 1rem;
}

.source-description {
    margin: 0 0 0.5rem 0;
}

.source-link {
    color: #000;
    text-decoration: underline;
}

.source-link:hover {
    text-decoration: none;
}
```

**Step 2: Verify manually**

Run: `cd kasten && uvicorn src.main:app --reload`
Expected: Source header styled correctly - monospace, brutalist aesthetic

**Step 3: Commit**

```bash
cd kasten && git add src/templates/base.html && git commit -m "feat(ui): add source header CSS styles"
```

---

## Phase 4: Integration & Testing

### Task 10: Add integration test for full flow

**Files:**
- Create: `kasten/tests/test_integration.py`

**Step 1: Create integration test**

```python
# kasten/tests/test_integration.py
import pytest
import tempfile
import os
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import init_db


async def setup_integration_env():
    """Setup clean test environment"""
    await init_db("sqlite+aiosqlite:///:memory:")
    tmpdir = tempfile.mkdtemp()
    os.environ["NOTES_PATH"] = tmpdir
    return tmpdir


@pytest.mark.asyncio
async def test_full_source_to_note_flow():
    """Test complete flow: create source -> create note with source -> view note with source"""
    await setup_integration_env()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create source (simulating what Canvas would do)
        source_resp = await client.post("/api/sources", json={
            "url": "https://youtu.be/ABC123",
            "title": "How to Learn Effectively",
            "description": "A video about spaced repetition and active recall",
            "video_id": "ABC123"
        })
        assert source_resp.status_code == 201
        source = source_resp.json()
        source_id = source["id"]

        # 2. Create note linked to source
        note_resp = await client.post("/api/notes", json={
            "title": "Learning Techniques",
            "content": "Key insight: Active recall beats passive review",
            "source_id": source_id
        })
        assert note_resp.status_code == 201
        note_id = note_resp.json()["id"]

        # 3. Get note via API - should include source
        get_resp = await client.get(f"/api/notes/{note_id}")
        assert get_resp.status_code == 200
        note_data = get_resp.json()

        assert note_data["source"] is not None
        assert note_data["source"]["url"] == "https://youtu.be/ABC123"
        assert note_data["source"]["title"] == "How to Learn Effectively"
        assert note_data["source"]["video_id"] == "ABC123"

        # 4. Get source - should list note
        source_get_resp = await client.get(f"/api/sources/{source_id}")
        assert source_get_resp.status_code == 200
        source_data = source_get_resp.json()
        assert note_id in source_data["note_ids"]

        # 5. View note page - should include source
        page_resp = await client.get(f"/note/{note_id}")
        assert page_resp.status_code == 200
        assert b"Source:" in page_resp.content
        assert b"How to Learn Effectively" in page_resp.content
        assert b"youtu.be" in page_resp.content


@pytest.mark.asyncio
async def test_note_without_source():
    """Test that notes without sources still work"""
    await setup_integration_env()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create note without source
        note_resp = await client.post("/api/notes", json={
            "title": "Standalone Note",
            "content": "No source for this one"
        })
        assert note_resp.status_code == 201
        note_id = note_resp.json()["id"]

        # Get note - source should be None
        get_resp = await client.get(f"/api/notes/{note_id}")
        note_data = get_resp.json()
        assert note_data["source"] is None

        # View note page - should NOT have source header
        page_resp = await client.get(f"/note/{note_id}")
        assert page_resp.status_code == 200
        assert b"Source:" not in page_resp.content
```

**Step 2: Run integration tests**

Run: `cd kasten && pytest tests/test_integration.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
cd kasten && git add tests/test_integration.py && git commit -m "test: add integration tests for source flow"
```

---

### Task 11: Run full test suite

**Step 1: Run all tests**

Run: `cd kasten && pytest -v`
Expected: All tests PASS

**Step 2: Fix any failures**

If tests fail, debug and fix before proceeding.

**Step 3: Commit any fixes**

```bash
cd kasten && git add -A && git commit -m "fix: address test failures"
```

---

### Task 12: Final manual verification

**Step 1: Start Kasten locally**

```bash
cd kasten && uvicorn src.main:app --reload --port 8001
```

**Step 2: Manual checklist**

- [ ] Can create source via API
- [ ] Can create note with source_id via API
- [ ] GET /api/notes/{id} includes source when present
- [ ] GET /api/sources/{id} shows linked note_ids
- [ ] Note page shows source header when source exists
- [ ] Source header expands/collapses on [+]/[-] click
- [ ] "Open original" link works
- [ ] Notes without sources display normally (no source header)

**Step 3: Final commit**

```bash
cd kasten && git add -A && git commit -m "feat: complete Kasten sources implementation"
```

---

## Summary

| Phase | Tasks | Key Changes |
|-------|-------|-------------|
| 1 | 1-2 | Data model (Source model, Note.source_id) |
| 2 | 3-6 | API endpoints (create/get sources, update notes) |
| 3 | 7-9 | UI (source header in template, CSS) |
| 4 | 10-12 | Integration testing and verification |

---

Plan complete and saved to `docs/plans/2025-12-24-kasten-sources-implementation.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
