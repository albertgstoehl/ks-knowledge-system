# YouTube Gatekeeper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add YouTube as a time-boxed session type in Balance with NextDNS enforcement and server-side break enforcement for all session types.

**Architecture:** YouTube sessions integrate into existing Balance session flow. NextDNS API toggles youtube.com blocking. APScheduler enforces session expiry (all types) and evening cutoff server-side, ensuring breaks are set even if browser is closed.

**Tech Stack:** Python/FastAPI, APScheduler, NextDNS API, SQLite, vanilla JS

**Design doc:** `docs/plans/2026-01-01-youtube-gatekeeper-design.md`

**Prerequisites:** Next Up feature complete (`docs/plans/2026-01-03-next-up-implementation-plan.md`)

---

## Task 1: NextDNS Service

**Files:**
- Create: `balance/src/services/__init__.py`
- Create: `balance/src/services/nextdns.py`
- Create: `balance/tests/test_nextdns.py`

**Step 1: Create services directory**

```bash
mkdir -p balance/src/services
touch balance/src/services/__init__.py
```

**Step 2: Write failing test for NextDNS service**

```python
# balance/tests/test_nextdns.py
import pytest
from unittest.mock import AsyncMock, patch
from src.services.nextdns import NextDNSService, NextDNSError


@pytest.fixture
def nextdns_service():
    return NextDNSService(
        api_key="test-api-key",
        profile_id="test-profile"
    )


@pytest.mark.asyncio
async def test_unblock_youtube_success(nextdns_service):
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_request.return_value = AsyncMock(status_code=204)

        result = await nextdns_service.unblock_youtube()

        assert result is True
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_block_youtube_success(nextdns_service):
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_request.return_value = AsyncMock(status_code=204)

        result = await nextdns_service.block_youtube()

        assert result is True


@pytest.mark.asyncio
async def test_unblock_youtube_api_failure(nextdns_service):
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_request.return_value = AsyncMock(status_code=500)

        with pytest.raises(NextDNSError):
            await nextdns_service.unblock_youtube()
```

**Step 3: Run test to verify it fails**

```bash
cd balance && python -m pytest tests/test_nextdns.py -v
```

Expected: FAIL with "No module named 'src.services.nextdns'"

**Step 4: Implement NextDNS service**

```python
# balance/src/services/nextdns.py
import httpx
import os
from typing import Optional


class NextDNSError(Exception):
    """Raised when NextDNS API call fails."""
    pass


class NextDNSService:
    BASE_URL = "https://api.nextdns.io"
    YOUTUBE_DOMAIN = "youtube.com"

    def __init__(self, api_key: str = None, profile_id: str = None):
        self.api_key = api_key or os.getenv("NEXTDNS_API_KEY")
        self.profile_id = profile_id or os.getenv("NEXTDNS_PROFILE_ID")

        if not self.api_key or not self.profile_id:
            raise ValueError("NEXTDNS_API_KEY and NEXTDNS_PROFILE_ID required")

    async def unblock_youtube(self) -> bool:
        """Remove youtube.com from denylist."""
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method="DELETE",
                url=f"{self.BASE_URL}/profiles/{self.profile_id}/denylist/{self.YOUTUBE_DOMAIN}",
                headers={"X-Api-Key": self.api_key},
                timeout=10.0
            )

            if response.status_code not in (200, 204, 404):
                raise NextDNSError(f"Failed to unblock: {response.status_code}")

            return True

    async def block_youtube(self) -> bool:
        """Add youtube.com to denylist."""
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method="PUT",
                url=f"{self.BASE_URL}/profiles/{self.profile_id}/denylist/{self.YOUTUBE_DOMAIN}",
                headers={"X-Api-Key": self.api_key},
                json={"id": self.YOUTUBE_DOMAIN, "active": True},
                timeout=10.0
            )

            if response.status_code not in (200, 204):
                raise NextDNSError(f"Failed to block: {response.status_code}")

            return True


# Singleton instance (initialized on first use)
_service: Optional[NextDNSService] = None


def get_nextdns_service() -> NextDNSService:
    global _service
    if _service is None:
        _service = NextDNSService()
    return _service
```

**Step 5: Run tests to verify they pass**

