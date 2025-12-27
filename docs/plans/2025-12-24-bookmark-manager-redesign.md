# Bookmark Manager Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform bookmark manager from archive-based to ephemeral capture system with expiry pressure, where content flows to Kasten instead of internal archive.

**Architecture:** Remove Archive concept entirely. Bookmarks expire after 7 days unless protected (thesis/pinned). Navigation becomes Feeds | Inbox | Thesis | Pins. Process action redirects to Canvas for note creation, which archives to Kasten.

**Tech Stack:** FastAPI, SQLAlchemy, Jinja2 templates, Python-telegram-bot

---

## Phase 1: Data Model & Schema Changes

### Task 1: Add expires_at column and rename is_paper to is_thesis in model

**Files:**
- Modify: `bookmark-manager/src/models.py:10-28`
- Test: `bookmark-manager/tests/test_database.py`

**Step 1: Write failing test for expires_at column**

```python
# In tests/test_database.py - add this test
@pytest.mark.asyncio
async def test_bookmark_has_expires_at_column(session):
    """Test that bookmark model has expires_at column"""
    from datetime import datetime, timedelta
    from src.models import Bookmark, BookmarkState

    expires = datetime.utcnow() + timedelta(days=7)
    bookmark = Bookmark(
        url="https://example.com/expiry-test",
        state=BookmarkState.inbox,
        expires_at=expires
    )
    session.add(bookmark)
    await session.commit()
    await session.refresh(bookmark)

    assert bookmark.expires_at is not None
    assert abs((bookmark.expires_at - expires).total_seconds()) < 1
```

**Step 2: Run test to verify it fails**

Run: `cd bookmark-manager && pytest tests/test_database.py::test_bookmark_has_expires_at_column -v`
Expected: FAIL with "unexpected keyword argument 'expires_at'"

**Step 3: Add expires_at column to Bookmark model**

```python
# In src/models.py - update Bookmark class
class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    state = Column(SQLEnum(BookmarkState), default=BookmarkState.inbox, nullable=False, index=True)
    archive_url = Column(String, nullable=True)
    content_hash = Column(String, nullable=True)
    added_at = Column(DateTime, default=func.now(), nullable=False)
    read_at = Column(DateTime, nullable=True)
    video_id = Column(String, nullable=True)
    video_timestamp = Column(Integer, default=0)
    is_thesis = Column(Boolean, default=False, index=True)  # Renamed from is_paper
    pinned = Column(Boolean, default=False, index=True)
    zotero_key = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # NULL = never expires
```

**Step 4: Run test to verify it passes**

Run: `cd bookmark-manager && pytest tests/test_database.py::test_bookmark_has_expires_at_column -v`
Expected: PASS

**Step 5: Commit**

```bash
cd bookmark-manager && git add src/models.py tests/test_database.py && git commit -m "feat(models): add expires_at column and rename is_paper to is_thesis"
```

---

### Task 2: Update schemas with is_thesis and expires_at

**Files:**
- Modify: `bookmark-manager/src/schemas.py`
- Test: `bookmark-manager/tests/test_bookmarks_api.py`

**Step 1: Write failing test for is_thesis in response**

```python
# In tests/test_bookmarks_api.py - add/modify test
@pytest.mark.asyncio
async def test_bookmark_response_has_is_thesis(client):
    """Test that bookmark response includes is_thesis field"""
    response = await client.post("/bookmarks", json={"url": "https://example.com/thesis-test"})
    assert response.status_code == 201
    data = response.json()
    assert "is_thesis" in data
    assert "expires_at" in data
```

**Step 2: Run test to verify it fails**

Run: `cd bookmark-manager && pytest tests/test_bookmarks_api.py::test_bookmark_response_has_is_thesis -v`
Expected: FAIL with "is_thesis" not in data

**Step 3: Update schemas**

```python
# In src/schemas.py - update BookmarkResponse
class BookmarkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: Optional[str]
    description: Optional[str]
    state: str
    archive_url: Optional[str]
    added_at: datetime
    read_at: Optional[datetime]
    video_id: Optional[str]
    video_timestamp: int = 0
    is_thesis: bool = False  # Renamed from is_paper
    pinned: bool = False
    zotero_key: Optional[str] = None
    expires_at: Optional[datetime] = None  # Added


# Rename BookmarkPaperUpdate to BookmarkThesisUpdate
class BookmarkThesisUpdate(BaseModel):
    is_thesis: bool
```

**Step 4: Run test to verify it passes**

Run: `cd bookmark-manager && pytest tests/test_bookmarks_api.py::test_bookmark_response_has_is_thesis -v`
Expected: PASS

**Step 5: Commit**

```bash
cd bookmark-manager && git add src/schemas.py tests/test_bookmarks_api.py && git commit -m "feat(schemas): rename is_paper to is_thesis, add expires_at"
```

---

## Phase 2: API Endpoint Changes

### Task 3: Update bookmark creation with expiry calculation

**Files:**
- Modify: `bookmark-manager/src/routers/bookmarks.py:30-78`
- Test: `bookmark-manager/tests/test_bookmarks_api.py`

**Step 1: Write failing test for expiry on create**

