# System-Wide Analytics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add events tracking across all 4 services (Bookmark Manager, Canvas, Kasten, Balance) with API endpoints for weekly export and analysis.

**Architecture:** Each service gets an identical `events` table and `/api/events` endpoint. A shared Python helper logs events. Weekly export script calls all 4 APIs and aggregates into JSON for Saturday analysis.

**Tech Stack:** Python 3.11, FastAPI, SQLite (aiosqlite), httpx

---

## Task 1: Shared Events Helper

**Files:**
- Create: `shared/events.py`

**Step 1: Create the shared events helper**

```python
# shared/events.py
"""Shared event logging helper for analytics across all services."""
import json
from datetime import datetime


async def log_event(db, event_type: str, name: str, metadata: dict = None):
    """Log an analytics event.

    Args:
        db: aiosqlite connection
        event_type: 'funnel' or 'feature'
        name: Event name like 'bookmark_created', 'rss_subscribe'
        metadata: Optional dict of additional context
    """
    await db.execute(
        "INSERT INTO events (timestamp, event_type, name, metadata) VALUES (?, ?, ?, ?)",
        (
            datetime.utcnow().isoformat(),
            event_type,
            name,
            json.dumps(metadata) if metadata else None
        )
    )
    await db.commit()
```

**Step 2: Commit**

```bash
git add shared/events.py
git commit -m "feat(analytics): add shared events helper"
```

---

## Task 2: Bookmark Manager - Events Table & API

**Files:**
- Modify: `bookmark-manager/src/database.py`
- Create: `bookmark-manager/src/routers/events.py`
- Modify: `bookmark-manager/src/main.py`
- Create: `bookmark-manager/tests/test_events.py`

**Step 1: Write the failing test**

```python
# bookmark-manager/tests/test_events.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import init_db, get_db

@pytest.fixture
async def setup_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    import src.database as db_module
    db_module.DATABASE_URL = db_path
    await init_db(db_path)
    yield db_path

@pytest.mark.asyncio
async def test_get_events_empty(setup_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/events")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "bookmark-manager"
        assert data["events"] == []

@pytest.mark.asyncio
async def test_get_events_with_since_filter(setup_db):
    # Insert a test event directly
    async with get_db(setup_db) as db:
        await db.execute(
            "INSERT INTO events (timestamp, event_type, name, metadata) VALUES (?, ?, ?, ?)",
            ("2026-01-01T00:00:00", "funnel", "bookmark_created", '{"source": "manual"}')
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Should find the event
        response = await client.get("/api/events?since=2025-12-01T00:00:00")
        assert response.status_code == 200
        assert len(response.json()["events"]) == 1

        # Should not find the event (since is after)
        response = await client.get("/api/events?since=2026-02-01T00:00:00")
        assert response.status_code == 200
        assert len(response.json()["events"]) == 0
```

**Step 2: Run test to verify it fails**

Run: `cd bookmark-manager && python -m pytest tests/test_events.py -v`
Expected: FAIL - events table doesn't exist, router not found

**Step 3: Add events table to database schema**

Modify `bookmark-manager/src/database.py`, add to the schema after other CREATE TABLE statements:

```python
            -- Analytics Events
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                event_type TEXT NOT NULL,
                name TEXT NOT NULL,
                metadata TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_name ON events(name);
```

**Step 4: Create events router**

```python
# bookmark-manager/src/routers/events.py
from fastapi import APIRouter
from ..database import get_db
import json

router = APIRouter(prefix="/api", tags=["events"])

SERVICE_NAME = "bookmark-manager"


@router.get("/events")
async def get_events(since: str = None):
    """Get analytics events, optionally filtered by timestamp."""
    query = "SELECT timestamp, event_type, name, metadata FROM events"
    params = ()

    if since:
        query += " WHERE timestamp > ?"
        params = (since,)

    query += " ORDER BY timestamp"

    async with get_db() as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        events = []
        for row in rows:
            events.append({
                "timestamp": row[0],
                "event_type": row[1],
                "name": row[2],
                "metadata": json.loads(row[3]) if row[3] else None
            })

        return {"service": SERVICE_NAME, "events": events}
```

**Step 5: Register router in main.py**

Add to `bookmark-manager/src/main.py`:

```python
from .routers import events
# ... after other router includes
app.include_router(events.router)
```

**Step 6: Run test to verify it passes**

Run: `cd bookmark-manager && python -m pytest tests/test_events.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add bookmark-manager/src/database.py bookmark-manager/src/routers/events.py bookmark-manager/src/main.py bookmark-manager/tests/test_events.py
git commit -m "feat(bookmark-manager): add events table and API endpoint"
```

