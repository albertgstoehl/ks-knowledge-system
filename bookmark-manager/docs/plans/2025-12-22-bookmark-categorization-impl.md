# Bookmark Categorization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add paper detection, pinboard, and Zotero sync to bookmark manager.

**Architecture:** Two new boolean fields (`is_paper`, `pinned`) on Bookmark model with smart UI filtering. Paper auto-detection by URL domain. Zotero sync on marking paper as read.

**Tech Stack:** FastAPI, SQLAlchemy, python-telegram-bot, Zotero Web API, Jinja2 templates

**Style Guide:** Follow [docs/style.md](../style.md) for all UI components.

---

## Task 1: Database Migration

**Files:**
- Modify: `src/models.py:10-25`

**Step 1: Add new fields to Bookmark model**

```python
# In src/models.py, add to Bookmark class after video_timestamp:
    is_paper = Column(Boolean, default=False, index=True)
    pinned = Column(Boolean, default=False, index=True)
    zotero_key = Column(String, nullable=True)
```

**Step 2: Add Boolean import**

Add `Boolean` to the SQLAlchemy imports at top of file:
```python
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Text, ForeignKey, UniqueConstraint, Boolean
```

**Step 3: Run migration manually**

```bash
# Connect to k3s pod and run migration
kubectl exec -it deploy/bookmark-manager -n knowledge-system -- python -c "
from src.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text('ALTER TABLE bookmarks ADD COLUMN is_paper BOOLEAN DEFAULT 0'))
    conn.execute(text('ALTER TABLE bookmarks ADD COLUMN pinned BOOLEAN DEFAULT 0'))
    conn.execute(text('ALTER TABLE bookmarks ADD COLUMN zotero_key VARCHAR'))
    conn.execute(text('CREATE INDEX ix_bookmarks_is_paper ON bookmarks(is_paper)'))
    conn.execute(text('CREATE INDEX ix_bookmarks_pinned ON bookmarks(pinned)'))
    conn.commit()
print('Migration complete')
"
```

**Step 4: Commit**

```bash
git add src/models.py
git commit -m "feat: add is_paper, pinned, zotero_key fields to Bookmark model"
```

---

## Task 2: Paper Auto-Detection Helper

**Files:**
- Create: `src/services/paper_detection.py`
- Test: `tests/test_paper_detection.py`

**Step 1: Write the test**

```python
# tests/test_paper_detection.py
import pytest
from src.services.paper_detection import is_academic_url, extract_doi

class TestIsAcademicUrl:
    def test_arxiv(self):
        assert is_academic_url("https://arxiv.org/abs/2301.00001") is True

    def test_doi_org(self):
        assert is_academic_url("https://doi.org/10.1000/xyz123") is True

    def test_pubmed(self):
        assert is_academic_url("https://pubmed.ncbi.nlm.nih.gov/12345678/") is True

    def test_ieee(self):
        assert is_academic_url("https://ieeexplore.ieee.org/document/123456") is True

    def test_acm(self):
        assert is_academic_url("https://dl.acm.org/doi/10.1145/123456") is True

    def test_regular_website(self):
        assert is_academic_url("https://github.com/user/repo") is False

    def test_blog(self):
        assert is_academic_url("https://medium.com/some-article") is False

    def test_youtube(self):
        assert is_academic_url("https://youtube.com/watch?v=abc123") is False


class TestExtractDoi:
    def test_doi_org_url(self):
        assert extract_doi("https://doi.org/10.1000/xyz123") == "10.1000/xyz123"

    def test_dx_doi_org_url(self):
        assert extract_doi("https://dx.doi.org/10.1234/test") == "10.1234/test"

    def test_arxiv_url(self):
        # arxiv has DOIs like 10.48550/arXiv.2301.00001
        doi = extract_doi("https://arxiv.org/abs/2301.00001")
        assert doi == "10.48550/arXiv.2301.00001"

    def test_no_doi(self):
        assert extract_doi("https://github.com/user/repo") is None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_paper_detection.py -v
```
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement paper detection**