```bash
cd balance && python -m pytest tests/test_nextdns.py -v
```

Expected: PASS (3 tests)

**Step 6: Add httpx to requirements**

```bash
echo "httpx>=0.25.0" >> balance/requirements.txt
```

**Step 7: Commit**

```bash
git add balance/src/services/ balance/tests/test_nextdns.py balance/requirements.txt
git commit -m "feat(balance): add NextDNS service for YouTube blocking"
```

---

## Task 2: Database Migration for YouTube Session Type

**Files:**
- Modify: `balance/src/database.py`
- Modify: `balance/tests/test_database.py`

**Context:** After next-up implementation, sessions table already has `next_up_id`. We need to:
1. Add `youtube` to session type CHECK constraint
2. Add `duration_minutes` column for variable-length YouTube sessions

**Step 1: Write failing test for youtube session type**

Add to `balance/tests/test_database.py`:

```python
@pytest.mark.asyncio
async def test_youtube_session_type_allowed(temp_db):
    """YouTube should be a valid session type."""
    async with get_db(temp_db) as db:
        await db.execute(
            "INSERT INTO sessions (type, intention, duration_minutes) VALUES (?, ?, ?)",
            ("youtube", "exploring music production", 30)
        )
        await db.commit()

        cursor = await db.execute("SELECT type, duration_minutes FROM sessions WHERE type = 'youtube'")
        row = await cursor.fetchone()
        assert row["type"] == "youtube"
        assert row["duration_minutes"] == 30
```

**Step 2: Run test to verify it fails**

```bash
cd balance && DATABASE_URL=./data/test.db python -m pytest tests/test_database.py::test_youtube_session_type_allowed -v
```

Expected: FAIL with CHECK constraint violation

**Step 3: Update database schema**

In `balance/src/database.py`, update the sessions table CHECK constraint in the CREATE TABLE statement:

```python
# Change this line:
type TEXT NOT NULL CHECK (type IN ('expected', 'personal')),

# To:
type TEXT NOT NULL CHECK (type IN ('expected', 'personal', 'youtube')),
```

**Step 4: Add migration for existing databases**

Add after the existing migrations in `init_db()` (after the `next_up_id` migration):

```python
        # Migration: add duration_minutes column for youtube sessions
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN duration_minutes INTEGER")
        except Exception:
            pass  # Column already exists

        # Migration: allow youtube session type (recreate table with new CHECK)
        # Check if youtube is already allowed
        try:
            await db.execute("INSERT INTO sessions (type, intention) VALUES ('youtube', 'test')")
            await db.execute("DELETE FROM sessions WHERE intention = 'test' AND type = 'youtube'")
            await db.commit()
        except Exception:
            # Need to migrate - youtube not allowed yet
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL CHECK (type IN ('expected', 'personal', 'youtube')),
                    intention TEXT,
                    priority_id INTEGER,
                    next_up_id INTEGER,
                    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    distractions TEXT CHECK (distractions IN ('none', 'some', 'many')),
                    did_the_thing BOOLEAN,
                    rabbit_hole BOOLEAN,
                    claude_used BOOLEAN DEFAULT FALSE,
                    duration_minutes INTEGER,
                    FOREIGN KEY (priority_id) REFERENCES priorities(id),
                    FOREIGN KEY (next_up_id) REFERENCES next_up(id)
                )
            """)
            await db.execute("""
                INSERT INTO sessions_new
                SELECT id, type, intention, priority_id, next_up_id, started_at, ended_at,
                       distractions, did_the_thing, rabbit_hole, claude_used, duration_minutes
                FROM sessions
            """)
            await db.execute("DROP TABLE sessions")
            await db.execute("ALTER TABLE sessions_new RENAME TO sessions")
            await db.commit()
```

**Step 5: Run test to verify it passes**

```bash
cd balance && DATABASE_URL=./data/test.db python -m pytest tests/test_database.py::test_youtube_session_type_allowed -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add balance/src/database.py balance/tests/test_database.py
git commit -m "feat(balance): add youtube session type and duration_minutes to schema"
```

---

## Task 3: Update Models

**Files:**
- Modify: `balance/src/models.py`