---

## Task 3: Canvas - Events Table & API

**Files:**
- Modify: `canvas/src/database.py`
- Create: `canvas/src/routers/events.py`
- Modify: `canvas/src/main.py`
- Create: `canvas/tests/test_events.py`

**Step 1: Write the failing test**

```python
# canvas/tests/test_events.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import init_db, get_db

@pytest.fixture
async def setup_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    import src.database as db_module
    db_module.DATABASE_URL = db_path
    await init_db(db_path)
    yield db_path

@pytest.mark.asyncio
async def test_get_events_empty(setup_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/events")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "canvas"
        assert data["events"] == []
```

**Step 2: Run test to verify it fails**

Run: `cd canvas && python -m pytest tests/test_events.py -v`
Expected: FAIL

**Step 3: Add events table to database schema**

Modify `canvas/src/database.py`, add to schema:

```python
            -- Analytics Events
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                event_type TEXT NOT NULL,
                name TEXT NOT NULL,
                metadata TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_name ON events(name);
```

**Step 4: Create events router**

```python
# canvas/src/routers/events.py
from fastapi import APIRouter
from ..database import get_db
import json

router = APIRouter(prefix="/api", tags=["events"])

SERVICE_NAME = "canvas"


@router.get("/events")
async def get_events(since: str = None):
    """Get analytics events, optionally filtered by timestamp."""
    query = "SELECT timestamp, event_type, name, metadata FROM events"
    params = ()

    if since:
        query += " WHERE timestamp > ?"
        params = (since,)

    query += " ORDER BY timestamp"

    async with get_db() as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        events = []
        for row in rows:
            events.append({
                "timestamp": row[0],
                "event_type": row[1],
                "name": row[2],
                "metadata": json.loads(row[3]) if row[3] else None
            })

        return {"service": SERVICE_NAME, "events": events}
```

**Step 5: Register router in main.py**

Add to `canvas/src/main.py`:

```python
from .routers import events
app.include_router(events.router)
```

**Step 6: Run test to verify it passes**

Run: `cd canvas && python -m pytest tests/test_events.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add canvas/src/database.py canvas/src/routers/events.py canvas/src/main.py canvas/tests/test_events.py
git commit -m "feat(canvas): add events table and API endpoint"
```

---

## Task 4: Kasten - Events Table & API

**Files:**
- Modify: `kasten/src/database.py`
- Create: `kasten/src/routers/events.py`
- Modify: `kasten/src/main.py`
- Create: `kasten/tests/test_events.py`

**Step 1: Write the failing test**

```python
# kasten/tests/test_events.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import init_db, get_db

@pytest.fixture
async def setup_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    import src.database as db_module
    db_module.DATABASE_URL = db_path
    await init_db(db_path)
    yield db_path

@pytest.mark.asyncio
async def test_get_events_empty(setup_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/events")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "kasten"
        assert data["events"] == []
```

**Step 2: Run test to verify it fails**

Run: `cd kasten && python -m pytest tests/test_events.py -v`
Expected: FAIL

**Step 3: Add events table to database schema**

Modify `kasten/src/database.py`, add to schema:

```python
            -- Analytics Events
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                event_type TEXT NOT NULL,
                name TEXT NOT NULL,
                metadata TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_name ON events(name);
```

**Step 4: Create events router**

```python
# kasten/src/routers/events.py
from fastapi import APIRouter
from ..database import get_db
import json

router = APIRouter(prefix="/api", tags=["events"])

SERVICE_NAME = "kasten"


@router.get("/events")
async def get_events(since: str = None):
    """Get analytics events, optionally filtered by timestamp."""
    query = "SELECT timestamp, event_type, name, metadata FROM events"
    params = ()

    if since:
        query += " WHERE timestamp > ?"
        params = (since,)

    query += " ORDER BY timestamp"

    async with get_db() as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        events = []
        for row in rows:
            events.append({
                "timestamp": row[0],
                "event_type": row[1],
                "name": row[2],
                "metadata": json.loads(row[3]) if row[3] else None
            })

        return {"service": SERVICE_NAME, "events": events}
```

**Step 5: Register router in main.py**

Add to `kasten/src/main.py`:

```python
from .routers import events
app.include_router(events.router)
```

**Step 6: Run test to verify it passes**

Run: `cd kasten && python -m pytest tests/test_events.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add kasten/src/database.py kasten/src/routers/events.py kasten/src/main.py kasten/tests/test_events.py
git commit -m "feat(kasten): add events table and API endpoint"
```