```python
# src/services/paper_detection.py
"""Paper and academic URL detection utilities."""

import re
from typing import Optional
from urllib.parse import urlparse

ACADEMIC_DOMAINS = [
    # Preprint servers
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
    "ssrn.com",
    "osf.io",
    "zenodo.org",
    "cogprints.org",
    # DOI resolvers
    "doi.org",
    # Databases / indexes
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "europepmc.org",
    "semanticscholar.org",
    "scholar.google.com",
    "core.ac.uk",
    "doaj.org",
    "jstor.org",
    "philpapers.org",
    "repec.org",
    "dblp.dagstuhl.de",
    "inspirehep.net",
    "citeseerx.ist.psu.edu",
    "scienceopen.com",
    # Publishers
    "sciencedirect.com",
    "springer.com",
    "springerlink.com",
    "link.springer.com",
    "nature.com",
    "wiley.com",
    "onlinelibrary.wiley.com",
    "tandfonline.com",
    "sagepub.com",
    "cambridge.org",
    "academic.oup.com",
    "oup.com",
    "plos.org",
    "frontiersin.org",
    "mdpi.com",
    "hindawi.com",
    "bioone.org",
    "ingentaconnect.com",
    "muse.jhu.edu",
    "rsc.org",
    # Tech/CS specific
    "ieee.org",
    "ieeexplore.ieee.org",
    "acm.org",
    "dl.acm.org",
    "portal.acm.org",
    "aclanthology.org",
    # Government/institutional
    "nih.gov",
    "eric.ed.gov",
    "nber.org",
    "osti.gov",
]


def is_academic_url(url: str) -> bool:
    """Check if URL is from an academic domain."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")

        for academic_domain in ACADEMIC_DOMAINS:
            if domain == academic_domain or domain.endswith("." + academic_domain):
                return True
        return False
    except Exception:
        return False


def extract_doi(url: str) -> Optional[str]:
    """Extract DOI from URL if possible."""
    try:
        # Direct DOI URL: doi.org/10.xxx or dx.doi.org/10.xxx
        doi_match = re.search(r'(?:doi\.org|dx\.doi\.org)/(.+?)(?:\?|#|$)', url)
        if doi_match:
            return doi_match.group(1).rstrip('/')

        # ArXiv: convert to DOI format
        arxiv_match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', url)
        if arxiv_match:
            return f"10.48550/arXiv.{arxiv_match.group(1)}"

        return None
    except Exception:
        return None
```

**Step 4: Run tests**

```bash
pytest tests/test_paper_detection.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/paper_detection.py tests/test_paper_detection.py
git commit -m "feat: add paper auto-detection by academic domain"
```

---

## Task 3: Update Schemas

**Files:**
- Modify: `src/schemas.py`

**Step 1: Update BookmarkResponse**

Add to BookmarkResponse class:
```python
    is_paper: bool = False
    pinned: bool = False
    zotero_key: Optional[str] = None
```

**Step 2: Add BookmarkPinUpdate schema**

```python
class BookmarkPinUpdate(BaseModel):
    pinned: bool
```

**Step 3: Add BookmarkPaperUpdate schema**

```python
class BookmarkPaperUpdate(BaseModel):
    is_paper: bool
```

**Step 4: Commit**

```bash
git add src/schemas.py
git commit -m "feat: add is_paper, pinned, zotero_key to schemas"
```

---

## Task 4: Update Bookmarks API

**Files:**
- Modify: `src/routers/bookmarks.py`

**Step 1: Update create_bookmark for auto-detection**

In `create_bookmark()`, after video_id detection, add:
```python
    # Detect academic paper
    from src.services.paper_detection import is_academic_url
    is_paper = is_academic_url(url_str)

    # Create bookmark
    bookmark = Bookmark(
        url=url_str,
        state=BookmarkState.inbox,
        video_id=video_id,
        is_paper=is_paper
    )
```

**Step 2: Update list_bookmarks filter**