```python
# In tests/test_bookmarks_api.py
@pytest.mark.asyncio
async def test_bookmark_expires_in_7_days(client):
    """Regular bookmarks expire in 7 days"""
    from datetime import datetime, timedelta

    response = await client.post("/bookmarks", json={"url": "https://example.com/expiry-calc"})
    assert response.status_code == 201
    data = response.json()

    expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
    expected = datetime.utcnow() + timedelta(days=7)

    # Within 1 minute of expected
    assert abs((expires_at - expected).total_seconds()) < 60


@pytest.mark.asyncio
async def test_thesis_bookmark_never_expires(client, monkeypatch):
    """Thesis bookmarks don't expire"""
    # Mock is_academic_url to return True
    monkeypatch.setattr("src.routers.bookmarks.is_academic_url", lambda x: True)

    response = await client.post("/bookmarks", json={"url": "https://arxiv.org/paper123"})
    assert response.status_code == 201
    data = response.json()

    assert data["expires_at"] is None
    assert data["is_thesis"] is True
```

**Step 2: Run tests to verify they fail**

Run: `cd bookmark-manager && pytest tests/test_bookmarks_api.py::test_bookmark_expires_in_7_days tests/test_bookmarks_api.py::test_thesis_bookmark_never_expires -v`
Expected: FAIL

**Step 3: Update create_bookmark with expiry logic**

```python
# In src/routers/bookmarks.py - update create_bookmark function
from datetime import datetime, timedelta

def calculate_expiry(pinned: bool, is_thesis: bool) -> Optional[datetime]:
    """Calculate expiry date. Returns None for protected items."""
    if pinned or is_thesis:
        return None
    return datetime.utcnow() + timedelta(days=7)


@router.post("", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    bookmark_data: BookmarkCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    """Create a new bookmark"""
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
```

**Step 4: Run tests to verify they pass**

Run: `cd bookmark-manager && pytest tests/test_bookmarks_api.py::test_bookmark_expires_in_7_days tests/test_bookmarks_api.py::test_thesis_bookmark_never_expires -v`
Expected: PASS

**Step 5: Commit**

```bash
cd bookmark-manager && git add src/routers/bookmarks.py tests/test_bookmarks_api.py && git commit -m "feat(api): add expiry calculation on bookmark create"
```

---

### Task 4: Rename /paper endpoint to /thesis

**Files:**
- Modify: `bookmark-manager/src/routers/bookmarks.py:284-299`
- Test: `bookmark-manager/tests/test_bookmarks_api.py`

**Step 1: Write failing test for /thesis endpoint**

```python
# In tests/test_bookmarks_api.py
@pytest.mark.asyncio
async def test_toggle_thesis_endpoint(client):
    """Test /thesis endpoint exists and works"""
    # Create bookmark first
    create_resp = await client.post("/bookmarks", json={"url": "https://example.com/thesis-toggle"})
    bookmark_id = create_resp.json()["id"]

    # Toggle thesis
    response = await client.patch(
        f"/bookmarks/{bookmark_id}/thesis",
        json={"is_thesis": True}
    )
    assert response.status_code == 200
    assert response.json()["is_thesis"] is True
    assert response.json()["expires_at"] is None  # Should clear expiry
```

**Step 2: Run test to verify it fails**

Run: `cd bookmark-manager && pytest tests/test_bookmarks_api.py::test_toggle_thesis_endpoint -v`
Expected: FAIL with 404

**Step 3: Rename endpoint and update logic**

```python
# In src/routers/bookmarks.py - rename toggle_paper to toggle_thesis
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
```

**Step 4: Run test to verify it passes**

Run: `cd bookmark-manager && pytest tests/test_bookmarks_api.py::test_toggle_thesis_endpoint -v`
Expected: PASS

**Step 5: Commit**

```bash
cd bookmark-manager && git add src/routers/bookmarks.py tests/test_bookmarks_api.py && git commit -m "feat(api): rename /paper endpoint to /thesis with expiry update"
```

---

### Task 5: Update pin endpoint to clear expiry

**Files:**
- Modify: `bookmark-manager/src/routers/bookmarks.py:267-282`
- Test: `bookmark-manager/tests/test_bookmarks_api.py`

**Step 1: Write failing test for pin clearing expiry**

```python
# In tests/test_bookmarks_api.py
@pytest.mark.asyncio
async def test_pin_clears_expiry(client):
    """Pinning a bookmark should clear its expiry"""
    create_resp = await client.post("/bookmarks", json={"url": "https://example.com/pin-expiry"})
    data = create_resp.json()
    bookmark_id = data["id"]

    # Initially has expiry
    assert data["expires_at"] is not None

    # Pin it
    response = await client.patch(f"/bookmarks/{bookmark_id}/pin", json={"pinned": True})
    assert response.status_code == 200
    assert response.json()["expires_at"] is None
```

**Step 2: Run test to verify it fails**

Run: `cd bookmark-manager && pytest tests/test_bookmarks_api.py::test_pin_clears_expiry -v`
Expected: FAIL - expires_at still set after pinning

**Step 3: Update toggle_pin to recalculate expiry**

```python
# In src/routers/bookmarks.py
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
```

**Step 4: Run test to verify it passes**

Run: `cd bookmark-manager && pytest tests/test_bookmarks_api.py::test_pin_clears_expiry -v`
Expected: PASS

**Step 5: Commit**

```bash
cd bookmark-manager && git add src/routers/bookmarks.py tests/test_bookmarks_api.py && git commit -m "feat(api): pin toggle recalculates expiry"
```

---

### Task 6: Add view filter parameter to list endpoint

