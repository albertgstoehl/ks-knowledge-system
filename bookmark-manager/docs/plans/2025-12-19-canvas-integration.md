# Bookmark-Manager Canvas Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace "Add Note" with "Cite this" button that pushes selected quotes to Canvas.

**Architecture:** Remove km note creation entirely. Add `/canvas/quotes` endpoint that proxies to Canvas API. Simplify modal to show source content with text selection. Selected text + source metadata sent to Canvas.

**Tech Stack:** FastAPI, httpx (HTTP client), Vanilla JS, Playwright (E2E tests)

---

## Task 1: Remove KM Note Creation

This is a refactor task - removing unused code. No new tests needed since we're deleting functionality.

**Files:**
- Delete: `src/routers/km.py`
- Delete: `src/services/km_service.py`
- Modify: `src/main.py:8,15` (remove km router)
- Modify: `src/models.py` (remove KmNote)
- Modify: `src/schemas.py` (remove km schemas)

**Step 1: Remove km router import and registration from main.py**

In `src/main.py`, remove the km import and router registration.

**Step 2: Delete km router file**

```bash
rm /home/ags/knowledge-system/bookmark-manager/src/routers/km.py
```

**Step 3: Delete km service file**

```bash
rm /home/ags/knowledge-system/bookmark-manager/src/services/km_service.py
```

**Step 4: Remove KmNote model from models.py**

Remove the `KmNote` class from `src/models.py`.

**Step 5: Remove km schemas from schemas.py**

Remove `KmNoteCreate` and `KmNoteResponse` from `src/schemas.py`.

**Step 6: Verify app starts**

```bash
cd /home/ags/knowledge-system/bookmark-manager && python -m uvicorn src.main:app --host 0.0.0.0 --port 8001
```

Expected: App starts without import errors

**Step 7: Commit**

```bash
git add -A && git commit -m "chore: remove km note creation (moves to Canvas)"
```

---

## Task 2: Add Canvas Quote Schema

**Files:**
- Modify: `src/schemas.py`

**Step 1: Add quote schemas to schemas.py**

Add to `src/schemas.py`:

```python
class CanvasQuoteCreate(BaseModel):
    bookmark_id: int
    quote: str

class CanvasQuoteResponse(BaseModel):
    success: bool
    message: str
```

**Step 2: Verify schema imports work**

```bash
cd /home/ags/knowledge-system/bookmark-manager && python -c "from src.schemas import CanvasQuoteCreate, CanvasQuoteResponse; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add -A && git commit -m "feat: add canvas quote schemas"
```

---

## Task 3: Write Failing Test for Canvas Quote Endpoint

**Files:**
- Create: `tests/test_canvas.py`

**Step 1: Add httpx dependency**

```bash
cd /home/ags/knowledge-system/bookmark-manager && uv add httpx
```

**Step 2: Write the failing test**

Create `tests/test_canvas.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_push_quote_to_canvas(async_client, test_bookmark):
    """Test pushing a quote to Canvas"""

    with patch('src.routers.canvas.httpx.AsyncClient') as mock_client_class:
        # Setup mock
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        response = await async_client.post(
            "/canvas/quotes",
            json={
                "bookmark_id": test_bookmark.id,
                "quote": "Test quote from source"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@pytest.mark.asyncio
async def test_push_quote_bookmark_not_found(async_client):
    """Test pushing quote for non-existent bookmark"""

    response = await async_client.post(
        "/canvas/quotes",
        json={
            "bookmark_id": 99999,
            "quote": "Test quote"
        }
    )

    assert response.status_code == 404
```

**Step 3: Run test to verify it fails**

```bash
cd /home/ags/knowledge-system/bookmark-manager && pytest tests/test_canvas.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.routers.canvas'`

**Step 4: Commit**

```bash
git add -A && git commit -m "test: add failing tests for canvas quote endpoint"
```

---

## Task 4: Implement Canvas Quote Endpoint

**Files:**
- Create: `src/routers/canvas.py`
- Modify: `src/main.py` (add router)

**Step 1: Create canvas router**

Create `src/routers/canvas.py`:

```python
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models import Bookmark
from src.schemas import CanvasQuoteCreate, CanvasQuoteResponse

router = APIRouter(prefix="/canvas", tags=["canvas"])

CANVAS_API_URL = os.getenv("CANVAS_API_URL", "http://canvas:8000/api/quotes")


@router.post("/quotes", response_model=CanvasQuoteResponse)
async def push_quote_to_canvas(
    data: CanvasQuoteCreate,
    session: AsyncSession = Depends(get_db)
):
    """Push a quote to Canvas draft mode"""

    # Get bookmark for source metadata
    bookmark = await session.get(Bookmark, data.bookmark_id)
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    # Push to Canvas
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                CANVAS_API_URL,
                json={
                    "text": data.quote,
                    "source_url": bookmark.url,
                    "source_title": bookmark.title or "Untitled"
                },
                timeout=10.0
            )
            response.raise_for_status()
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Canvas service unavailable: {str(e)}"
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Canvas error: {e.response.text}"
            )

    return CanvasQuoteResponse(success=True, message="Quote sent to Canvas")
```

**Step 2: Register router in main.py**

Add to `src/main.py` imports:

```python
from src.routers import canvas
```

Add to router registrations:

```python
app.include_router(canvas.router)
```

**Step 3: Run tests to verify they pass**

```bash
cd /home/ags/knowledge-system/bookmark-manager && pytest tests/test_canvas.py -v
```

Expected: All tests PASS

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: implement canvas quote endpoint"
```

---

## Task 5: Write Failing Test for Canvas Unavailable

**Files:**
- Modify: `tests/test_canvas.py`

**Step 1: Write the failing test**

Add to `tests/test_canvas.py`:

```python
@pytest.mark.asyncio
async def test_push_quote_canvas_unavailable(async_client, test_bookmark):
    """Test handling when Canvas is unavailable"""

    with patch('src.routers.canvas.httpx.AsyncClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(
            side_effect=httpx.RequestError("Connection refused")
        )
        mock_client_class.return_value = mock_client

        response = await async_client.post(
            "/canvas/quotes",
            json={
                "bookmark_id": test_bookmark.id,
                "quote": "Test quote"
            }
        )

        assert response.status_code == 503
```

Also add import at top:

```python
import httpx
```

**Step 2: Run test to verify it passes**

```bash
cd /home/ags/knowledge-system/bookmark-manager && pytest tests/test_canvas.py::test_push_quote_canvas_unavailable -v
```

Expected: PASS (implementation already handles this)

**Step 3: Commit**

```bash
git add -A && git commit -m "test: add canvas unavailable test"
```

---

## Task 6: Simplify Modal HTML

**Files:**
- Modify: `src/templates/base.html:508-548`

**Step 1: Replace note-modal with cite-modal**

In `src/templates/base.html`, replace the note-modal section (lines 508-548) with:

```html
<!-- Citation Modal -->
<div id="cite-modal" class="modal" style="display: none;">
    <div class="modal-content">
        <div class="modal-header">
            <h2>Cite</h2>
            <button class="btn" onclick="closeCiteModal()">×</button>
        </div>
        <div class="modal-body" style="grid-template-columns: 1fr;">
            <div id="cite-source-content" class="source-content">
                Loading...
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn" onclick="closeCiteModal()">Cancel</button>
            <button class="btn btn-primary" onclick="citeSelection()" id="cite-btn" disabled>Cite this</button>
        </div>
    </div>
</div>
```

**Step 2: Remove unused CSS**

Remove CSS for `.note-form`, `.form-group`, `.connection-options`, `#note-connected-to` (lines 388-482).

**Step 3: Verify page loads**

```bash
cd /home/ags/knowledge-system/bookmark-manager && python -m uvicorn src.main:app --host 0.0.0.0 --port 8001
```

Open http://localhost:8001 and inspect - modal HTML should be present.

**Step 4: Commit**

```bash
git add -A && git commit -m "refactor: simplify modal to citation view"
```

---

## Task 7: Update Button and JavaScript

**Files:**
- Modify: `src/templates/index.html:215,330-448`

**Step 1: Change button in renderDetail**

In `src/templates/index.html`, line 215, change:

```javascript
<button class="btn" onclick="openNoteModal(${data.id})">Add Note</button>
```

to:

```javascript
<button class="btn" onclick="openCiteModal(${data.id})">Cite</button>
```

**Step 2: Replace modal JavaScript**