Replace the list_bookmarks function with enhanced filtering:
```python
@router.get("", response_model=List[BookmarkResponse])
async def list_bookmarks(
    state: Optional[str] = None,
    is_paper: Optional[bool] = None,
    pinned: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db)
):
    """List bookmarks with optional filters"""
    query = select(Bookmark)

    if state:
        try:
            state_enum = BookmarkState(state)
            query = query.where(Bookmark.state == state_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state. Must be 'inbox' or 'read'"
            )

    if is_paper is not None:
        query = query.where(Bookmark.is_paper == is_paper)

    if pinned is not None:
        query = query.where(Bookmark.pinned == pinned)

    query = query.order_by(Bookmark.added_at.desc()).limit(limit).offset(offset)

    result = await session.execute(query)
    bookmarks = result.scalars().all()

    return bookmarks
```

**Step 3: Add pin toggle endpoint**

```python
@router.patch("/{bookmark_id}/pin", response_model=BookmarkResponse)
async def toggle_pin(
    bookmark_id: int,
    update_data: BookmarkPinUpdate,
    session: AsyncSession = Depends(get_db)
):
    """Toggle bookmark pinned status"""
    from src.schemas import BookmarkPinUpdate

    bookmark = await session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    bookmark.pinned = update_data.pinned
    await session.commit()
    await session.refresh(bookmark)
    return bookmark
```

**Step 4: Add paper toggle endpoint**

```python
@router.patch("/{bookmark_id}/paper", response_model=BookmarkResponse)
async def toggle_paper(
    bookmark_id: int,
    update_data: BookmarkPaperUpdate,
    session: AsyncSession = Depends(get_db)
):
    """Toggle bookmark paper status"""
    from src.schemas import BookmarkPaperUpdate

    bookmark = await session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    bookmark.is_paper = update_data.is_paper
    await session.commit()
    await session.refresh(bookmark)
    return bookmark
```

**Step 5: Add imports at top**

```python
from src.schemas import BookmarkCreate, BookmarkUpdate, BookmarkDescriptionUpdate, BookmarkTitleUpdate, BookmarkTimestampUpdate, BookmarkResponse, BookmarkContentResponse, BookmarkPinUpdate, BookmarkPaperUpdate
```

**Step 6: Commit**

```bash
git add src/routers/bookmarks.py
git commit -m "feat: add paper auto-detection and pin/paper toggle endpoints"
```

---

## Task 5: Telegram Bot Commands

**Files:**
- Modify: `bot/main.py`
- Test: `tests/test_telegram_bot.py`

**Step 1: Add /paper command handler**

```python
async def handle_paper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /paper command - save or convert to paper"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Not authorized.")
        return

    # Extract URL from command args
    if not context.args:
        await update.message.reply_text("Usage: /paper <url>")
        return

    url = context.args[0]
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("Please provide a valid URL")
        return

    try:
        async with httpx.AsyncClient() as client:
            # First try to create new bookmark
            response = await client.post(
                f"{API_URL}/bookmarks",
                json={"url": url},
                timeout=30.0
            )

            if response.status_code == 201:
                data = response.json()
                bookmark_id = data["id"]
            elif response.status_code == 409:
                # Already exists - get its ID
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

            # Mark as paper
            paper_response = await client.patch(
                f"{API_URL}/bookmarks/{bookmark_id}/paper",
                json={"is_paper": True},
                timeout=30.0
            )

            if paper_response.ok:
                data = paper_response.json()
                title = data.get("title") or "Untitled"
                await update.message.reply_text(f"Paper saved: {title}")
            else:
                await update.message.reply_text("Failed to mark as paper")

    except Exception as e:
        logger.error(f"Error in /paper command: {e}")
        await update.message.reply_text("Failed to process paper")
```

**Step 2: Add /pin command handler**

```python
async def handle_pin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pin command - save and pin bookmark"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /pin <url>")
        return

    url = context.args[0]
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("Please provide a valid URL")
        return

    try:
        async with httpx.AsyncClient() as client:
            # First try to create new bookmark
            response = await client.post(
                f"{API_URL}/bookmarks",
                json={"url": url},
                timeout=30.0
            )

            if response.status_code == 201:
                data = response.json()
                bookmark_id = data["id"]
            elif response.status_code == 409:
                # Already exists - get its ID
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

            # Pin it
            pin_response = await client.patch(
                f"{API_URL}/bookmarks/{bookmark_id}/pin",
                json={"pinned": True},
                timeout=30.0
            )

            if pin_response.ok:
                data = pin_response.json()
                title = data.get("title") or "Untitled"
                await update.message.reply_text(f"Pinned: {title}")
            else:
                await update.message.reply_text("Failed to pin")

    except Exception as e:
        logger.error(f"Error in /pin command: {e}")
        await update.message.reply_text("Failed to pin bookmark")
```