**Context:** After next-up implementation, SessionStart already has `next_up_id`. We add `youtube` type and `duration_minutes`.

**Step 1: Update SessionStart model**

In `balance/src/models.py`, find SessionStart and update:

```python
# Change:
class SessionStart(BaseModel):
    type: Literal["expected", "personal"]
    intention: Optional[str] = None
    priority_id: Optional[int] = None
    next_up_id: Optional[int] = None

# To:
class SessionStart(BaseModel):
    type: Literal["expected", "personal", "youtube"]
    intention: Optional[str] = None
    priority_id: Optional[int] = None
    next_up_id: Optional[int] = None
    duration_minutes: Optional[int] = None  # Only for youtube sessions
```

**Step 2: Update SessionEnd model**

```python
# Change:
class SessionEnd(BaseModel):
    distractions: Literal["none", "some", "many"]
    did_the_thing: bool
    rabbit_hole: Optional[bool] = None

# To:
class SessionEnd(BaseModel):
    distractions: Optional[Literal["none", "some", "many"]] = None  # Not for youtube
    did_the_thing: Optional[bool] = None  # Not for youtube
    rabbit_hole: Optional[bool] = None
    saved_something: Optional[bool] = None  # Only for youtube
```

**Step 3: Update QuickStartRequest model**

```python
# Change:
class QuickStartRequest(BaseModel):
    type: Literal["expected", "personal"]
    intention: str

# To:
class QuickStartRequest(BaseModel):
    type: Literal["expected", "personal", "youtube"]
    intention: str
    duration_minutes: Optional[int] = None  # Only for youtube
```

**Step 4: Commit**

```bash
git add balance/src/models.py
git commit -m "feat(balance): update models for youtube session type"
```

---

## Task 4: Update Sessions Router

**Files:**
- Modify: `balance/src/routers/sessions.py`
- Modify: `balance/tests/test_sessions.py`

**Context:** After next-up implementation, the INSERT includes `next_up_id`. We add YouTube validation and NextDNS integration.

**Step 1: Write failing test for youtube session start**

Add to `balance/tests/test_sessions.py`:

```python
@pytest.mark.asyncio
async def test_start_youtube_session(client):
    """YouTube sessions require duration_minutes."""
    response = await client.post("/api/sessions/start", json={
        "type": "youtube",
        "intention": "exploring music production",
        "duration_minutes": 30
    })
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "youtube"
    assert data["duration"] == 30 * 60  # seconds


@pytest.mark.asyncio
async def test_start_youtube_session_without_duration_fails(client):
    """YouTube sessions must have duration."""
    response = await client.post("/api/sessions/start", json={
        "type": "youtube",
        "intention": "exploring"
    })
    assert response.status_code == 400
```

**Step 2: Run tests to verify they fail**

```bash
cd balance && DATABASE_URL=./data/test.db python -m pytest tests/test_sessions.py -k youtube -v
```

Expected: FAIL

**Step 3: Update session start endpoint**

In `balance/src/routers/sessions.py`, find the `start_session` function and update. Add YouTube validation after the `can_start` check, and update the INSERT to include `duration_minutes`:

```python
@router.post("/sessions/start")
async def start_session(req: SessionStart):
    """Start a new session."""
    # Check if can start
    can_start = await check_can_start()
    if not can_start.allowed:
        raise HTTPException(400, can_start.reason)

    # Validate youtube-specific requirements
    if req.type == "youtube":
        if not req.duration_minutes:
            raise HTTPException(400, "YouTube sessions require duration_minutes")
        if req.duration_minutes not in (15, 30, 45, 60):
            raise HTTPException(400, "Duration must be 15, 30, 45, or 60 minutes")

    settings = await get_settings()

    # Determine session duration
    if req.type == "youtube":
        duration = req.duration_minutes * 60  # to seconds
    else:
        duration = settings["session_duration"] * 60

    end_timestamp = datetime.now().timestamp() + duration

    # For youtube: unblock via NextDNS
    if req.type == "youtube":
        try:
            from ..services.nextdns import get_nextdns_service
            nextdns = get_nextdns_service()
            await nextdns.unblock_youtube()
        except Exception as e:
            raise HTTPException(500, f"Failed to unlock YouTube: {str(e)}")

    # Create session in database
    async with get_db() as db:
        cursor = await db.execute(
            """INSERT INTO sessions (type, intention, priority_id, next_up_id, duration_minutes, started_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (req.type, req.intention, req.priority_id, req.next_up_id, req.duration_minutes, datetime.now().isoformat())
        )
        session_id = cursor.lastrowid
        await db.commit()

    return {
        "id": session_id,
        "type": req.type,
        "intention": req.intention,
        "end_timestamp": end_timestamp,
        "duration": duration,
        "server_timestamp": datetime.now().timestamp()
    }
```

