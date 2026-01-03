# km Integration Phase 1: Sources → Processed

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable creating km notes from archived bookmarks with quote + addition + Luhmann connection

**Architecture:** Add `content` column to store Jina's full markdown, create `/km/notes` endpoint that calls km CLI, build UI modal for quote selection and note creation

**Tech Stack:** FastAPI, SQLAlchemy, Jinja2, km CLI (Rust), SQLite

---

## Task 1: Add content column to Bookmark model

**Files:**
- Modify: `src/models.py:10-24`

**Step 1: Add content column**

In `src/models.py`, add the content column to the Bookmark model:

```python
class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)  # Full markdown from Jina
    state = Column(SQLEnum(BookmarkState), default=BookmarkState.inbox, nullable=False, index=True)
    archive_url = Column(String, nullable=True)
    content_hash = Column(String, nullable=True)
    added_at = Column(DateTime, default=func.now(), nullable=False)
    read_at = Column(DateTime, nullable=True)
    video_id = Column(String, nullable=True)
    video_timestamp = Column(Integer, default=0)
```

**Step 2: Verify existing tests still pass**

Run: `cd /home/ags/bookmark-manager && python -m pytest tests/test_database.py -v`
Expected: PASS (no behavior change, just schema)

**Step 3: Commit**

```bash
git add src/models.py
git commit -m "feat: add content column to Bookmark model"
```

---

## Task 2: Store full content when processing bookmarks

**Files:**
- Modify: `src/services/background_jobs.py:46-67`

**Step 1: Write test for content storage**

Create `tests/test_content_storage.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from src.services.background_jobs import BackgroundJobService
from src.models import Bookmark, BookmarkState
from src.database import get_db, engine, Base
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async for session in get_db():
        yield session

@pytest.mark.asyncio
async def test_process_bookmark_stores_content(db_session):
    """Content from Jina should be stored in bookmark.content"""
    # Create bookmark
    bookmark = Bookmark(url="https://example.com", state=BookmarkState.inbox)
    db_session.add(bookmark)
    await db_session.commit()
    await db_session.refresh(bookmark)

    # Mock Jina response with content
    mock_metadata = {
        "title": "Test Article",
        "description": "A test",
        "content": "# Test Article\n\nThis is the full markdown content."
    }

    service = BackgroundJobService()
    with patch.object(service.jina_client, 'extract_metadata', new_callable=AsyncMock) as mock_jina:
        mock_jina.return_value = mock_metadata
        with patch.object(service, '_get_embedding_service') as mock_embed:
            mock_embed.return_value.generate_embedding.return_value = [0.1] * 384
            with patch.object(service.archive_service, 'submit_to_archive', new_callable=AsyncMock) as mock_archive:
                mock_archive.return_value = {"snapshot_url": "https://archive.org/test"}

                await service.process_new_bookmark(bookmark.id, db_session)

    # Refresh and check content was stored
    await db_session.refresh(bookmark)
    assert bookmark.content == "# Test Article\n\nThis is the full markdown content."
```

**Step 2: Run test to verify it fails**

Run: `cd /home/ags/bookmark-manager && python -m pytest tests/test_content_storage.py -v`
Expected: FAIL (content not stored yet)

**Step 3: Modify background_jobs.py to store content**

In `src/services/background_jobs.py`, after line 52, add:

```python
        bookmark.title = metadata.get("title", "Untitled")
        jina_description = metadata.get("description", "")
        full_content = metadata.get("content", "")

        # Store full content for note creation
        bookmark.content = full_content
```

**Step 4: Run test to verify it passes**

Run: `cd /home/ags/bookmark-manager && python -m pytest tests/test_content_storage.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/background_jobs.py tests/test_content_storage.py
git commit -m "feat: store full Jina content in bookmark.content"
```

---

## Task 3: Create km_notes tracking table

**Files:**
- Modify: `src/models.py`

**Step 1: Add KmNote model**

Add to `src/models.py`:

```python
class KmNote(Base):
    __tablename__ = "km_notes"

    id = Column(Integer, primary_key=True, index=True)
    km_id = Column(String, nullable=False, index=True)  # e.g., "20251218123456"
    source_type = Column(String, nullable=False)  # "bookmark" or "paper"
    source_id = Column(Integer, nullable=False, index=True)  # bookmark.id or zotero key
    quote = Column(Text, nullable=False)
    addition = Column(Text, nullable=False)
    connection_type = Column(String, nullable=True)  # "stump", "continues", "branches"
    connected_to = Column(String, nullable=True)  # km_id of connected note
    created_at = Column(DateTime, default=func.now(), nullable=False)
```