**Step 3: Register handlers in main()**

Add before `application.run_polling`:
```python
    application.add_handler(CommandHandler("paper", handle_paper))
    application.add_handler(CommandHandler("pin", handle_pin))
```

**Step 4: Commit**

```bash
git add bot/main.py
git commit -m "feat: add /paper and /pin telegram commands"
```

---

## Task 6: Zotero Service

**Files:**
- Create: `src/services/zotero_service.py`
- Test: `tests/test_zotero_service.py`

**Step 1: Write the test**

```python
# tests/test_zotero_service.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.zotero_service import ZoteroService

@pytest.fixture
def zotero_service():
    return ZoteroService(api_key="test_key", user_id="12345")


class TestZoteroService:
    @pytest.mark.asyncio
    async def test_create_item_with_doi(self, zotero_service):
        with patch.object(zotero_service, '_fetch_metadata_by_doi') as mock_fetch:
            mock_fetch.return_value = {
                "title": "Test Paper",
                "creators": [{"firstName": "John", "lastName": "Doe", "creatorType": "author"}],
                "date": "2024",
            }
            with patch.object(zotero_service, '_create_zotero_item') as mock_create:
                mock_create.return_value = "ABC123"

                result = await zotero_service.sync_paper(
                    url="https://doi.org/10.1000/test",
                    title="Test Paper",
                    doi="10.1000/test"
                )

                assert result["zotero_key"] == "ABC123"
                assert result["needs_manual"] is False

    @pytest.mark.asyncio
    async def test_create_item_without_doi(self, zotero_service):
        with patch.object(zotero_service, '_create_zotero_item') as mock_create:
            mock_create.return_value = "XYZ789"

            result = await zotero_service.sync_paper(
                url="https://example.com/paper",
                title="Unknown Paper",
                doi=None
            )

            assert result["zotero_key"] == "XYZ789"
            assert result["needs_manual"] is True
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_zotero_service.py -v
```
Expected: FAIL

**Step 3: Implement Zotero service**