**Files:**
- Modify: `bookmark-manager/src/routers/bookmarks.py:80-113`
- Test: `bookmark-manager/tests/test_bookmarks_api.py`

**Step 1: Write failing test for view filter**

```python
# In tests/test_bookmarks_api.py
@pytest.mark.asyncio
async def test_list_bookmarks_by_view(client):
    """Test view filter parameter"""
    # Create test bookmarks
    await client.post("/bookmarks", json={"url": "https://example.com/inbox-item"})

    # Create thesis bookmark
    resp = await client.post("/bookmarks", json={"url": "https://arxiv.org/thesis-item"})

    # Create pinned bookmark
    pin_resp = await client.post("/bookmarks", json={"url": "https://example.com/pinned-item"})
    await client.patch(f"/bookmarks/{pin_resp.json()['id']}/pin", json={"pinned": True})

    # Test inbox view (excludes thesis and pinned)
    inbox_resp = await client.get("/bookmarks?view=inbox")
    inbox_urls = [b["url"] for b in inbox_resp.json()]
    assert "https://example.com/inbox-item" in inbox_urls
    assert "https://arxiv.org/thesis-item" not in inbox_urls
    assert "https://example.com/pinned-item" not in inbox_urls

    # Test thesis view
    thesis_resp = await client.get("/bookmarks?view=thesis")
    thesis_urls = [b["url"] for b in thesis_resp.json()]
    assert "https://arxiv.org/thesis-item" in thesis_urls

    # Test pins view
    pins_resp = await client.get("/bookmarks?view=pins")
    pins_urls = [b["url"] for b in pins_resp.json()]
    assert "https://example.com/pinned-item" in pins_urls
```

**Step 2: Run test to verify it fails**

Run: `cd bookmark-manager && pytest tests/test_bookmarks_api.py::test_list_bookmarks_by_view -v`
Expected: FAIL

**Step 3: Add view filter to list_bookmarks**

```python
# In src/routers/bookmarks.py
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
                    detail="Invalid state. Must be 'inbox' or 'read'"
                )

        if is_thesis is not None:
            query = query.where(Bookmark.is_thesis == is_thesis)

        if pinned is not None:
            query = query.where(Bookmark.pinned == pinned)

    query = query.order_by(Bookmark.added_at.desc()).limit(limit).offset(offset)

    result = await session.execute(query)
    bookmarks = result.scalars().all()

    return bookmarks
```

**Step 4: Run test to verify it passes**

Run: `cd bookmark-manager && pytest tests/test_bookmarks_api.py::test_list_bookmarks_by_view -v`
Expected: PASS

**Step 5: Commit**

```bash
cd bookmark-manager && git add src/routers/bookmarks.py tests/test_bookmarks_api.py && git commit -m "feat(api): add view filter parameter (inbox|thesis|pins)"
```

---

### Task 7: Add export endpoint

**Files:**
- Modify: `bookmark-manager/src/routers/bookmarks.py`
- Modify: `bookmark-manager/src/schemas.py`
- Test: `bookmark-manager/tests/test_bookmarks_api.py`

**Step 1: Write failing test for export endpoint**

```python
# In tests/test_bookmarks_api.py
@pytest.mark.asyncio
async def test_export_bookmark(client):
    """Test export endpoint returns full bookmark data"""
    create_resp = await client.post("/bookmarks", json={"url": "https://example.com/export-test"})
    bookmark_id = create_resp.json()["id"]

    response = await client.get(f"/bookmarks/{bookmark_id}/export")
    assert response.status_code == 200
    data = response.json()

    assert "url" in data
    assert "title" in data
    assert "description" in data
    assert "content" in data
    assert "video_id" in data
```

**Step 2: Run test to verify it fails**

Run: `cd bookmark-manager && pytest tests/test_bookmarks_api.py::test_export_bookmark -v`
Expected: FAIL with 404

**Step 3: Add export schema and endpoint**

```python
# In src/schemas.py - add export schema
class BookmarkExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str
    title: Optional[str]
    description: Optional[str]
    content: Optional[str]
    video_id: Optional[str]
```

```python
# In src/routers/bookmarks.py - add export endpoint
from src.schemas import BookmarkExportResponse

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
```

**Step 4: Run test to verify it passes**

Run: `cd bookmark-manager && pytest tests/test_bookmarks_api.py::test_export_bookmark -v`
Expected: PASS

**Step 5: Commit**

```bash
cd bookmark-manager && git add src/routers/bookmarks.py src/schemas.py tests/test_bookmarks_api.py && git commit -m "feat(api): add /export endpoint for Kasten archiving"
```

---

### Task 8: Add expiring endpoint

**Files:**
- Modify: `bookmark-manager/src/routers/bookmarks.py`
- Test: `bookmark-manager/tests/test_bookmarks_api.py`

**Step 1: Write failing test for expiring endpoint**

```python
# In tests/test_bookmarks_api.py
@pytest.mark.asyncio
async def test_expiring_bookmarks(client):
    """Test endpoint to list bookmarks expiring soon"""
    from datetime import datetime, timedelta

    # Create a bookmark that expires in 12 hours (within 24h window)
    # We need to manually set expires_at via DB
    create_resp = await client.post("/bookmarks", json={"url": "https://example.com/expiring-soon"})
    bookmark_id = create_resp.json()["id"]

    response = await client.get("/bookmarks/expiring")
    assert response.status_code == 200
    # Should return list (may be empty if no bookmarks expiring within 24h)
    assert isinstance(response.json(), list)
```