**Step 4: Run tests to verify they pass**

```bash
cd balance && DATABASE_URL=./data/test.db python -m pytest tests/test_sessions.py -k youtube -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add balance/src/routers/sessions.py balance/tests/test_sessions.py
git commit -m "feat(balance): implement youtube session start with NextDNS unlock"
```

---

## Task 5: APScheduler Setup (All Session Types)

**Files:**
- Create: `balance/src/scheduler.py`
- Modify: `balance/src/main.py`
- Create: `balance/tests/test_scheduler.py`

**Key change:** The scheduler enforces session expiry for ALL session types (not just YouTube), ensuring breaks are set even if browser is closed mid-session.

**Step 1: Add APScheduler to requirements**

```bash
echo "apscheduler>=3.10.0" >> balance/requirements.txt
```

**Step 2: Write failing tests for scheduler**

```python
# balance/tests/test_scheduler.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import os

assert "DATABASE_URL" in os.environ, "Run tests with DATABASE_URL=./data/test.db"

from src.database import init_db, get_db
from src.scheduler import check_expired_sessions


@pytest.fixture(autouse=True)
async def setup_test():
    """Initialize database and cleanup between tests."""
    await init_db()
    async with get_db() as db:
        await db.execute("DELETE FROM sessions")
        await db.commit()
    yield


@pytest.mark.asyncio
async def test_expired_youtube_session_triggers_block():
    """Expired YouTube sessions should trigger NextDNS block and set break."""
    async with get_db() as db:
        past_time = datetime.now() - timedelta(minutes=5)
        await db.execute(
            """INSERT INTO sessions (type, intention, started_at, duration_minutes)
               VALUES (?, ?, ?, ?)""",
            ("youtube", "test", past_time.isoformat(), 1)
        )
        await db.commit()

    with patch("src.scheduler.get_nextdns_service") as mock_nextdns:
        mock_service = AsyncMock()
        mock_nextdns.return_value = mock_service

        await check_expired_sessions()

        mock_service.block_youtube.assert_called_once()

    # Verify break was set
    async with get_db() as db:
        cursor = await db.execute("SELECT break_until FROM app_state WHERE id = 1")
        row = await cursor.fetchone()
        assert row["break_until"] is not None


@pytest.mark.asyncio
async def test_expired_focus_session_sets_break():
    """Expired focus sessions should set break even without client callback."""
    async with get_db() as db:
        # Create expired expected session (25 min default, started 30 min ago)
        past_time = datetime.now() - timedelta(minutes=30)
        await db.execute(
            """INSERT INTO sessions (type, intention, started_at)
               VALUES (?, ?, ?)""",
            ("expected", "coding task", past_time.isoformat())
        )
        # Clear any existing break
        await db.execute("UPDATE app_state SET break_until = NULL WHERE id = 1")
        await db.commit()

    await check_expired_sessions()

    # Verify session was ended and break was set
    async with get_db() as db:
        cursor = await db.execute("SELECT ended_at FROM sessions WHERE type = 'expected'")
        row = await cursor.fetchone()
        assert row["ended_at"] is not None

        cursor = await db.execute("SELECT break_until FROM app_state WHERE id = 1")
        row = await cursor.fetchone()
        assert row["break_until"] is not None
```

**Step 3: Run test to verify it fails**

```bash
cd balance && DATABASE_URL=./data/test.db python -m pytest tests/test_scheduler.py -v
```

Expected: FAIL with "No module named 'src.scheduler'"

**Step 4: Implement scheduler**