```python
# src/services/zotero_service.py
"""Zotero Web API integration for paper sync."""

import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

ZOTERO_API_BASE = "https://api.zotero.org"
API_VERSION = "3"


class ZoteroService:
    def __init__(self, api_key: str = None, user_id: str = None):
        import os
        self.api_key = api_key or os.getenv("ZOTERO_API_KEY")
        self.user_id = user_id or os.getenv("ZOTERO_USER_ID")

        if not self.api_key or not self.user_id:
            logger.warning("Zotero API credentials not configured")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Zotero-API-Key": self.api_key,
            "Zotero-API-Version": API_VERSION,
            "Content-Type": "application/json",
        }

    async def _fetch_metadata_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Fetch metadata from CrossRef by DOI."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.crossref.org/works/{doi}",
                    timeout=30.0
                )
                if not response.is_success:
                    return None

                data = response.json()
                work = data.get("message", {})

                creators = []
                for author in work.get("author", []):
                    creators.append({
                        "creatorType": "author",
                        "firstName": author.get("given", ""),
                        "lastName": author.get("family", ""),
                    })

                date_parts = work.get("published", {}).get("date-parts", [[]])
                date = "-".join(str(p) for p in date_parts[0]) if date_parts[0] else None

                return {
                    "itemType": "journalArticle",
                    "title": work.get("title", ["Untitled"])[0],
                    "creators": creators,
                    "date": date,
                    "DOI": doi,
                    "url": work.get("URL"),
                    "abstractNote": work.get("abstract", "").replace("<jats:p>", "").replace("</jats:p>", ""),
                    "publicationTitle": work.get("container-title", [""])[0],
                }
        except Exception as e:
            logger.error(f"Failed to fetch DOI metadata: {e}")
            return None

    async def _create_zotero_item(self, item_data: Dict[str, Any], tags: list) -> Optional[str]:
        """Create item in Zotero library."""
        if not self.api_key or not self.user_id:
            logger.error("Zotero credentials not configured")
            return None

        item_data["tags"] = [{"tag": t} for t in tags]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{ZOTERO_API_BASE}/users/{self.user_id}/items",
                    headers=self._get_headers(),
                    json=[item_data],
                    timeout=30.0
                )

                if not response.is_success:
                    logger.error(f"Zotero API error: {response.status_code} - {response.text}")
                    return None

                result = response.json()
                successful = result.get("successful", {})
                if successful:
                    return list(successful.values())[0].get("key")

                failed = result.get("failed", {})
                if failed:
                    logger.error(f"Zotero creation failed: {failed}")

                return None
        except Exception as e:
            logger.error(f"Failed to create Zotero item: {e}")
            return None

    async def sync_paper(
        self,
        url: str,
        title: str,
        doi: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sync paper to Zotero.

        Returns:
            Dict with zotero_key and needs_manual flag
        """
        tags = ["bookmark-manager"]
        item_data = None
        needs_manual = False

        # Try to get metadata from DOI
        if doi:
            item_data = await self._fetch_metadata_by_doi(doi)

        # Fallback to basic item
        if not item_data:
            needs_manual = True
            tags.append("needs-doi")
            item_data = {
                "itemType": "webpage",
                "title": title,
                "url": url,
            }

        zotero_key = await self._create_zotero_item(item_data, tags)

        return {
            "zotero_key": zotero_key,
            "needs_manual": needs_manual,
        }
```

**Step 4: Run tests**

```bash
pytest tests/test_zotero_service.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/zotero_service.py tests/test_zotero_service.py
git commit -m "feat: add Zotero sync service"
```

---

## Task 7: Integrate Zotero Sync on Mark Read

**Files:**
- Modify: `src/routers/bookmarks.py`

**Step 1: Update update_bookmark to trigger Zotero sync**

Replace the `update_bookmark` function:
```python
@router.patch("/{bookmark_id}", response_model=BookmarkResponse)
async def update_bookmark(
    bookmark_id: int,
    update_data: BookmarkUpdate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    """Update bookmark (mark as read/inbox)"""
    bookmark = await session.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    if update_data.state:
        bookmark.state = BookmarkState(update_data.state)
        if update_data.state == "read":
            from datetime import datetime
            bookmark.read_at = datetime.utcnow()

            # Trigger Zotero sync for papers
            if bookmark.is_paper and not bookmark.zotero_key:
                background_tasks.add_task(
                    sync_paper_to_zotero,
                    bookmark.id,
                    session
                )
        else:
            bookmark.read_at = None

    await session.commit()
    await session.refresh(bookmark)

    return bookmark


async def sync_paper_to_zotero(bookmark_id: int, session: AsyncSession):
    """Background task to sync paper to Zotero."""
    import os
    from src.services.zotero_service import ZoteroService
    from src.services.paper_detection import extract_doi

    bookmark = await session.get(Bookmark, bookmark_id)
    if not bookmark or not bookmark.is_paper:
        return

    zotero = ZoteroService()
    if not zotero.api_key:
        return

    doi = extract_doi(bookmark.url)
    result = await zotero.sync_paper(
        url=bookmark.url,
        title=bookmark.title or "Untitled",
        doi=doi
    )

    if result.get("zotero_key"):
        bookmark.zotero_key = result["zotero_key"]
        await session.commit()
```

**Step 2: Commit**

```bash
git add src/routers/bookmarks.py
git commit -m "feat: trigger Zotero sync when marking paper as read"
```

---

## Task 8: Update Archive Service to Skip Papers/Pins

**Files:**
- Modify: `src/services/background_jobs.py`

**Step 1: Add skip logic**