**Step 2: Run test to verify it fails**

Run: `cd bookmark-manager && pytest tests/test_bookmarks_api.py::test_expiring_bookmarks -v`
Expected: FAIL with 404

**Step 3: Add expiring endpoint**

```python
# In src/routers/bookmarks.py
@router.get("/expiring", response_model=List[BookmarkResponse])
async def get_expiring_bookmarks(
    hours: int = 24,
    session: AsyncSession = Depends(get_db)
):
    """Get bookmarks expiring within the next N hours (default 24)"""
    from datetime import datetime, timedelta

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
```

**Step 4: Run test to verify it passes**

Run: `cd bookmark-manager && pytest tests/test_bookmarks_api.py::test_expiring_bookmarks -v`
Expected: PASS

**Step 5: Commit**

```bash
cd bookmark-manager && git add src/routers/bookmarks.py tests/test_bookmarks_api.py && git commit -m "feat(api): add /expiring endpoint for notification system"
```

---

## Phase 3: Background Jobs & Expiry

### Task 9: Add expiry cron job

**Files:**
- Create: `bookmark-manager/src/services/expiry_service.py`
- Modify: `bookmark-manager/src/main.py`
- Test: `bookmark-manager/tests/test_expiry_service.py`

**Step 1: Write failing test for expiry service**

```python
# Create tests/test_expiry_service.py
import pytest
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_expire_old_bookmarks(session):
    """Test that expired bookmarks are deleted"""
    from src.models import Bookmark, BookmarkState
    from src.services.expiry_service import expire_old_bookmarks

    # Create expired bookmark
    expired = Bookmark(
        url="https://example.com/expired",
        state=BookmarkState.inbox,
        expires_at=datetime.utcnow() - timedelta(hours=1)
    )
    # Create non-expired bookmark
    valid = Bookmark(
        url="https://example.com/valid",
        state=BookmarkState.inbox,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    session.add_all([expired, valid])
    await session.commit()

    # Run expiry
    deleted_count = await expire_old_bookmarks(session)

    assert deleted_count == 1

    # Verify expired is gone
    result = await session.get(Bookmark, expired.id)
    assert result is None

    # Verify valid still exists
    result = await session.get(Bookmark, valid.id)
    assert result is not None
```

**Step 2: Run test to verify it fails**

Run: `cd bookmark-manager && pytest tests/test_expiry_service.py::test_expire_old_bookmarks -v`
Expected: FAIL with import error

**Step 3: Create expiry service**

```python
# Create src/services/expiry_service.py
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, func
from src.models import Bookmark, FeedItem
import logging

logger = logging.getLogger(__name__)


async def expire_old_bookmarks(session: AsyncSession) -> int:
    """Delete bookmarks past their expiry date. Returns count deleted."""
    now = datetime.utcnow()

    # Count before delete
    count_query = select(func.count()).select_from(Bookmark).where(
        Bookmark.expires_at != None,
        Bookmark.expires_at < now
    )
    result = await session.execute(count_query)
    count = result.scalar()

    if count > 0:
        await session.execute(
            delete(Bookmark).where(
                Bookmark.expires_at != None,
                Bookmark.expires_at < now
            )
        )
        await session.commit()
        logger.info(f"Expired {count} bookmarks")

    return count


async def expire_old_feed_items(session: AsyncSession) -> int:
    """Delete feed items older than 7 days. Returns count deleted."""
    cutoff = datetime.utcnow() - timedelta(days=7)

    count_query = select(func.count()).select_from(FeedItem).where(
        FeedItem.published_at < cutoff
    )
    result = await session.execute(count_query)
    count = result.scalar()

    if count > 0:
        await session.execute(
            delete(FeedItem).where(FeedItem.published_at < cutoff)
        )
        await session.commit()
        logger.info(f"Expired {count} feed items")

    return count
```

**Step 4: Run test to verify it passes**

Run: `cd bookmark-manager && pytest tests/test_expiry_service.py::test_expire_old_bookmarks -v`
Expected: PASS

**Step 5: Commit**

```bash
cd bookmark-manager && git add src/services/expiry_service.py tests/test_expiry_service.py && git commit -m "feat(services): add expiry service for bookmark/feed cleanup"
```

---

### Task 10: Update background_jobs.py references from is_paper to is_thesis

**Files:**
- Modify: `bookmark-manager/src/services/background_jobs.py:114-124`

**Step 1: Run existing tests to establish baseline**

Run: `cd bookmark-manager && pytest tests/test_background_jobs.py -v`
Expected: PASS (existing tests should pass)

**Step 2: Update is_paper references to is_thesis**

```python
# In src/services/background_jobs.py line 114-124
# Change:
if not bookmark.is_paper and not bookmark.pinned:
# To:
if not bookmark.is_thesis and not bookmark.pinned:

# And:
logger.info(f"Skipping archive for bookmark {bookmark_id} (paper={bookmark.is_paper}, pinned={bookmark.pinned})")
# To:
logger.info(f"Skipping archive for bookmark {bookmark_id} (thesis={bookmark.is_thesis}, pinned={bookmark.pinned})")
```

**Step 3: Run tests to verify no regression**

Run: `cd bookmark-manager && pytest tests/test_background_jobs.py -v`
Expected: PASS

**Step 4: Commit**

```bash
cd bookmark-manager && git add src/services/background_jobs.py && git commit -m "refactor(services): rename is_paper to is_thesis in background jobs"
```