```python
# balance/src/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import logging

from .database import get_db

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def get_settings(db):
    """Get current settings."""
    cursor = await db.execute("SELECT * FROM settings WHERE id = 1")
    row = await cursor.fetchone()
    return dict(row)


async def check_expired_sessions(db_url: str = None):
    """Check for ALL expired sessions, end them, and set breaks.

    This ensures breaks are enforced even if the browser is closed mid-session.
    For YouTube sessions, also blocks YouTube via NextDNS.
    """
    try:
        async with get_db(db_url) as db:
            settings = await get_settings(db)
            default_duration = settings["session_duration"]  # minutes
            short_break = settings["short_break"]

            # Find all active sessions (no ended_at)
            cursor = await db.execute("""
                SELECT id, type, started_at, duration_minutes
                FROM sessions
                WHERE ended_at IS NULL
            """)
            sessions = await cursor.fetchall()

            now = datetime.now()
            for session in sessions:
                started = datetime.fromisoformat(session["started_at"])

                # YouTube uses custom duration, others use default
                if session["duration_minutes"]:
                    duration_mins = session["duration_minutes"]
                else:
                    duration_mins = default_duration

                end_time = started + timedelta(minutes=duration_mins)

                if now >= end_time:
                    logger.info(f"Session {session['id']} ({session['type']}) expired, enforcing end")

                    # For YouTube: block via NextDNS
                    if session["type"] == "youtube":
                        try:
                            from .services.nextdns import get_nextdns_service, NextDNSError
                            nextdns = get_nextdns_service()
                            await nextdns.block_youtube()
                            logger.info(f"Blocked YouTube for expired session {session['id']}")
                        except NextDNSError as e:
                            logger.error(f"Failed to block YouTube: {e}")
                        except Exception as e:
                            logger.error(f"NextDNS not configured: {e}")

                    # Mark session as ended
                    await db.execute(
                        "UPDATE sessions SET ended_at = ? WHERE id = ?",
                        (now.isoformat(), session["id"])
                    )

                    # Set break
                    break_until = now + timedelta(minutes=short_break)
                    await db.execute(
                        "UPDATE app_state SET break_until = ? WHERE id = 1",
                        (break_until.isoformat(),)
                    )
                    logger.info(f"Break set until {break_until.isoformat()}")

                    await db.commit()
    except Exception as e:
        logger.error(f"Error checking expired sessions: {e}")


async def check_evening_cutoff(db_url: str = None):
    """Check if evening cutoff has passed and set evening mode."""
    try:
        async with get_db(db_url) as db:
            cursor = await db.execute("SELECT evening_cutoff FROM settings WHERE id = 1")
            row = await cursor.fetchone()
            if not row:
                return

            cutoff_str = row["evening_cutoff"]
            cutoff_hour, cutoff_min = map(int, cutoff_str.split(":"))

            now = datetime.now()
            cutoff_time = now.replace(hour=cutoff_hour, minute=cutoff_min, second=0, microsecond=0)

            if now >= cutoff_time:
                # Check if already in evening mode today
                cursor = await db.execute("SELECT check_in_mode FROM app_state WHERE id = 1")
                state = await cursor.fetchone()
                if not state["check_in_mode"]:
                    await db.execute(
                        "UPDATE app_state SET check_in_mode = TRUE WHERE id = 1"
                    )
                    await db.commit()
                    logger.info("Evening cutoff reached, enabled check-in mode")
    except Exception as e:
        logger.error(f"Error checking evening cutoff: {e}")


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(
        check_expired_sessions,
        IntervalTrigger(seconds=30),
        id="session_expiry_check",
        replace_existing=True
    )
    scheduler.add_job(
        check_evening_cutoff,
        IntervalTrigger(minutes=1),
        id="evening_cutoff_check",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started with session expiry (30s) and evening cutoff (1m) checks")


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")
```

**Step 5: Integrate scheduler into main.py**

Add imports at top of `balance/src/main.py`:

```python
from .scheduler import start_scheduler, stop_scheduler, check_expired_sessions
```

Add startup/shutdown handlers (or update existing ones):

```python
@app.on_event("startup")
async def startup():
    await init_db()
    # Check for any expired sessions on startup (catches sessions from pod restarts)
    await check_expired_sessions()
    start_scheduler()


@app.on_event("shutdown")
async def shutdown():
    stop_scheduler()
```