In `process_new_bookmark`, replace the archive section (around line 114-120):
```python
        # 2. Submit to Web Archive (skip papers and pinned items)
        if not bookmark.is_paper and not bookmark.pinned:
            logger.info(f"Submitting to Web Archive: {bookmark.url}")
            archive_result = await self.archive_service.submit_to_archive(bookmark.url)
            if archive_result and "snapshot_url" in archive_result:
                bookmark.archive_url = archive_result["snapshot_url"]
            elif archive_result and "error_type" in archive_result:
                logger.warning(f"Archive failed for bookmark {bookmark_id}: {archive_result['error_type']}")
        else:
            logger.info(f"Skipping archive for bookmark {bookmark_id} (paper={bookmark.is_paper}, pinned={bookmark.pinned})")
```

**Step 2: Commit**

```bash
git add src/services/background_jobs.py
git commit -m "feat: skip web archive for papers and pinned bookmarks"
```

---

## Task 9: Update UI Router

**Files:**
- Modify: `src/routers/ui.py`

**Step 1: Update ui_index for new views**

Replace the ui_index function:
```python
@router.get("/", response_class=HTMLResponse)
async def ui_index(
    request: Request,
    view: str = "inbox",
    q: str = None,
    session: AsyncSession = Depends(get_db)
):
    """Main UI page"""
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
            {
                "request": request,
                "feeds": feeds_with_items,
                "view": view
            }
        )

    # Build query based on view
    query = select(Bookmark)

    if view == "inbox":
        # Regular inbox: not pinned, not paper
        query = query.where(
            Bookmark.state == BookmarkState.inbox,
            Bookmark.pinned == False,
            Bookmark.is_paper == False
        )
    elif view == "papers":
        # Papers queue
        query = query.where(
            Bookmark.is_paper == True,
            Bookmark.state == BookmarkState.inbox
        )
    elif view == "pinboard":
        # Pinboard: pinned + inbox
        query = query.where(
            Bookmark.pinned == True,
            Bookmark.state == BookmarkState.inbox
        )
    elif view == "archive":
        # Archive: read items (with optional search)
        query = query.where(Bookmark.state == BookmarkState.read)
        if q:
            search_term = f"%{q}%"
            query = query.where(
                (Bookmark.title.ilike(search_term)) |
                (Bookmark.description.ilike(search_term)) |
                (Bookmark.url.ilike(search_term))
            )
    elif view == "archive-pins":
        # Archive pins: pinned + read
        query = query.where(
            Bookmark.pinned == True,
            Bookmark.state == BookmarkState.read
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

**Step 2: Commit**

```bash
git add src/routers/ui.py
git commit -m "feat: add papers, pinboard, archive-pins views"
```

---

## Task 10: Update UI Template - Navigation

**Files:**
- Modify: `src/templates/index.html`

**Step 1: Update navigation tabs**

Replace the nav section (lines 6-10):
```html
    <nav class="tabs">
        <a href="/ui/?view=inbox" class="tab {% if view == 'inbox' %}active{% endif %}">Inbox</a>
        <a href="/ui/?view=papers" class="tab {% if view == 'papers' %}active{% endif %}">Papers</a>
        <a href="/ui/?view=pinboard" class="tab {% if view == 'pinboard' %}active{% endif %}">Pinboard</a>
        <a href="/ui/?view=archive" class="tab {% if view == 'archive' %}active{% endif %}">Archive</a>
        <a href="/ui/?view=feeds" class="tab {% if view == 'feeds' %}active{% endif %}">Feeds</a>
    </nav>
```

**Step 2: Update empty state messages**

Replace the empty state section (lines 40-46):
```html
            <div class="empty-state">
                {% if view == 'inbox' %}
                    No unread bookmarks
                {% elif view == 'papers' %}
                    No papers to read
                {% elif view == 'pinboard' %}
                    No pinned items
                {% elif view == 'archive-pins' %}
                    No archived pins
                {% else %}
                    No bookmarks found
                {% endif %}
            </div>