**Step 2: Verify tests pass**

Run: `cd /home/ags/bookmark-manager && python -m pytest tests/test_database.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/models.py
git commit -m "feat: add KmNote model for tracking created notes"
```

---

## Task 4: Create GET /bookmarks/{id}/content endpoint

**Files:**
- Modify: `src/routers/bookmarks.py`
- Modify: `src/schemas.py`

**Step 1: Write test for content endpoint**

Add to `tests/test_bookmarks_api.py`:

```python
@pytest.mark.asyncio
async def test_get_bookmark_content(client, db_session):
    """GET /bookmarks/{id}/content returns full content"""
    # Create bookmark with content
    bookmark = Bookmark(
        url="https://example.com/article",
        title="Test Article",
        content="# Full Content\n\nThis is the full markdown.",
        state=BookmarkState.inbox
    )
    db_session.add(bookmark)
    await db_session.commit()
    await db_session.refresh(bookmark)

    response = client.get(f"/bookmarks/{bookmark.id}/content")
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "# Full Content\n\nThis is the full markdown."
    assert data["title"] == "Test Article"
    assert data["url"] == "https://example.com/article"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/ags/bookmark-manager && python -m pytest tests/test_bookmarks_api.py::test_get_bookmark_content -v`
Expected: FAIL (endpoint doesn't exist)

**Step 3: Add schema**

Add to `src/schemas.py`:

```python
class BookmarkContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: Optional[str]
    content: Optional[str]
```

**Step 4: Add endpoint**

Add to `src/routers/bookmarks.py`:

```python
from src.schemas import BookmarkContentResponse

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
```

**Step 5: Run test to verify it passes**

Run: `cd /home/ags/bookmark-manager && python -m pytest tests/test_bookmarks_api.py::test_get_bookmark_content -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/routers/bookmarks.py src/schemas.py tests/test_bookmarks_api.py
git commit -m "feat: add GET /bookmarks/{id}/content endpoint"
```

---

## Task 5: Create km service for note creation

**Files:**
- Create: `src/services/km_service.py`
- Create: `tests/test_km_service.py`

**Step 1: Write test for km service**

Create `tests/test_km_service.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from src.services.km_service import KmService

def test_km_service_creates_note_file():
    """KmService should create a properly formatted note"""
    service = KmService(notes_dir="/tmp/test_notes")

    note_content = service.format_note(
        title="My Insight",
        quote="This is a key passage from the source",
        addition="I think this means X because Y",
        source_title="Article Title",
        source_url="https://example.com/article",
        connection_type="continues",
        connected_to="20251218120000"
    )

    expected = '''# My Insight

> "This is a key passage from the source"

I think this means X because Y

---
Source: [Article Title](https://example.com/article)
Connected to: [[20251218120000]] (continues)
'''
    assert note_content == expected

def test_km_service_creates_stump_note():
    """Stump notes should have no connection"""
    service = KmService(notes_dir="/tmp/test_notes")

    note_content = service.format_note(
        title="New Thought",
        quote="Starting point",
        addition="This begins a new chain",
        source_title="Source",
        source_url="https://example.com",
        connection_type="stump",
        connected_to=None
    )

    assert "Connected to:" not in note_content

@pytest.mark.asyncio
async def test_km_service_calls_km_cli():
    """KmService should call km new command"""
    service = KmService(notes_dir="/home/ags/notes")

    with patch('asyncio.create_subprocess_exec') as mock_exec:
        mock_process = MagicMock()
        mock_process.communicate = MagicMock(return_value=(b"Created: 20251218123456.md", b""))
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        km_id = await service.create_note(
            title="Test Note",
            quote="Quote",
            addition="Addition",
            source_title="Source",
            source_url="https://example.com",
            connection_type="stump",
            connected_to=None
        )

        assert km_id is not None
```

**Step 2: Run test to verify it fails**

Run: `cd /home/ags/bookmark-manager && python -m pytest tests/test_km_service.py -v`
Expected: FAIL (module doesn't exist)

**Step 3: Create km_service.py**

Create `src/services/km_service.py`:

```python
import asyncio
import os
import re
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class KmService:
    def __init__(self, notes_dir: str = "/home/ags/notes"):
        self.notes_dir = notes_dir

    def format_note(
        self,
        title: str,
        quote: str,
        addition: str,
        source_title: str,
        source_url: str,
        connection_type: str,
        connected_to: Optional[str]
    ) -> str:
        """Format a km note with quote, addition, and source"""
        lines = [
            f"# {title}",
            "",
            f'> "{quote}"',
            "",
            addition,
            "",
            "---",
            f"Source: [{source_title}]({source_url})",
        ]

        if connection_type != "stump" and connected_to:
            lines.append(f"Connected to: [[{connected_to}]] ({connection_type})")

        return "\n".join(lines) + "\n"

    async def create_note(
        self,
        title: str,
        quote: str,
        addition: str,
        source_title: str,
        source_url: str,
        connection_type: str,
        connected_to: Optional[str]
    ) -> Optional[str]:
        """Create a km note and return its ID"""
        content = self.format_note(
            title=title,
            quote=quote,
            addition=addition,
            source_title=source_title,
            source_url=source_url,
            connection_type=connection_type,
            connected_to=connected_to
        )

        # Generate timestamp-based filename
        km_id = datetime.now().strftime("%Y%m%d%H%M%S")
        filepath = os.path.join(self.notes_dir, f"{km_id}.md")

        # Write note directly (km new just opens editor)
        try:
            with open(filepath, 'w') as f:
                f.write(content)
            logger.info(f"Created km note: {km_id}")
            return km_id
        except Exception as e:
            logger.error(f"Failed to create km note: {e}")
            return None
```

**Step 4: Run test to verify it passes**

Run: `cd /home/ags/bookmark-manager && python -m pytest tests/test_km_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/km_service.py tests/test_km_service.py
git commit -m "feat: add KmService for creating km notes"
```

---

## Task 6: Create POST /km/notes endpoint

**Files:**
- Create: `src/routers/km.py`
- Modify: `src/main.py`
- Modify: `src/schemas.py`

**Step 1: Write test for endpoint**

Create `tests/test_km_api.py`:

```python
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from src.main import app
from src.models import Bookmark, BookmarkState, KmNote
from src.database import get_db, engine, Base

client = TestClient(app)

@pytest.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async for session in get_db():
        yield session

@pytest.mark.asyncio
async def test_create_km_note_from_bookmark(db_session):
    """POST /km/notes creates a note and tracks it"""
    # Create source bookmark
    bookmark = Bookmark(
        url="https://example.com/article",
        title="Test Article",
        content="Full content here",
        state=BookmarkState.read
    )
    db_session.add(bookmark)
    await db_session.commit()
    await db_session.refresh(bookmark)

    with patch('src.routers.km.km_service.create_note', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = "20251218123456"

        response = client.post("/km/notes", json={
            "source_type": "bookmark",
            "source_id": bookmark.id,
            "title": "My Insight",
            "quote": "Key passage",
            "addition": "My thoughts on this",
            "connection_type": "stump",
            "connected_to": None
        })

    assert response.status_code == 201
    data = response.json()
    assert data["km_id"] == "20251218123456"
    assert data["source_type"] == "bookmark"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/ags/bookmark-manager && python -m pytest tests/test_km_api.py -v`
Expected: FAIL (endpoint doesn't exist)

**Step 3: Add schemas**

Add to `src/schemas.py`:

```python
class KmNoteCreate(BaseModel):
    source_type: Literal["bookmark", "paper"]
    source_id: int
    title: str
    quote: str
    addition: str
    connection_type: Literal["stump", "continues", "branches"]
    connected_to: Optional[str] = None

class KmNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    km_id: str
    source_type: str
    source_id: int
    quote: str
    addition: str
    connection_type: Optional[str]
    connected_to: Optional[str]
    created_at: datetime
```

**Step 4: Create km router**

Create `src/routers/km.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models import Bookmark, KmNote
from src.schemas import KmNoteCreate, KmNoteResponse
from src.services.km_service import KmService

router = APIRouter(prefix="/km", tags=["km"])
km_service = KmService()

@router.post("/notes", response_model=KmNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_km_note(
    note_data: KmNoteCreate,
    session: AsyncSession = Depends(get_db)
):
    """Create a km note from a bookmark or paper"""

    # Get source for metadata
    if note_data.source_type == "bookmark":
        source = await session.get(Bookmark, note_data.source_id)
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bookmark not found"
            )
        source_title = source.title or "Untitled"
        source_url = source.url
    else:
        # TODO: Zotero paper support
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paper source not yet supported"
        )

    # Create km note
    km_id = await km_service.create_note(
        title=note_data.title,
        quote=note_data.quote,
        addition=note_data.addition,
        source_title=source_title,
        source_url=source_url,
        connection_type=note_data.connection_type,
        connected_to=note_data.connected_to
    )

    if not km_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create km note"
        )

    # Track the note
    km_note = KmNote(
        km_id=km_id,
        source_type=note_data.source_type,
        source_id=note_data.source_id,
        quote=note_data.quote,
        addition=note_data.addition,
        connection_type=note_data.connection_type,
        connected_to=note_data.connected_to
    )
    session.add(km_note)
    await session.commit()
    await session.refresh(km_note)

    return km_note
```

**Step 5: Register router in main.py**

Add to `src/main.py` after other router imports:

```python
from src.routers import km

# After other router includes:
app.include_router(km.router)
```

**Step 6: Run test to verify it passes**

Run: `cd /home/ags/bookmark-manager && python -m pytest tests/test_km_api.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/routers/km.py src/schemas.py src/main.py tests/test_km_api.py
git commit -m "feat: add POST /km/notes endpoint"
```

---

## Task 7: Add "Add Note" button to detail panel UI

**Files:**
- Modify: `src/templates/index.html`

**Step 1: Add button to detail panel**

In `src/templates/index.html`, find the `renderDetail` function and add an "Add Note" button after the existing action buttons (around line 215):

```javascript
<button class="btn" onclick="openNoteModal(${data.id})">Add Note</button>
```

**Step 2: Verify button appears**

Run: `cd /home/ags/bookmark-manager && python -m uvicorn src.main:app --reload`
Navigate to archive view, select a bookmark, verify "Add Note" button appears.

**Step 3: Commit**

```bash
git add src/templates/index.html
git commit -m "feat: add 'Add Note' button to bookmark detail panel"
```

---

## Task 8: Create note creation modal

**Files:**
- Modify: `src/templates/index.html`
- Modify: `src/templates/base.html`

**Step 1: Add modal HTML to base.html**

Add before `</body>` in `src/templates/base.html`:

```html
<!-- Note Creation Modal -->
<div id="note-modal" class="modal" style="display: none;">
    <div class="modal-content">
        <div class="modal-header">
            <h2>Add Note</h2>
            <button class="btn" onclick="closeNoteModal()">×</button>
        </div>
        <div class="modal-body">
            <div id="note-source-content" class="source-content">
                Loading content...
            </div>
            <div class="note-form">
                <div class="form-group">
                    <label>Selected Quote</label>
                    <textarea id="note-quote" readonly placeholder="Select text above to quote"></textarea>
                </div>
                <div class="form-group">
                    <label>Title (your idea)</label>
                    <input type="text" id="note-title" placeholder="What's the insight?">
                </div>
                <div class="form-group">
                    <label>Your Addition (not summary!)</label>
                    <textarea id="note-addition" placeholder="What do YOU add to this idea?"></textarea>
                </div>
                <div class="form-group">
                    <label>Connection</label>
                    <div class="connection-options">
                        <label><input type="radio" name="connection" value="stump" checked> New chain (stump)</label>
                        <label><input type="radio" name="connection" value="continues"> Continues existing note</label>
                        <label><input type="radio" name="connection" value="branches"> Branches from note</label>
                    </div>
                    <input type="text" id="note-connected-to" placeholder="Note ID to connect to" style="display: none;">
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn" onclick="closeNoteModal()">Cancel</button>
            <button class="btn btn-primary" onclick="createNote()" id="create-note-btn" disabled>Create Note</button>
        </div>
    </div>
</div>
```

**Step 2: Add modal styles to base.html**

Add to the `<style>` section in `src/templates/base.html`:

```css
/* Modal */
.modal {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.8);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
}

.modal-content {
    background: var(--surface);
    border-radius: 8px;
    width: 90%;
    max-width: 800px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
}

.modal-header {
    padding: 1rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal-body {
    padding: 1rem;
    overflow-y: auto;
    flex: 1;
}

.modal-footer {
    padding: 1rem;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
}

.source-content {
    background: var(--background);
    padding: 1rem;
    border-radius: 4px;
    max-height: 200px;
    overflow-y: auto;
    margin-bottom: 1rem;
    user-select: text;
}

.note-form .form-group {
    margin-bottom: 1rem;
}

.note-form label {
    display: block;
    margin-bottom: 0.25rem;
    font-weight: 500;
}

.note-form input[type="text"],
.note-form textarea {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--background);
    color: var(--text);
}

.note-form textarea {
    min-height: 80px;
    resize: vertical;
}

.connection-options label {
    display: block;
    margin: 0.25rem 0;
}
```

**Step 3: Add modal JavaScript to index.html**

Add to the script section in `src/templates/index.html`:

```javascript
// Note modal state
let currentNoteBookmarkId = null;

// Open note modal
window.openNoteModal = async function(bookmarkId) {
    currentNoteBookmarkId = bookmarkId;
    const modal = document.getElementById('note-modal');
    const contentDiv = document.getElementById('note-source-content');

    modal.style.display = 'flex';
    contentDiv.innerHTML = 'Loading content...';

    try {
        const res = await fetch(`${API_BASE}/${bookmarkId}/content`);
        const data = await res.json();

        // Render markdown content as HTML (basic)
        contentDiv.innerHTML = data.content || 'No content available';

        // Setup text selection listener
        contentDiv.addEventListener('mouseup', handleTextSelection);
    } catch (err) {
        contentDiv.innerHTML = 'Failed to load content';
        console.error(err);
    }
};

// Handle text selection for quote
function handleTextSelection() {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (selectedText) {
        document.getElementById('note-quote').value = selectedText;
        updateCreateButton();
    }
}

// Update create button state
function updateCreateButton() {
    const quote = document.getElementById('note-quote').value.trim();
    const title = document.getElementById('note-title').value.trim();
    const addition = document.getElementById('note-addition').value.trim();

    const btn = document.getElementById('create-note-btn');
    btn.disabled = !(quote && title && addition);
}

// Add input listeners
document.getElementById('note-title')?.addEventListener('input', updateCreateButton);
document.getElementById('note-addition')?.addEventListener('input', updateCreateButton);

// Connection type toggle
document.querySelectorAll('input[name="connection"]').forEach(radio => {
    radio.addEventListener('change', function() {
        const connectedToInput = document.getElementById('note-connected-to');
        connectedToInput.style.display = this.value === 'stump' ? 'none' : 'block';
    });
});

// Close modal
window.closeNoteModal = function() {
    document.getElementById('note-modal').style.display = 'none';
    currentNoteBookmarkId = null;

    // Reset form
    document.getElementById('note-quote').value = '';
    document.getElementById('note-title').value = '';
    document.getElementById('note-addition').value = '';
    document.getElementById('note-connected-to').value = '';
    document.querySelector('input[name="connection"][value="stump"]').checked = true;
    document.getElementById('note-connected-to').style.display = 'none';
};

// Create note
window.createNote = async function() {
    const quote = document.getElementById('note-quote').value.trim();
    const title = document.getElementById('note-title').value.trim();
    const addition = document.getElementById('note-addition').value.trim();
    const connectionType = document.querySelector('input[name="connection"]:checked').value;
    const connectedTo = document.getElementById('note-connected-to').value.trim() || null;

    try {
        const res = await fetch('/km/notes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_type: 'bookmark',
                source_id: currentNoteBookmarkId,
                title: title,
                quote: quote,
                addition: addition,
                connection_type: connectionType,
                connected_to: connectedTo
            })
        });

        if (res.ok) {
            const data = await res.json();
            alert(`Note created: ${data.km_id}`);
            closeNoteModal();
        } else {
            const error = await res.json();
            alert(`Failed to create note: ${error.detail}`);
        }
    } catch (err) {
        alert('Failed to create note');
        console.error(err);
    }
};
```

**Step 4: Test the full flow manually**

1. Run: `cd /home/ags/bookmark-manager && python -m uvicorn src.main:app --reload`
2. Navigate to archive view
3. Select a bookmark with content
4. Click "Add Note"
5. Select text to quote
6. Fill in title and addition
7. Click "Create Note"
8. Verify note is created in /home/ags/notes/

**Step 5: Commit**

```bash
git add src/templates/index.html src/templates/base.html
git commit -m "feat: add note creation modal UI"
```

---

## Task 9: Run all tests and verify

**Files:** None (verification only)

**Step 1: Run full test suite**

Run: `cd /home/ags/bookmark-manager && python -m pytest -v`
Expected: All tests PASS

**Step 2: Manual smoke test**

1. Create a new bookmark
2. Wait for processing (content should be stored)
3. Archive the bookmark
4. Open "Add Note" modal
5. Create a note with quote + addition
6. Verify note exists in /home/ags/notes/

**Step 3: Final commit if needed**

```bash
git status
# If any uncommitted changes:
git add .
git commit -m "chore: cleanup after phase 1 implementation"
```

---

## Summary

After completing all tasks, Phase 1 provides:

1. **Content storage** - Jina markdown stored in `bookmark.content`
2. **Content endpoint** - `GET /bookmarks/{id}/content`
3. **km service** - Creates properly formatted notes
4. **km API** - `POST /km/notes` with tracking
5. **UI modal** - Quote selection + addition + connection type

Next phase will add the Processed tab (km notes visualization) and Zotero paper support.