**Step 6: Run tests to verify they pass**

```bash
cd balance && DATABASE_URL=./data/test.db python -m pytest tests/test_scheduler.py -v
```

Expected: PASS

**Step 7: Commit**

```bash
git add balance/src/scheduler.py balance/src/main.py balance/tests/test_scheduler.py balance/requirements.txt
git commit -m "feat(balance): add APScheduler for session expiry and evening cutoff enforcement"
```

---

## Task 6: Frontend - Type Selection Update

**Files:**
- Modify: `balance/src/templates/_content_index.html`
- Modify: `balance/src/static/js/timer.js`

**Step 1: Add YouTube button to type selection**

In `balance/src/templates/_content_index.html`, update the type selection buttons:

```html
<div class="button-group type-selection">
  <button class="btn btn--option active" data-type="expected">Expected</button>
  <button class="btn btn--option" data-type="personal">Personal</button>
  <button class="btn btn--option" data-type="youtube">YouTube</button>
</div>
```

**Step 2: Add duration picker section (hidden by default)**

Add after the intention-group div:

```html
<div id="duration-section" class="duration-section" style="display: none;">
  <label class="label">Duration</label>
  <div class="button-group duration-options">
    <button class="btn btn--option" data-duration="15">15m</button>
    <button class="btn btn--option active" data-duration="30">30m</button>
    <button class="btn btn--option" data-duration="45">45m</button>
    <button class="btn btn--option" data-duration="60">60m</button>
  </div>
</div>
```

**Step 3: Commit template changes**

```bash
git add balance/src/templates/_content_index.html
git commit -m "feat(balance): add YouTube type and duration picker to UI"
```

---

## Task 7: Frontend - JavaScript Updates

**Files:**
- Modify: `balance/src/static/js/timer.js`

**Step 1: Update type selection handler**

Find the type selection click handler and update:

```javascript
// Handle type selection (expected/personal/youtube)
document.querySelectorAll('.type-selection .btn--option').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.type-selection .btn--option').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const type = btn.dataset.type;
    const prioritySection = document.getElementById('priority-section');
    const durationSection = document.getElementById('duration-section');
    const intentionLabel = document.querySelector('.intention-group .label');

    if (type === 'expected') {
      prioritySection.style.display = 'block';
      durationSection.style.display = 'none';
      intentionLabel.textContent = "What's the one thing?";
    } else if (type === 'youtube') {
      prioritySection.style.display = 'none';
      durationSection.style.display = 'block';
      intentionLabel.textContent = "What are you looking for?";
    } else {
      prioritySection.style.display = 'none';
      durationSection.style.display = 'none';
      intentionLabel.textContent = "What's the one thing?";
    }
  });
});
```

**Step 2: Add duration selection handler**

```javascript
// Handle duration selection (youtube only)
let selectedDuration = 30; // default
document.querySelectorAll('.duration-options .btn--option').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.duration-options .btn--option').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedDuration = parseInt(btn.dataset.duration);
  });
});
```

**Step 3: Update startSession function**

Modify the startSession function to include duration for YouTube:

```javascript
async startSession() {
  const type = document.querySelector('.type-selection .btn--option.active').dataset.type;
  const intention = document.getElementById('intention-input').value;

  const body = { type, intention };

  if (type === 'expected') {
    const priorityId = this.selectedPriorityId;
    if (priorityId) body.priority_id = priorityId;
  } else if (type === 'youtube') {
    body.duration_minutes = selectedDuration;
  }

  const response = await fetch('/api/sessions/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const error = await response.json();
    alert(error.detail || 'Failed to start session');
    return;
  }

  const data = await response.json();
  this.showActivePage(data);
}
```

**Step 4: Update active session badge**

The badge should show "YouTube" for youtube sessions:

```javascript
showActivePage(session) {
  document.getElementById('active-type').textContent =
    session.type.charAt(0).toUpperCase() + session.type.slice(1);
  // ... rest of function
}
```

**Step 5: Commit JavaScript changes**

```bash
git add balance/src/static/js/timer.js
git commit -m "feat(balance): add YouTube session handling to frontend"
```