```

**Step 3: Add pin indicator to bookmark items**

Update the bookmark-item div (around line 27-37):
```html
            <div class="bookmark-item"
                 data-id="{{ bookmark.id }}"
                 data-url="{{ bookmark.url }}"
                 data-title="{{ bookmark.title or 'Untitled' }}"
                 data-description="{{ bookmark.description or '' }}"
                 data-state="{{ bookmark.state }}"
                 data-video-id="{{ bookmark.video_id or '' }}"
                 data-video-timestamp="{{ bookmark.video_timestamp or 0 }}"
                 data-is-paper="{{ bookmark.is_paper | lower }}"
                 data-pinned="{{ bookmark.pinned | lower }}">
                <div class="bookmark-title">
                    {% if bookmark.pinned %}<span class="pin-icon">&#128204;</span>{% endif %}
                    {% if bookmark.is_paper %}<span class="paper-icon">&#128196;</span>{% endif %}
                    {{ bookmark.title or 'Untitled' }}
                </div>
                <div class="bookmark-domain">{{ bookmark.url | domain }}</div>
            </div>
```

**Step 4: Commit**

```bash
git add src/templates/index.html
git commit -m "feat: add papers and pinboard tabs to UI"
```

---

## Task 11: Update UI Template - Detail Panel Actions

**Files:**
- Modify: `src/templates/index.html`

**Step 1: Update renderDetail function**

In the JavaScript section, update the renderDetail function to include pin toggle and paper-specific actions. Find the detail-actions div and update it:

```javascript
    // Render detail panel
    function renderDetail(item) {
        const panel = document.getElementById('detail-panel');
        const data = item.dataset;
        const isRead = data.state === 'read';
        const isPaper = data.isPaper === 'true';
        const isPinned = data.pinned === 'true';
        const videoId = data.videoId;
        const videoTimestamp = parseInt(data.videoTimestamp) || 0;
        const currentView = new URL(window.location).searchParams.get('view') || 'inbox';

        let videoSection = '';
        if (videoId) {
            const embedUrl = `https://www.youtube-nocookie.com/embed/${videoId}?start=${videoTimestamp}&enablejsapi=1&origin=${window.location.origin}`;
            videoSection = `
                <div class="video-container">
                    <iframe
                        id="yt-player"
                        src="${embedUrl}"
                        frameborder="0"
                        allowfullscreen
                        allow="autoplay; fullscreen"
                        class="video-embed">
                    </iframe>
                </div>
                <div class="timestamp-controls">
                    <span id="timestamp-status">Position: ${formatTime(videoTimestamp)}</span>
                    <span id="save-indicator"></span>
                </div>
            `;
            setTimeout(() => initYouTubePlayer(data.id, videoTimestamp), 100);
        }

        // Build action buttons based on context
        let actionButtons = `<a href="${data.url}" target="_blank" class="btn btn-primary">Open</a>`;
        actionButtons += `<button class="btn" onclick="editTitle(${data.id}, '${data.title.replace(/'/g, "\\'")}')">Edit</button>`;
        actionButtons += `<button class="btn" onclick="openCiteModal(${data.id})">Cite</button>`;

        // Pin toggle (only in inbox views, not for papers in papers view)
        if (currentView !== 'papers') {
            actionButtons += `<button class="btn" onclick="togglePin(${data.id}, ${!isPinned})">${isPinned ? 'Unpin' : 'Pin'}</button>`;
        }

        // Paper toggle (only in regular inbox)
        if (currentView === 'inbox' && !isPaper) {
            actionButtons += `<button class="btn" onclick="togglePaper(${data.id}, true)">Mark as Paper</button>`;
        }

        // State toggle
        if (currentView === 'pinboard') {
            actionButtons += `<button class="btn" onclick="toggleState(${data.id}, 'read')">Tried it</button>`;
        } else if (currentView === 'archive-pins') {
            actionButtons += `<button class="btn" onclick="togglePin(${data.id}, false)">Unpin</button>`;
        } else {
            actionButtons += `<button class="btn" onclick="toggleState(${data.id}, '${isRead ? 'inbox' : 'read'}')">${isRead ? 'Move to Inbox' : 'Mark Read'}</button>`;
        }

        actionButtons += `<button class="btn btn-danger" onclick="deleteBookmark(${data.id})">Delete</button>`;

        panel.innerHTML = `
            <button class="btn back-btn" onclick="closeDetail()">← Back</button>
            <h2 class="detail-title">${isPinned ? '&#128204; ' : ''}${isPaper ? '&#128196; ' : ''}${data.title}</h2>
            <div class="detail-domain">${getDomain(data.url)}</div>
            ${videoSection}
            <p class="detail-description">${data.description || 'No description'}</p>
            <div class="detail-actions">${actionButtons}</div>
        `;
        panel.classList.add('active');
    }