---

## Task 5: Balance - Events Table & API

**Files:**
- Modify: `balance/src/database.py`
- Create: `balance/src/routers/events.py`
- Modify: `balance/src/main.py`
- Create: `balance/tests/test_events.py`

**Step 1: Write the failing test**

```python
# balance/tests/test_events.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import init_db, get_db

@pytest.fixture
async def setup_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    import src.database as db_module
    db_module.DATABASE_URL = db_path
    await init_db(db_path)
    yield db_path

@pytest.mark.asyncio
async def test_get_events_empty(setup_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/events")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "balance"
        assert data["events"] == []
```

**Step 2: Run test to verify it fails**

Run: `cd balance && DATABASE_URL=./data/test.db python -m pytest tests/test_events.py -v`
Expected: FAIL

**Step 3: Add events table to database schema**

Modify `balance/src/database.py`, add to the schema (inside the executescript):

```python
            -- Analytics Events
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                event_type TEXT NOT NULL,
                name TEXT NOT NULL,
                metadata TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_name ON events(name);
```

**Step 4: Create events router**

```python
# balance/src/routers/events.py
from fastapi import APIRouter
from ..database import get_db
import json

router = APIRouter(prefix="/api", tags=["events"])

SERVICE_NAME = "balance"


@router.get("/events")
async def get_events(since: str = None):
    """Get analytics events, optionally filtered by timestamp."""
    query = "SELECT timestamp, event_type, name, metadata FROM events"
    params = ()

    if since:
        query += " WHERE timestamp > ?"
        params = (since,)

    query += " ORDER BY timestamp"

    async with get_db() as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        events = []
        for row in rows:
            events.append({
                "timestamp": row[0],
                "event_type": row[1],
                "name": row[2],
                "metadata": json.loads(row[3]) if row[3] else None
            })

        return {"service": SERVICE_NAME, "events": events}
```

**Step 5: Register router in main.py**

Add to `balance/src/main.py`:

```python
from .routers import events
app.include_router(events.router)
```

**Step 6: Run test to verify it passes**

Run: `cd balance && DATABASE_URL=./data/test.db python -m pytest tests/test_events.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add balance/src/database.py balance/src/routers/events.py balance/src/main.py balance/tests/test_events.py
git commit -m "feat(balance): add events table and API endpoint"
```

---

## Task 6: Instrument Bookmark Manager - Funnel Events

**Files:**
- Modify: `bookmark-manager/src/routers/bookmarks.py`
- Modify: `bookmark-manager/src/routers/canvas.py` (quote push)
- Modify: `bookmark-manager/src/jobs/expiry.py` (if exists, for expiry tracking)

**Step 1: Add bookmark_created event**

In `bookmark-manager/src/routers/bookmarks.py`, after successful bookmark creation:

```python
# At top of file
from shared.events import log_event

# After bookmark is inserted and committed, add:
await log_event(db, "funnel", "bookmark_created", {
    "bookmark_id": bookmark_id,
    "source": source,  # "telegram", "rss", or "manual"
    "is_thesis": is_thesis,
    "is_pinned": is_pinned
})
```

**Step 2: Add quote_pushed event**

In the canvas quote push endpoint (wherever POST /canvas/quotes is handled):

```python
await log_event(db, "funnel", "quote_pushed", {
    "bookmark_id": bookmark_id,
    "quote_length": len(quote_text)
})
```

**Step 3: Add bookmark_expired event**

In the expiry job (if it exists), when a bookmark is deleted due to expiry:

```python
await log_event(db, "funnel", "bookmark_expired", {
    "bookmark_id": bookmark_id,
    "days_in_inbox": days_since_created
})
```

**Step 4: Commit**

```bash
git add bookmark-manager/src/routers/bookmarks.py bookmark-manager/src/routers/canvas.py
git commit -m "feat(bookmark-manager): instrument funnel events"
```

---

## Task 7: Instrument Bookmark Manager - Feature Events

**Files:**
- Modify: `bookmark-manager/src/routers/feeds.py`
- Modify: `bookmark-manager/src/routers/bookmarks.py`

**Step 1: Add RSS feature events**

In `bookmark-manager/src/routers/feeds.py`:

```python
from shared.events import log_event

# After feed subscribe:
await log_event(db, "feature", "rss_subscribe", {"feed_url": feed_url})

# After feed unsubscribe:
await log_event(db, "feature", "rss_unsubscribe", {"feed_id": feed_id})

# After feed item promoted to bookmark:
await log_event(db, "feature", "feed_item_promoted", {"feed_id": feed_id, "item_id": item_id})
```