---

## Phase 4: Telegram Bot

### Task 11: Rename /paper command to /thesis

**Files:**
- Modify: `bookmark-manager/bot/main.py:83-148`
- Test: `bookmark-manager/tests/test_telegram_bot.py`

**Step 1: Write failing test for /thesis command**

```python
# In tests/test_telegram_bot.py - add test
@pytest.mark.asyncio
async def test_thesis_command_handler_exists():
    """Test that /thesis command is registered"""
    from bot.main import Application, CommandHandler
    from telegram.ext import Application

    # Import main to check handlers
    import bot.main as bot_module

    # Check that handle_thesis function exists
    assert hasattr(bot_module, 'handle_thesis')
```

**Step 2: Run test to verify it fails**

Run: `cd bookmark-manager && pytest tests/test_telegram_bot.py::test_thesis_command_handler_exists -v`
Expected: FAIL with AttributeError

**Step 3: Rename handle_paper to handle_thesis**

```python
# In bot/main.py
# Rename function handle_paper to handle_thesis
async def handle_thesis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /thesis command - save or convert to thesis"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /thesis <url>")
        return

    url = context.args[0]
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("Please provide a valid URL")
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/bookmarks",
                json={"url": url},
                timeout=30.0
            )

            if response.status_code == 201:
                data = response.json()
                bookmark_id = data["id"]
            elif response.status_code == 409:
                list_response = await client.get(
                    f"{API_URL}/bookmarks",
                    params={"limit": 1000},
                    timeout=30.0
                )
                bookmarks = list_response.json()
                bookmark_id = None
                for b in bookmarks:
                    if b["url"] == url:
                        bookmark_id = b["id"]
                        break
                if not bookmark_id:
                    await update.message.reply_text("Could not find bookmark")
                    return
            else:
                await update.message.reply_text("Failed to save bookmark")
                return

            # Mark as thesis (changed endpoint)
            thesis_response = await client.patch(
                f"{API_URL}/bookmarks/{bookmark_id}/thesis",
                json={"is_thesis": True},
                timeout=30.0
            )

            if thesis_response.ok:
                data = thesis_response.json()
                title = data.get("title") or "Untitled"
                await update.message.reply_text(f"Thesis saved: {title}")
            else:
                await update.message.reply_text("Failed to mark as thesis")

    except Exception as e:
        logger.error(f"Error in /thesis command: {e}")
        await update.message.reply_text("Failed to process thesis")


# Update main() to register /thesis instead of /paper
def main() -> None:
    # ...
    application.add_handler(CommandHandler("thesis", handle_thesis))
    # Remove: application.add_handler(CommandHandler("paper", handle_paper))
```

**Step 4: Run test to verify it passes**

Run: `cd bookmark-manager && pytest tests/test_telegram_bot.py::test_thesis_command_handler_exists -v`
Expected: PASS

**Step 5: Commit**

```bash
cd bookmark-manager && git add bot/main.py tests/test_telegram_bot.py && git commit -m "feat(bot): rename /paper command to /thesis"
```

---

## Phase 5: UI Changes

### Task 12: Update navigation tabs (remove Archive, add Thesis/Pins)

**Files:**
- Modify: `bookmark-manager/src/templates/base.html:626-631`
- Modify: `bookmark-manager/src/templates/index.html:1-11`
- Test: Manual UI verification

**Step 1: Update base.html bottom navigation**

```html
<!-- In src/templates/base.html - update bottom-nav-links -->
<nav class="bottom-nav">
    <div class="bottom-nav-links">
        <a href="/ui/?view=feeds" class="bottom-nav-link" data-view="feeds">Feeds</a>
        <a href="/ui/?view=inbox" class="bottom-nav-link" data-view="inbox">Inbox</a>
        <a href="/ui/?view=thesis" class="bottom-nav-link" data-view="thesis">Thesis</a>
        <a href="/ui/?view=pins" class="bottom-nav-link" data-view="pins">Pins</a>
    </div>
</nav>
```

**Step 2: Update index.html header tabs**

```html
<!-- In src/templates/index.html - update tabs -->
<header class="header">
    <h1>Bookmarks</h1>
    <nav class="tabs">
        <a href="/ui/?view=feeds" class="tab {% if view == 'feeds' %}active{% endif %}">Feeds</a>
        <a href="/ui/?view=inbox" class="tab {% if view == 'inbox' %}active{% endif %}">Inbox</a>
        <a href="/ui/?view=thesis" class="tab {% if view == 'thesis' %}active{% endif %}">Thesis</a>
        <a href="/ui/?view=pins" class="tab {% if view == 'pins' %}active{% endif %}">Pins</a>
    </nav>
</header>
```

**Step 3: Verify manually**

Run: `cd bookmark-manager && uvicorn src.main:app --reload`
Visit: http://localhost:8000/ui/
Expected: See Feeds | Inbox | Thesis | Pins navigation

**Step 4: Commit**

```bash
cd bookmark-manager && git add src/templates/base.html src/templates/index.html && git commit -m "feat(ui): update navigation to Feeds|Inbox|Thesis|Pins"
```

---

### Task 13: Update UI router with thesis and pins views

**Files:**
- Modify: `bookmark-manager/src/routers/ui.py`
- Test: `bookmark-manager/tests/test_ui.py`

**Step 1: Write failing test for thesis view**