```

**Step 2: Add togglePin function**

Add after the toggleState function:
```javascript
    // Toggle pinned status
    window.togglePin = async function(id, pinned) {
        try {
            const res = await fetch(`${API_BASE}/${id}/pin`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pinned: pinned })
            });
            if (res.ok) {
                // Refresh the page to update the list
                window.location.reload();
            }
        } catch (err) {
            console.error('Failed to toggle pin:', err);
        }
    };

    // Toggle paper status
    window.togglePaper = async function(id, isPaper) {
        try {
            const res = await fetch(`${API_BASE}/${id}/paper`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_paper: isPaper })
            });
            if (res.ok) {
                window.location.reload();
            }
        } catch (err) {
            console.error('Failed to toggle paper:', err);
        }
    };
```

**Step 3: Commit**

```bash
git add src/templates/index.html
git commit -m "feat: add pin/paper toggle buttons to detail panel"
```

---

## Task 12: Add CSS for Icons

**Files:**
- Modify: `src/templates/base.html`

**Step 1: Add icon styles**

Add to the style section:
```css
.pin-icon, .paper-icon {
    margin-right: 0.25rem;
}
```

**Step 2: Commit**

```bash
git add src/templates/base.html
git commit -m "style: add spacing for pin and paper icons"
```

---

## Task 13: Add Archive Pins Link

**Files:**
- Modify: `src/templates/index.html`

**Step 1: Add archive-pins toggle in archive view**

After the search box in archive view, add:
```html
{% if view == 'archive' %}
<div class="search-box">
    <input type="text"
           id="search-input"
           placeholder="Search bookmarks..."
           value="{{ query or '' }}"
           autocomplete="off">
    <a href="/ui/?view=archive-pins" class="btn" style="margin-left: 0.5rem;">Show Pins</a>
</div>
{% elif view == 'archive-pins' %}
<div class="search-box">
    <a href="/ui/?view=archive" class="btn">← Back to Archive</a>
</div>
{% endif %}
```

**Step 2: Commit**

```bash
git add src/templates/index.html
git commit -m "feat: add archive-pins view toggle"
```

---

## Task 14: Deploy and Test

**Step 1: Build and deploy**

```bash
cd /home/ags/knowledge-system/bookmark-manager
docker build -t bookmark-manager:latest .
docker save bookmark-manager:latest | sudo k3s ctr images import -
kubectl rollout restart deploy/bookmark-manager -n knowledge-system
```

**Step 2: Run database migration**

```bash
kubectl exec -it deploy/bookmark-manager -n knowledge-system -- python -c "
from src.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text('ALTER TABLE bookmarks ADD COLUMN is_paper BOOLEAN DEFAULT 0'))
    conn.execute(text('ALTER TABLE bookmarks ADD COLUMN pinned BOOLEAN DEFAULT 0'))
    conn.execute(text('ALTER TABLE bookmarks ADD COLUMN zotero_key VARCHAR'))
    conn.execute(text('CREATE INDEX ix_bookmarks_is_paper ON bookmarks(is_paper)'))
    conn.execute(text('CREATE INDEX ix_bookmarks_pinned ON bookmarks(pinned)'))
    conn.commit()
print('Migration complete')
"
```

**Step 3: Verify**

```bash
kubectl logs -f deploy/bookmark-manager -n knowledge-system
```

**Step 4: Test in browser**

- Navigate to bookmark.gstoehl.dev
- Verify tabs: Inbox, Papers, Pinboard, Archive, Feeds
- Test pin functionality
- Test paper auto-detection with arxiv URL
- Test Telegram /paper and /pin commands

**Step 5: Final commit**

```bash
git add .
git commit -m "feat: complete bookmark categorization implementation"
```