---

## Task 8: Session End Flow for YouTube

**Files:**
- Modify: `balance/src/templates/_content_index.html`
- Modify: `balance/src/static/js/timer.js`

**Step 1: Add YouTube-specific end questions**

In the session end page, add conditional display:

```html
<!-- YouTube-specific question -->
<div class="question-group youtube-only" id="youtube-end-group" style="display: none;">
  <label class="question-label">Save anything good?</label>
  <div class="button-group binary-options" id="saved-something-options">
    <button class="btn btn--option" data-value="yes">Yes</button>
    <button class="btn btn--option" data-value="no">No</button>
  </div>
</div>
```

**Step 2: Update timerComplete to show correct questions**

```javascript
showEndPage(sessionType) {
  // Hide/show appropriate question groups
  const isYoutube = sessionType === 'youtube';

  document.getElementById('distraction-options').parentElement.style.display =
    isYoutube ? 'none' : 'block';
  document.getElementById('did-thing-options').parentElement.style.display =
    isYoutube ? 'none' : 'block';
  document.getElementById('youtube-end-group').style.display =
    isYoutube ? 'block' : 'none';

  // ... rest of function
}
```

**Step 3: Commit**

```bash
git add balance/src/templates/_content_index.html balance/src/static/js/timer.js
git commit -m "feat(balance): add YouTube-specific session end questions"
```

---

## Task 9: Environment Variables & Documentation

**Files:**
- Modify: `balance/Dockerfile`
- Modify: `k8s/base/balance.yaml`
- Modify: `docs/plans/2025-12-27-balance-app-design.md`

**Step 1: Document required environment variables**

Add to Balance deployment in `k8s/base/balance.yaml`:

```yaml
env:
  - name: NEXTDNS_API_KEY
    valueFrom:
      secretKeyRef:
        name: balance-secrets
        key: nextdns-api-key
  - name: NEXTDNS_PROFILE_ID
    valueFrom:
      secretKeyRef:
        name: balance-secrets
        key: nextdns-profile-id
```

**Step 2: Create the secret (manual step)**

```bash
kubectl create secret generic balance-secrets \
  --from-literal=nextdns-api-key=YOUR_API_KEY \
  --from-literal=nextdns-profile-id=YOUR_PROFILE_ID \
  -n knowledge-system
```

**Step 3: Update Balance design doc**

Add YouTube session section to `docs/plans/2025-12-27-balance-app-design.md`.

**Step 4: Commit**

```bash
git add k8s/base/balance.yaml docs/
git commit -m "docs(balance): add YouTube gatekeeper configuration"
```

---

## Task 10: Integration Testing

**Step 1: Run all Balance tests**

```bash
cd balance && python -m pytest tests/ -v
```

**Step 2: Manual testing checklist**

- [ ] Start YouTube session with 15 min duration
- [ ] Verify youtube.com is accessible
- [ ] Wait for timer to expire (or set short duration for testing)
- [ ] Verify youtube.com is blocked after expiry
- [ ] Check stats page shows YouTube session
- [ ] Verify evening cutoff still works

**Step 3: Deploy to k3s and test**

```bash
cd balance
docker build -t balance:latest .
docker save balance:latest | sudo k3s ctr images import -
kubectl rollout restart deploy/balance -n knowledge-system
```

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat(balance): complete YouTube gatekeeper implementation"
```

---

## Summary

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| 1 | NextDNS service | Medium |
| 2 | Database migration (youtube type + duration_minutes) | Medium |
| 3 | Update models (add youtube + duration_minutes) | Simple |
| 4 | Update sessions router (YouTube start + NextDNS) | Medium |
| 5 | APScheduler (ALL session types + evening cutoff) | Medium |
| 6 | Frontend type selection | Simple |
| 7 | Frontend JavaScript | Medium |
| 8 | Session end flow | Simple |
| 9 | Environment & docs | Simple |
| 10 | Integration testing | Manual |

**Key improvements beyond YouTube:**
- Server-side break enforcement for ALL session types (not just YouTube)
- Evening cutoff enforcement server-side (doesn't require browser visit)
- Pod restart recovery (checks for expired sessions on startup)