```python
# In tests/test_ui.py
@pytest.mark.asyncio
async def test_thesis_view(client):
    """Test thesis view renders"""
    response = await client.get("/ui/?view=thesis")
    assert response.status_code == 200
    assert b"THESIS" in response.content
```

**Step 2: Run test to verify it fails**

Run: `cd bookmark-manager && pytest tests/test_ui.py::test_thesis_view -v`
Expected: FAIL

**Step 3: Update ui.py with thesis and pins views**

```python
# In src/routers/ui.py - update ui_index function
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

        return templates.TemplateResponse(
            "feeds.html",
            {"request": request, "feeds": feeds_with_items, "view": view}
        )

    # Build query based on view
    query = select(Bookmark)

    if view == "inbox":
        query = query.where(
            Bookmark.state == BookmarkState.inbox,
            Bookmark.is_thesis == False,
            Bookmark.pinned == False
        )
    elif view == "thesis":
        query = query.where(
            Bookmark.state == BookmarkState.inbox,
            Bookmark.is_thesis == True
        )
    elif view == "pins":
        query = query.where(
            Bookmark.state == BookmarkState.inbox,
            Bookmark.pinned == True
        )

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

**Step 4: Run test to verify it passes**

Run: `cd bookmark-manager && pytest tests/test_ui.py::test_thesis_view -v`
Expected: PASS

**Step 5: Commit**

```bash
cd bookmark-manager && git add src/routers/ui.py tests/test_ui.py && git commit -m "feat(ui): add thesis and pins view handlers"
```

---

### Task 14: Add expiry countdown to inbox template

**Files:**
- Modify: `bookmark-manager/src/templates/index.html`

**Step 1: Add Jinja filter for expiry display**

```python
# In src/routers/ui.py - add filter
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
```

**Step 2: Update index.html to show expiry**

```html
<!-- In src/templates/index.html - update current-item section -->
<div class="current-item-title" data-id="{{ current.id }}">
    {% if current.video_id %}&#127909; {% endif %}
    {% if current.pinned %}&#128204; {% endif %}
    {% if current.is_thesis %}&#128196; {% endif %}
    {{ current.title or 'Untitled' }}
    {% if current.expires_at %}
    <span style="color: #666; font-weight: normal; font-size: 0.875rem; float: right;">
        {{ current.expires_at | expiry }}
    </span>
    {% endif %}
</div>
```

**Step 3: Verify manually**

Run: `cd bookmark-manager && uvicorn src.main:app --reload`
Visit: http://localhost:8000/ui/?view=inbox
Expected: See expiry countdown on inbox items

**Step 4: Commit**

```bash
cd bookmark-manager && git add src/routers/ui.py src/templates/index.html && git commit -m "feat(ui): add expiry countdown display"
```

---

### Task 15: Update action bar design with PROCESS button

**Files:**
- Modify: `bookmark-manager/src/templates/index.html`
- Modify: `bookmark-manager/src/templates/base.html`

**Step 1: Update action bar styling in base.html**

```css
/* In src/templates/base.html - add/update action bar styles */
.action-bar {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem 0;
    border-top: 1px solid #000;
    margin-top: 1rem;
}
.action-primary {
    padding: 0.75rem 1.5rem;
    border: 2px solid #000;
    background: #fff;
    font-family: inherit;
    font-size: 0.875rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    cursor: pointer;
}
.action-primary:hover {
    background: #000;
    color: #fff;
}
.action-secondary {
    background: none;
    border: none;
    font-family: inherit;
    font-size: 0.875rem;
    cursor: pointer;
    color: #000;
    text-decoration: none;
}
.action-secondary:hover {
    text-decoration: underline;
}
.action-danger {
    color: #c00;
    margin-left: auto;
}
```

**Step 2: Update action panel in index.html**

```html
<!-- In src/templates/index.html - replace action-panel -->
<aside class="action-panel" id="action-panel">
    <div class="action-bar">
        <button class="action-primary" onclick="processItem({{ current.id }})">PROCESS</button>
        <a href="{{ current.url }}" target="_blank" class="action-secondary">Open</a>
        <button class="action-secondary" onclick="showMoveMenu({{ current.id }})">Move to</button>
        <button class="action-secondary action-danger" onclick="deleteItem({{ current.id }})">Delete</button>
    </div>
</aside>

<!-- Add move menu -->
<div id="move-menu" style="display: none; position: fixed; background: #fff; border: 2px solid #000; padding: 0.5rem 0; z-index: 100;">
    <button onclick="moveToView(currentMoveId, 'inbox')" style="display: block; width: 100%; text-align: left; padding: 0.5rem 1rem; border: none; background: none; cursor: pointer; font-family: inherit;">Inbox</button>
    <button onclick="moveToView(currentMoveId, 'thesis')" style="display: block; width: 100%; text-align: left; padding: 0.5rem 1rem; border: none; background: none; cursor: pointer; font-family: inherit;">Thesis</button>
    <button onclick="moveToView(currentMoveId, 'pins')" style="display: block; width: 100%; text-align: left; padding: 0.5rem 1rem; border: none; background: none; cursor: pointer; font-family: inherit;">Pins</button>
</div>
```

**Step 3: Add JavaScript for process and move**

```javascript
// In index.html scripts section
let currentMoveId = null;

window.processItem = function(id) {
    // Redirect to Canvas with bookmark ID
    window.location.href = `/canvas?bookmark_id=${id}`;
};