**Step 2: Add bookmark feature events**

In `bookmark-manager/src/routers/bookmarks.py`:

```python
# After retry scrape:
await log_event(db, "feature", "retry_scrape", {"bookmark_id": bookmark_id, "success": success})

# After move to pins:
await log_event(db, "feature", "move_to_pins", {"bookmark_id": bookmark_id})

# After move to thesis:
await log_event(db, "feature", "move_to_thesis", {"bookmark_id": bookmark_id})

# After Zotero sync:
await log_event(db, "feature", "zotero_sync", {"papers_synced": count})

# After backup created:
await log_event(db, "feature", "backup_created", {})
```

**Step 3: Commit**

```bash
git add bookmark-manager/src/routers/feeds.py bookmark-manager/src/routers/bookmarks.py
git commit -m "feat(bookmark-manager): instrument feature events"
```

---

## Task 8: Instrument Canvas - All Events

**Files:**
- Modify: `canvas/src/routers/canvas.py`
- Modify: `canvas/src/routers/quotes.py`
- Modify: `canvas/src/routers/workspace.py`

**Step 1: Add funnel events**

```python
from shared.events import log_event

# In quotes router - after quote received:
await log_event(db, "funnel", "quote_received", {"bookmark_id": bookmark_id})

# In canvas router - after note sent to Kasten:
await log_event(db, "funnel", "note_sent_to_kasten", {
    "note_id": note_id,
    "has_parent": parent_id is not None,
    "source_id": source_id
})
```

**Step 2: Add feature events**

```python
# After draft edited (debounced, in PUT /api/canvas):
await log_event(db, "feature", "draft_edited", {"char_count": len(content)})

# In workspace router:
await log_event(db, "feature", "workspace_note_added", {"note_id": note_id})
await log_event(db, "feature", "workspace_connection_created", {"from_id": from_id, "to_id": to_id})

# In parent picker:
await log_event(db, "feature", "parent_selected", {"parent_id": parent_id})
await log_event(db, "feature", "parent_skipped", {})
```

**Step 3: Commit**

```bash
git add canvas/src/routers/
git commit -m "feat(canvas): instrument all events"
```

---

## Task 9: Instrument Kasten - All Events

**Files:**
- Modify: `kasten/src/routers/notes.py`
- Modify: `kasten/src/routers/sources.py`

**Step 1: Add funnel events**

```python
from shared.events import log_event

# After note created:
await log_event(db, "funnel", "note_created", {
    "note_id": note_id,
    "parent_id": parent_id,
    "source_id": source_id,
    "link_count": len(links)
})

# After link followed (in note view, track where user came from):
await log_event(db, "funnel", "link_followed", {"from_note": from_id, "to_note": to_id})
```

**Step 2: Add feature events**

```python
# After entry point used:
await log_event(db, "feature", "entry_point_used", {"note_id": note_id})

# After random note:
await log_event(db, "feature", "random_note_used", {"landed_on": note_id})

# After source viewed:
await log_event(db, "feature", "source_viewed", {"source_id": source_id})

# After reindex:
await log_event(db, "feature", "reindex_triggered", {"notes_indexed": count})
```

**Step 3: Commit**

```bash
git add kasten/src/routers/
git commit -m "feat(kasten): instrument all events"
```

---

## Task 10: Instrument Balance - Feature Events

**Files:**
- Modify: `balance/src/routers/sessions.py`
- Modify: `balance/src/routers/nextup.py`

**Step 1: Add feature events**

```python
from shared.events import log_event

# In sessions.py - after YouTube session started:
if session_type == "youtube":
    await log_event(db, "feature", "youtube_session_started", {
        "duration_minutes": duration_minutes
    })

# In nextup.py - after task created:
await log_event(db, "feature", "nextup_created", {"text": text[:50]})

# In sessions.py - after session started with next_up_id:
if next_up_id:
    await log_event(db, "feature", "nextup_completed", {"next_up_id": next_up_id})
```

**Step 2: Commit**

```bash
git add balance/src/routers/sessions.py balance/src/routers/nextup.py
git commit -m "feat(balance): instrument feature events"
```

---

## Task 11: Weekly Export Script

**Files:**
- Create: `scripts/weekly_analytics_export.py`

**Step 1: Create the export script**