Replace the note modal JS (lines 330-448) with:

```javascript
let currentCiteBookmarkId = null;

window.openCiteModal = async function(bookmarkId) {
    currentCiteBookmarkId = bookmarkId;
    const modal = document.getElementById('cite-modal');
    const contentDiv = document.getElementById('cite-source-content');
    const citeBtn = document.getElementById('cite-btn');

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

// Handle text selection
let selectionTimeout;
document.addEventListener('selectionchange', () => {
    clearTimeout(selectionTimeout);

    selectionTimeout = setTimeout(() => {
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
    }, 300);
});

window.closeCiteModal = function() {
    document.getElementById('cite-modal').style.display = 'none';
    currentCiteBookmarkId = null;
    document.getElementById('cite-btn').disabled = true;
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
```

**Step 3: Verify UI manually**

1. Open http://localhost:8001
2. Click a bookmark
3. Click "Cite" button
4. Modal opens with source content
5. Select text - "Cite this" button enables
6. Deselect - button disables

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: implement cite button with text selection"
```

---

## Task 8: Write Playwright E2E Test

**Files:**
- Create: `tests/e2e/test_cite.py`

**Step 1: Write the E2E test**

Create `tests/e2e/test_cite.py`:

```python
import pytest
from playwright.async_api import Page, expect


@pytest.mark.asyncio
async def test_cite_modal_opens(page: Page, live_server):
    """Test that cite modal opens when clicking Cite button"""
    await page.goto(live_server)

    # Wait for bookmarks to load
    await page.wait_for_selector('.bookmark-item')

    # Click first bookmark
    await page.click('.bookmark-item')

    # Click Cite button
    await page.click('button:has-text("Cite")')

    # Modal should be visible
    modal = page.locator('#cite-modal')
    await expect(modal).to_be_visible()

    # Cite button should be disabled initially
    cite_btn = page.locator('#cite-btn')
    await expect(cite_btn).to_be_disabled()


@pytest.mark.asyncio
async def test_cite_button_enables_on_selection(page: Page, live_server):
    """Test that selecting text enables the Cite button"""
    await page.goto(live_server)

    await page.wait_for_selector('.bookmark-item')
    await page.click('.bookmark-item')
    await page.click('button:has-text("Cite")')

    # Wait for content to load
    await page.wait_for_selector('#cite-source-content:not(:has-text("Loading"))')

    # Select text in source content
    await page.evaluate('''() => {
        const content = document.getElementById('cite-source-content');
        const range = document.createRange();
        range.selectNodeContents(content);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
    }''')

    # Wait for selection debounce
    await page.wait_for_timeout(400)

    # Cite button should be enabled
    cite_btn = page.locator('#cite-btn')
    await expect(cite_btn).to_be_enabled()
```

**Step 2: Run E2E test**

```bash
cd /home/ags/knowledge-system/bookmark-manager && pytest tests/e2e/test_cite.py -v
```

Expected: Tests pass

**Step 3: Commit**

```bash
git add -A && git commit -m "test: add playwright e2e tests for cite flow"
```

---

## Task 9: Update Docker Compose

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Add CANVAS_API_URL environment variable**

In `docker-compose.yml`, add to the bookmark-manager service:

```yaml
environment:
  - CANVAS_API_URL=http://canvas:8000/api/quotes
```

**Step 2: Verify docker-compose config is valid**

```bash
cd /home/ags/knowledge-system/bookmark-manager && docker compose config
```

Expected: Valid YAML output with environment variable

**Step 3: Commit**

```bash
git add -A && git commit -m "chore: configure canvas URL in docker-compose"
```

---

## Summary

**Removed:**
- `src/routers/km.py`
- `src/services/km_service.py`
- KmNote model
- km schemas
- Note creation form CSS

**Added:**
- `src/routers/canvas.py` with `/canvas/quotes` endpoint
- `CanvasQuoteCreate` and `CanvasQuoteResponse` schemas
- `tests/test_canvas.py` with unit tests
- `tests/e2e/test_cite.py` with Playwright tests
- Simplified cite modal HTML
- Text selection JavaScript

**Data Flow:**
```
User selects text → Cite this → POST /canvas/quotes → Canvas API
                                      ↓
                              { text, source_url, source_title }
```