window.showMoveMenu = function(id) {
    currentMoveId = id;
    const menu = document.getElementById('move-menu');
    menu.style.display = 'block';
    // Position near cursor or button
    const btn = event.target;
    const rect = btn.getBoundingClientRect();
    menu.style.left = rect.left + 'px';
    menu.style.top = (rect.bottom + 4) + 'px';
};

window.moveToView = async function(id, view) {
    document.getElementById('move-menu').style.display = 'none';
    try {
        if (view === 'thesis') {
            await fetch(`${API_BASE}/${id}/thesis`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_thesis: true })
            });
        } else if (view === 'pins') {
            await fetch(`${API_BASE}/${id}/pin`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pinned: true })
            });
        } else {
            // Move to inbox - unset thesis and pin
            await fetch(`${API_BASE}/${id}/thesis`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_thesis: false })
            });
            await fetch(`${API_BASE}/${id}/pin`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pinned: false })
            });
        }
        window.location.reload();
    } catch (err) {
        console.error('Failed to move:', err);
    }
};

// Close move menu on click outside
document.addEventListener('click', function(e) {
    const menu = document.getElementById('move-menu');
    if (menu && !menu.contains(e.target) && !e.target.matches('[onclick*="showMoveMenu"]')) {
        menu.style.display = 'none';
    }
});
```

**Step 4: Verify manually**

Run: `cd bookmark-manager && uvicorn src.main:app --reload`
Visit: http://localhost:8000/ui/?view=inbox
Expected: See new action bar with PROCESS | Open | Move to | Delete

**Step 5: Commit**

```bash
cd bookmark-manager && git add src/templates/base.html src/templates/index.html && git commit -m "feat(ui): implement new action bar with PROCESS button and Move to picker"
```

---

### Task 16: Create thesis and pins list views

**Files:**
- Modify: `bookmark-manager/src/templates/index.html`

**Step 1: Add thesis view template section**

```html
<!-- In src/templates/index.html - add after inbox section -->
{% elif view == 'thesis' %}
<!-- THESIS: List View -->
<div class="inbox-header">
    <span class="inbox-count">THESIS ({{ bookmarks|length }})</span>
</div>

{% if bookmarks %}
<section class="bookmark-list">
    {% for bookmark in bookmarks %}
    <div class="bookmark-item"
         data-id="{{ bookmark.id }}"
         onclick="selectListItem(this, {{ bookmark.id }})">
        <div class="bookmark-title">&#128196; {{ bookmark.title or 'Untitled' }}</div>
        <div class="bookmark-domain">{{ bookmark.url | domain }} · {{ bookmark.added_at.strftime('%b %d') }}</div>
    </div>
    {% endfor %}
</section>

<!-- Detail panel for selected item -->
<aside class="detail-panel" id="detail-panel" style="display: none;">
    <div id="detail-content"></div>
</aside>
{% else %}
<div class="archive-void">
    <div class="archive-void-message">No thesis bookmarks</div>
</div>
{% endif %}

{% elif view == 'pins' %}
<!-- PINS: List View -->
<div class="inbox-header">
    <span class="inbox-count">PINS ({{ bookmarks|length }})</span>
</div>

{% if bookmarks %}
<section class="bookmark-list">
    {% for bookmark in bookmarks %}
    <div class="bookmark-item"
         data-id="{{ bookmark.id }}"
         onclick="selectListItem(this, {{ bookmark.id }})">
        <div class="bookmark-title">&#128204; {{ bookmark.title or 'Untitled' }}</div>
        <div class="bookmark-domain">{{ bookmark.url | domain }} · {{ bookmark.added_at.strftime('%b %d') }}</div>
    </div>
    {% endfor %}
</section>
{% else %}
<div class="archive-void">
    <div class="archive-void-message">No pinned bookmarks</div>
</div>
{% endif %}

{% endif %}
```

**Step 2: Add JavaScript for list item selection**

```javascript
// Add to scripts section
window.selectListItem = async function(element, id) {
    document.querySelectorAll('.bookmark-item').forEach(el => el.classList.remove('selected'));
    element.classList.add('selected');

    // Fetch bookmark details
    const resp = await fetch(`${API_BASE}/${id}`);
    const data = await resp.json();

    const panel = document.getElementById('detail-panel');
    const content = document.getElementById('detail-content');

    content.innerHTML = `
        <h2 class="detail-title">${data.title || 'Untitled'}</h2>
        <div class="detail-domain">${getDomain(data.url)}</div>
        <p class="detail-description">${data.description || 'No description'}</p>
        <div class="action-bar">
            <button class="action-primary" onclick="processItem(${id})">PROCESS</button>
            <a href="${data.url}" target="_blank" class="action-secondary">Open</a>
            <button class="action-secondary" onclick="showMoveMenu(${id})">Move to</button>
            <button class="action-secondary action-danger" onclick="deleteItem(${id})">Delete</button>
        </div>
    `;
    panel.style.display = 'block';
};
```

**Step 3: Verify manually**

Run: `cd bookmark-manager && uvicorn src.main:app --reload`
Visit: http://localhost:8000/ui/?view=thesis and http://localhost:8000/ui/?view=pins
Expected: See list views with clickable items

**Step 4: Commit**

```bash
cd bookmark-manager && git add src/templates/index.html && git commit -m "feat(ui): implement thesis and pins list views"
```

---

### Task 17: Update paper references to thesis in JavaScript

**Files:**
- Modify: `bookmark-manager/src/templates/index.html`

**Step 1: Find and replace all is_paper/paper references**

```javascript
// In index.html scripts section
// Change markAsPaper to markAsThesis
window.markAsThesis = async function(id) {
    try {
        await fetch(`${API_BASE}/${id}/thesis`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_thesis: true })
        });
        window.location.reload();
    } catch (err) {
        console.error('Failed to mark as thesis:', err);
    }
};
```

**Step 2: Update template references**

```html
<!-- Change is_paper to is_thesis -->
{% if current.is_thesis %}&#128196; {% endif %}