```python
#!/usr/bin/env python3
# scripts/weekly_analytics_export.py
"""Weekly analytics export - pulls events from all services via API."""

import httpx
import json
from datetime import datetime, timedelta
from pathlib import Path

SERVICES = {
    'bookmark': 'https://bookmark.gstoehl.dev/api/events',
    'canvas': 'https://canvas.gstoehl.dev/api/events',
    'kasten': 'https://kasten.gstoehl.dev/api/events',
    'balance': 'https://balance.gstoehl.dev/api/events',
}

OUTPUT_DIR = Path(__file__).parent.parent / 'analytics'


def export_weekly(days: int = 7) -> str:
    """Export events from the last N days."""
    since = (datetime.now() - timedelta(days=days)).isoformat()

    all_events = []
    errors = []

    for service, url in SERVICES.items():
        try:
            resp = httpx.get(f"{url}?since={since}", timeout=30.0)
            resp.raise_for_status()
            data = resp.json()

            for event in data.get('events', []):
                event['service'] = service
                all_events.append(event)

            print(f"✓ {service}: {len(data.get('events', []))} events")
        except Exception as e:
            errors.append(f"{service}: {e}")
            print(f"✗ {service}: {e}")

    # Sort by timestamp
    all_events.sort(key=lambda e: e.get('timestamp', ''))

    output = {
        'exported_at': datetime.now().isoformat(),
        'period': {
            'start': since,
            'end': datetime.now().isoformat(),
            'days': days
        },
        'summary': {
            'total_events': len(all_events),
            'by_service': {},
            'by_type': {},
            'by_name': {}
        },
        'events': all_events,
        'errors': errors
    }

    # Calculate summary
    for event in all_events:
        svc = event.get('service', 'unknown')
        etype = event.get('event_type', 'unknown')
        name = event.get('name', 'unknown')

        output['summary']['by_service'][svc] = output['summary']['by_service'].get(svc, 0) + 1
        output['summary']['by_type'][etype] = output['summary']['by_type'].get(etype, 0) + 1
        output['summary']['by_name'][name] = output['summary']['by_name'].get(name, 0) + 1

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outfile = OUTPUT_DIR / f"weekly-{datetime.now():%Y-%m-%d}.json"
    outfile.write_text(json.dumps(output, indent=2))

    print(f"\n✓ Exported {len(all_events)} events to {outfile}")
    return str(outfile)


if __name__ == '__main__':
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    export_weekly(days)
```

**Step 2: Make executable**

```bash
chmod +x scripts/weekly_analytics_export.py
```

**Step 3: Create analytics directory with gitignore**

```bash
mkdir -p analytics
echo "*.json" > analytics/.gitignore
echo "!.gitignore" >> analytics/.gitignore
```

**Step 4: Commit**

```bash
git add scripts/weekly_analytics_export.py analytics/.gitignore
git commit -m "feat(analytics): add weekly export script"
```

---

## Task 12: Deploy & Test

**Step 1: Rebuild all Docker images**

```bash
docker build -t bookmark-manager:latest -f bookmark-manager/Dockerfile .
docker build -t canvas:latest -f canvas/Dockerfile .
docker build -t kasten:latest -f kasten/Dockerfile .
docker build -t balance:latest -f balance/Dockerfile .
```

**Step 2: Apply K8s deployments**

```bash
kubectl rollout restart deployment/bookmark-manager -n knowledge-system
kubectl rollout restart deployment/canvas -n knowledge-system
kubectl rollout restart deployment/kasten -n knowledge-system
kubectl rollout restart deployment/balance -n knowledge-system
```

**Step 3: Verify API endpoints**

```bash
curl -s https://bookmark.gstoehl.dev/api/events | jq .
curl -s https://canvas.gstoehl.dev/api/events | jq .
curl -s https://kasten.gstoehl.dev/api/events | jq .
curl -s https://balance.gstoehl.dev/api/events | jq .
```

**Step 4: Test export script**

```bash
python scripts/weekly_analytics_export.py
cat analytics/weekly-*.json | jq .summary
```

**Step 5: Commit any final fixes**

```bash
git add -A
git commit -m "chore: deployment verification complete"
```

---

## Task 13: Cron Setup

**Step 1: Add Saturday cron job**

```bash
crontab -e
```

Add:
```
# Weekly analytics export - Saturday 8am
0 8 * * 6 cd /home/ags/knowledge-system && /usr/bin/python3 scripts/weekly_analytics_export.py >> /var/log/analytics-export.log 2>&1
```

**Step 2: Verify cron is set**

```bash
crontab -l | grep analytics
```

**Step 3: Done!**

The system is now tracking events. Use it for a week, then run the first Saturday analysis.