<!-- Update button text -->
<button class="action-btn" onclick="markAsThesis({{ current.id }})">Mark as Thesis</button>
```

**Step 3: Run tests**

Run: `cd bookmark-manager && pytest tests/test_ui.py -v`
Expected: PASS

**Step 4: Commit**

```bash
cd bookmark-manager && git add src/templates/index.html && git commit -m "refactor(ui): rename paper references to thesis"
```

---

## Phase 6: Database Migration

### Task 18: Create Alembic migration

**Files:**
- Create: `bookmark-manager/alembic/versions/xxx_rename_is_paper_add_expires_at.py`

**Step 1: Generate migration**

```bash
cd bookmark-manager && alembic revision --autogenerate -m "rename_is_paper_add_expires_at"
```

**Step 2: Edit migration to handle rename**

```python
# In the generated migration file
def upgrade():
    # Rename column
    op.alter_column('bookmarks', 'is_paper', new_column_name='is_thesis')

    # Add expires_at column
    op.add_column('bookmarks', sa.Column('expires_at', sa.DateTime(), nullable=True))

    # Set initial expiry for existing inbox items (14 days grace period)
    from datetime import datetime, timedelta
    grace_period = datetime.utcnow() + timedelta(days=14)
    op.execute(f"""
        UPDATE bookmarks
        SET expires_at = '{grace_period.isoformat()}'
        WHERE state = 'inbox'
        AND is_thesis = false
        AND pinned = false
    """)


def downgrade():
    op.drop_column('bookmarks', 'expires_at')
    op.alter_column('bookmarks', 'is_thesis', new_column_name='is_paper')
```

**Step 3: Run migration**

Run: `cd bookmark-manager && alembic upgrade head`
Expected: Migration completes successfully

**Step 4: Commit**

```bash
cd bookmark-manager && git add alembic/ && git commit -m "feat(db): add migration for is_thesis rename and expires_at"
```

---

## Phase 7: Integration & Cleanup

### Task 19: Remove archive view and related code

**Files:**
- Modify: `bookmark-manager/src/templates/index.html`
- Modify: `bookmark-manager/src/routers/ui.py`

**Step 1: Remove archive template section**

Remove the `{% elif view == 'archive' %}` section from index.html

**Step 2: Remove archive view handler from ui.py**

Remove the archive-related code from the view handling logic

**Step 3: Run all tests**

Run: `cd bookmark-manager && pytest -v`
Expected: All tests pass

**Step 4: Commit**

```bash
cd bookmark-manager && git add src/templates/index.html src/routers/ui.py && git commit -m "refactor(ui): remove archive view"
```

---

### Task 20: Update all remaining is_paper references

**Files:**
- Multiple files across codebase

**Step 1: Search for remaining is_paper references**

```bash
cd bookmark-manager && grep -r "is_paper" --include="*.py" --include="*.html"
```

**Step 2: Update each occurrence**

Update any remaining references in:
- `src/services/paper_detection.py` - leave as is (detection logic)
- Tests that reference is_paper
- Any other files found

**Step 3: Run full test suite**

Run: `cd bookmark-manager && pytest -v`
Expected: All tests pass

**Step 4: Commit**

```bash
cd bookmark-manager && git add -A && git commit -m "refactor: complete is_paper to is_thesis rename"
```

---

### Task 21: Final integration test

**Step 1: Start the application**

```bash
cd bookmark-manager && uvicorn src.main:app --reload
```

**Step 2: Manual verification checklist**

- [ ] Feeds view shows items from last 7 days
- [ ] Inbox view shows regular bookmarks with expiry countdown
- [ ] Thesis view shows thesis-marked bookmarks
- [ ] Pins view shows pinned bookmarks
- [ ] PROCESS button redirects to Canvas
- [ ] Move to picker works for all destinations
- [ ] Delete works
- [ ] Telegram /thesis command works
- [ ] New bookmarks get 7-day expiry
- [ ] Thesis/pinned bookmarks don't expire

**Step 3: Run full test suite**

```bash
cd bookmark-manager && pytest -v
```

**Step 4: Final commit**

```bash
cd bookmark-manager && git add -A && git commit -m "feat: complete bookmark manager redesign implementation"
```

---

## Summary

| Phase | Tasks | Key Changes |
|-------|-------|-------------|
| 1 | 1-2 | Model & schema updates (is_thesis, expires_at) |
| 2 | 3-8 | API endpoints (expiry, view filter, export, expiring) |
| 3 | 9-10 | Background jobs (expiry cron, rename references) |
| 4 | 11 | Telegram bot (/thesis command) |
| 5 | 12-17 | UI changes (navigation, views, action bar) |
| 6 | 18 | Database migration |
| 7 | 19-21 | Cleanup and integration testing |

---

Plan complete and saved to `docs/plans/2025-12-24-bookmark-manager-redesign.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
