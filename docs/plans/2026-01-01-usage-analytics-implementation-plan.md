# Usage Analytics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add lightweight event tracking across all services to measure note production, feature usage, and identify dead features.

**Architecture:** Each service logs events to its own SQLite `events` table. Weekly export script aggregates all events + session analyses into a single JSON file for Saturday analysis with Claude.

**Tech Stack:** Python/FastAPI, SQLite, aiosqlite, vanilla JS (Beacon API)

**Reference Docs:**
- Design: `docs/plans/2026-01-01-usage-analytics-design.md`
- Transcript Analysis (already implemented): `docs/plans/2026-01-01-transcript-analysis-design.md`

---

## Phase 1: Infrastructure

### Task 1.1: Create Shared Events Module

**Files:**
- Create: `shared/events.py`

**Step 1: Create the events helper module**

```python
# shared/events.py
"""
Lightweight event logging for usage analytics.

Usage:
    from shared.events import log_event
    await log_event(db, "target", "note_created", metadata={"note_id": "1230a", "link_count": 3})
"""
import json
from datetime import datetime
from typing import Optional

async def log_event(
    db,
    event_type: str,
    name: str,
    outcome: Optional[str] = None,
    duration_ms: Optional[int] = None,
    metadata: Optional[dict] = None
) -> None:
    """
    Log an event to the events table.

    Args:
        db: aiosqlite connection
        event_type: 'target' | 'feature' | 'navigation' | 'session'
        name: Event name (e.g., 'note_created', 'page_view')
        outcome: Optional outcome ('completed', 'abandoned', None)
        duration_ms: Optional duration in milliseconds
        metadata: Optional JSON-serializable dict
    """
    await db.execute("""
        INSERT INTO events (timestamp, event_type, name, outcome, duration_ms, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        event_type,
        name,
        outcome,
        duration_ms,
        json.dumps(metadata) if metadata else None
    ))
    await db.commit()


# SQL schema for events table - add to each service's database.py
EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    name TEXT NOT NULL,
    outcome TEXT,
    duration_ms INTEGER,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_type_name ON events(event_type, name);
"""
```

**Step 2: Commit**

```bash
git add shared/events.py
git commit -m "feat(shared): add events logging module for usage analytics"
```

---

### Task 1.2: Add Events Table to Kasten

**Files:**
- Modify: `kasten/src/database.py`

**Step 1: Read current database.py**

Check the existing schema and init_db function.

**Step 2: Add events table to schema**

Add after existing table creation:

```python
# In init_db() function, after existing CREATE TABLE statements:

# Events table for usage analytics
await db.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        name TEXT NOT NULL,
        outcome TEXT,
        duration_ms INTEGER,
        metadata TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
""")
await db.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
await db.execute("CREATE INDEX IF NOT EXISTS idx_events_type_name ON events(event_type, name)")
```

**Step 3: Verify by restarting service**

```bash
docker compose -f docker-compose.dev.yml restart kasten
docker compose -f docker-compose.dev.yml logs kasten | tail -20
```

Expected: No errors, service starts normally.

**Step 4: Verify table exists**

```bash
sqlite3 kasten/data/kasten.db ".schema events"
```

Expected: Shows the events table schema.

**Step 5: Commit**

```bash
git add kasten/src/database.py
git commit -m "feat(kasten): add events table for usage analytics"
```

---

### Task 1.3: Add Events Table to Canvas

**Files:**
- Modify: `canvas/src/database.py`

**Step 1: Read current database.py**

Check the existing schema.

**Step 2: Add events table (same schema as Kasten)**

```python
# In init_db() function:

await db.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        name TEXT NOT NULL,
        outcome TEXT,
        duration_ms INTEGER,
        metadata TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
""")
await db.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
await db.execute("CREATE INDEX IF NOT EXISTS idx_events_type_name ON events(event_type, name)")
```

**Step 3: Restart and verify**

```bash
docker compose -f docker-compose.dev.yml restart canvas
sqlite3 canvas/data/canvas.db ".schema events"
```

**Step 4: Commit**

```bash
git add canvas/src/database.py
git commit -m "feat(canvas): add events table for usage analytics"
```

---

### Task 1.4: Add Events Table to Bookmark Manager

**Files:**
- Modify: `bookmark-manager/src/database.py`

**Step 1: Read current database.py**

**Step 2: Add events table (same schema)**

**Step 3: Restart and verify**

```bash
docker compose -f docker-compose.dev.yml restart bookmark-manager
sqlite3 bookmark-manager/data/bookmarks.db ".schema events"
```

**Step 4: Commit**

```bash
git add bookmark-manager/src/database.py
git commit -m "feat(bookmark-manager): add events table for usage analytics"
```

---

### Task 1.5: Add Events Table to Balance

**Files:**
- Modify: `balance/src/database.py`

**Step 1: Read current database.py**

**Step 2: Add events table (same schema)**

**Step 3: Restart and verify**

```bash
docker compose -f docker-compose.dev.yml restart balance
sqlite3 balance/data/balance.db ".schema events"
```

**Step 4: Commit**

```bash
git add balance/src/database.py
git commit -m "feat(balance): add events table for usage analytics"
```

---

### Task 1.6: Create Weekly Export Script

**Files:**
- Create: `scripts/weekly_analytics_export.py`

**Step 1: Create the export script**

```python
#!/usr/bin/env python3
"""
Weekly analytics export script.
Aggregates events from all services + session analyses into a single JSON file.

Usage:
    python scripts/weekly_analytics_export.py

Output:
    /home/ags/knowledge-system/analytics/weekly-YYYY-MM-DD.json

Cron (Saturday 8am):
    0 8 * * 6 cd ~/knowledge-system && python3 scripts/weekly_analytics_export.py
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta

BASE_PATH = '/home/ags/knowledge-system'

SERVICES = {
    'bookmark': f'{BASE_PATH}/bookmark-manager/data/bookmarks.db',
    'canvas': f'{BASE_PATH}/canvas/data/canvas.db',
    'kasten': f'{BASE_PATH}/kasten/data/kasten.db',
    'balance': f'{BASE_PATH}/balance/data/balance.db',
}


def export_weekly_events():
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

    export = {
        'period': {
            'start': week_ago,
            'end': datetime.utcnow().isoformat(),
            'exported_at': datetime.utcnow().isoformat()
        },
        'events': [],
        'session_analyses': [],
        'sessions': []
    }

    # Export events from all services
    for service, db_path in SERVICES.items():
        if not Path(db_path).exists():
            print(f"Skipping {service}: {db_path} not found")
            continue
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.execute("""
                SELECT timestamp, event_type, name, outcome, duration_ms, metadata
                FROM events
                WHERE timestamp > ?
                ORDER BY timestamp
            """, (week_ago,))

            for row in cursor:
                export['events'].append({
                    'service': service,
                    'timestamp': row[0],
                    'event_type': row[1],
                    'name': row[2],
                    'outcome': row[3],
                    'duration_ms': row[4],
                    'metadata': json.loads(row[5]) if row[5] else {}
                })
            print(f"{service}: {len([e for e in export['events'] if e['service'] == service])} events")
        except sqlite3.OperationalError as e:
            print(f"{service}: events table not found ({e})")
        conn.close()

    # Export session analyses from Balance (transcript analysis results)
    balance_db = SERVICES['balance']
    if Path(balance_db).exists():
        conn = sqlite3.connect(balance_db)
        try:
            cursor = conn.execute("""
                SELECT
                    sa.session_id,
                    sa.analyzed_at,
                    sa.prompt_count,
                    sa.intention_alignment,
                    sa.alignment_detail,
                    sa.scope_behavior,
                    sa.scope_detail,
                    sa.project_switches,
                    sa.tool_appropriate_count,
                    sa.tool_questionable_count,
                    sa.red_flags,
                    sa.one_line_summary,
                    sa.severity
                FROM session_analyses sa
                JOIN sessions s ON sa.session_id = s.id
                WHERE s.started_at > ?
                ORDER BY sa.analyzed_at
            """, (week_ago,))

            for row in cursor:
                export['session_analyses'].append({
                    'session_id': row[0],
                    'analyzed_at': row[1],
                    'prompt_count': row[2],
                    'intention_alignment': row[3],
                    'alignment_detail': row[4],
                    'scope_behavior': row[5],
                    'scope_detail': row[6],
                    'project_switches': row[7],
                    'tool_appropriate_count': row[8],
                    'tool_questionable_count': row[9],
                    'red_flags': json.loads(row[10]) if row[10] else [],
                    'one_line_summary': row[11],
                    'severity': row[12]
                })
            print(f"session_analyses: {len(export['session_analyses'])} records")
        except sqlite3.OperationalError as e:
            print(f"session_analyses: table not found ({e})")

        try:
            cursor = conn.execute("""
                SELECT
                    id,
                    type,
                    intention,
                    started_at,
                    ended_at,
                    distractions,
                    did_the_thing,
                    rabbit_hole,
                    claude_used
                FROM sessions
                WHERE started_at > ?
                ORDER BY started_at
            """, (week_ago,))

            for row in cursor:
                export['sessions'].append({
                    'id': row[0],
                    'type': row[1],
                    'intention': row[2],
                    'started_at': row[3],
                    'ended_at': row[4],
                    'distractions': row[5],
                    'did_the_thing': row[6],
                    'rabbit_hole': row[7],
                    'claude_used': row[8]
                })
            print(f"sessions: {len(export['sessions'])} records")
        except sqlite3.OperationalError as e:
            print(f"sessions: error ({e})")
        conn.close()

    # Sort events by timestamp
    export['events'].sort(key=lambda e: e['timestamp'])

    # Save for Claude analysis
    output_dir = Path(f'{BASE_PATH}/analytics')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"weekly-{datetime.utcnow().strftime('%Y-%m-%d')}.json"

    with open(output_path, 'w') as f:
        json.dump(export, f, indent=2)

    print(f"\nExported to {output_path}")
    print(f"Total: {len(export['events'])} events, {len(export['sessions'])} sessions, {len(export['session_analyses'])} analyses")

    return str(output_path)


if __name__ == '__main__':
    export_weekly_events()
```

**Step 2: Make executable and test**

```bash
chmod +x scripts/weekly_analytics_export.py
python scripts/weekly_analytics_export.py
```

Expected: Creates `analytics/weekly-2026-01-01.json` (mostly empty since no events yet).

**Step 3: Verify output**

```bash
cat analytics/weekly-2026-01-01.json | head -30
```

**Step 4: Commit**

```bash
git add scripts/weekly_analytics_export.py
git commit -m "feat(scripts): add weekly analytics export script"
```

---

## Phase 2: Instrument Kasten (Target Layer)

### Task 2.1: Add Event Logging to Note Creation

**Files:**
- Modify: `kasten/src/routers/notes.py` (or wherever POST /api/notes is)

**Step 1: Read the current notes router**

Find the POST /api/notes endpoint.

**Step 2: Import events module and add logging**

```python
# At top of file
import sys
sys.path.insert(0, '/home/ags/knowledge-system')
from shared.events import log_event

# In the create_note endpoint, after successful creation:
await log_event(
    db,
    event_type="target",
    name="note_created",
    metadata={
        "note_id": note.id,
        "parent_id": note.parent_id,
        "source_id": note.source_id,
        "link_count": len(outgoing_links),  # count [[links]] in content
        "created_via": request.headers.get("X-Created-Via", "direct")
    }
)
```

**Step 3: Test by creating a note**

```bash
curl -X POST http://localhost:8003/api/notes \
  -H "Content-Type: application/json" \
  -d '{"content": "# Test Note\n\nTest content", "parent_id": null}'
```

**Step 4: Verify event was logged**

```bash
sqlite3 kasten/data/kasten.db "SELECT * FROM events ORDER BY id DESC LIMIT 1"
```

Expected: Shows the note_created event.

**Step 5: Commit**

```bash
git add kasten/src/routers/notes.py
git commit -m "feat(kasten): log note_created events for analytics"
```

---

### Task 2.2: Add Event Logging to Note View

**Files:**
- Modify: `kasten/src/routers/notes.py`

**Step 1: Find GET /api/notes/{id} endpoint**

**Step 2: Add logging**

```python
# In get_note endpoint, after fetching note:
await log_event(
    db,
    event_type="navigation",
    name="note_viewed",
    metadata={
        "note_id": note_id,
        "from_note_id": request.headers.get("X-From-Note"),  # if following a link
    }
)
```

**Step 3: Test and verify**

```bash
curl http://localhost:8003/api/notes/1230a
sqlite3 kasten/data/kasten.db "SELECT * FROM events WHERE name='note_viewed' LIMIT 1"
```

**Step 4: Commit**

```bash
git add kasten/src/routers/notes.py
git commit -m "feat(kasten): log note_viewed events for analytics"
```

---

### Task 2.3: Add Event Logging to Entry Points and Random Note

**Files:**
- Modify: `kasten/src/routers/notes.py`

**Step 1: Find entry points and random note endpoints**

**Step 2: Add logging for entry_point_used**

```python
# In entry points click handler or API:
await log_event(db, "navigation", "entry_point_used", metadata={"note_id": note_id})
```

**Step 3: Add logging for random_note_used**

```python
# In random note endpoint:
await log_event(db, "feature", "random_note_used", metadata={"landed_on": note_id})
```

**Step 4: Test both features**

**Step 5: Commit**

```bash
git add kasten/src/routers/notes.py
git commit -m "feat(kasten): log entry_point and random_note events"
```

---

### Task 2.4: Add Event Logging to Source View

**Files:**
- Modify: `kasten/src/routers/sources.py` (or wherever sources are)

**Step 1: Find GET /api/sources/{id} endpoint**

**Step 2: Add logging**

```python
await log_event(db, "feature", "source_viewed", metadata={"source_id": source_id})
```

**Step 3: Test and commit**

```bash
git add kasten/src/routers/sources.py
git commit -m "feat(kasten): log source_viewed events for analytics"
```

---

## Phase 3: Instrument Canvas

### Task 3.1: Add Event Logging to Quote Reception

**Files:**
- Modify: `canvas/src/routers/quotes.py` (or main.py)

**Step 1: Find POST /api/quotes endpoint**

**Step 2: Add logging**

```python
from shared.events import log_event

# After receiving quote:
await log_event(
    db,
    event_type="target",
    name="quote_received",
    metadata={
        "bookmark_id": quote.bookmark_id,
        "quote_length": len(quote.text),
        "source_url": quote.source_url
    }
)
```

**Step 3: Test and commit**

```bash
git add canvas/src/routers/quotes.py
git commit -m "feat(canvas): log quote_received events for analytics"
```

---

### Task 3.2: Add Event Logging to Note Extraction

**Files:**
- Modify: `canvas/src/routers/notes.py` (or draft router)

**Step 1: Find note extraction logic**

**Step 2: Add logging when note is sent to Kasten**

```python
await log_event(
    db,
    event_type="target",
    name="note_sent_to_kasten",
    metadata={
        "note_id": created_note_id,
        "source_bookmark_id": source_bookmark_id,
        "had_parent": parent_id is not None
    }
)
```

**Step 3: Test and commit**

```bash
git add canvas/src/
git commit -m "feat(canvas): log note extraction events for analytics"
```

---

### Task 3.3: Add Feature Event Logging

**Files:**
- Modify: `canvas/src/routers/workspace.py`

**Step 1: Add logging for workspace features**

```python
# workspace_note_added
await log_event(db, "feature", "workspace_note_added", metadata={"note_id": note_id})

# workspace_connection_created
await log_event(db, "feature", "workspace_connection_created", metadata={
    "from_id": from_id, "to_id": to_id, "label": label
})

# parent_selected / parent_skipped
await log_event(db, "feature", "parent_selected", metadata={"parent_id": parent_id})
# or
await log_event(db, "feature", "parent_skipped")
```

**Step 2: Commit**

```bash
git add canvas/src/
git commit -m "feat(canvas): log workspace feature events for analytics"
```

---

## Phase 4: Instrument Bookmark Manager

### Task 4.1: Add Event Logging to Bookmark Creation

**Files:**
- Modify: `bookmark-manager/src/routers/bookmarks.py`

**Step 1: Find POST /bookmarks endpoint**

**Step 2: Add logging**

```python
from shared.events import log_event

await log_event(
    db,
    event_type="target",
    name="bookmark_created",
    metadata={
        "bookmark_id": bookmark.id,
        "source": request.headers.get("X-Source", "manual"),  # telegram/rss/manual
        "is_thesis": bookmark.is_thesis,
        "is_pinned": bookmark.pinned
    }
)
```

**Step 3: Test via API and Telegram bot**

**Step 4: Commit**

```bash
git add bookmark-manager/src/routers/bookmarks.py
git commit -m "feat(bookmark-manager): log bookmark_created events"
```

---

### Task 4.2: Add Event Logging to Bookmark Processing

**Files:**
- Modify: `bookmark-manager/src/routers/bookmarks.py`

**Step 1: Add logging for processing actions**

```python
# When bookmark is moved to pins:
await log_event(db, "feature", "move_to_pins", metadata={"bookmark_id": bookmark_id})

# When moved to thesis:
await log_event(db, "feature", "move_to_thesis", metadata={"bookmark_id": bookmark_id})

# When quote is pushed:
await log_event(db, "target", "quote_pushed", metadata={
    "bookmark_id": bookmark_id,
    "quote_length": len(quote_text)
})

# When deleted manually:
await log_event(db, "target", "bookmark_processed", metadata={
    "bookmark_id": bookmark_id,
    "outcome": "dismissed",
    "days_in_inbox": (datetime.utcnow() - bookmark.added_at).days
})
```

**Step 2: Commit**

```bash
git add bookmark-manager/src/
git commit -m "feat(bookmark-manager): log bookmark processing events"
```

---

### Task 4.3: Add Event Logging to Expiry Job

**Files:**
- Modify: `bookmark-manager/src/jobs/expiry.py` (or wherever expiry runs)

**Step 1: Find expiry job**

**Step 2: Add logging for each expired bookmark**

```python
for bookmark in expired_bookmarks:
    await log_event(
        db,
        event_type="target",
        name="bookmark_expired",
        metadata={
            "bookmark_id": bookmark.id,
            "days_in_inbox": 7,
            "was_viewed": bookmark.view_count > 0
        }
    )
```

**Step 3: Commit**

```bash
git add bookmark-manager/src/
git commit -m "feat(bookmark-manager): log bookmark_expired events"
```

---

### Task 4.4: Add RSS Feature Event Logging

**Files:**
- Modify: `bookmark-manager/src/routers/feeds.py`

**Step 1: Add logging**

```python
# rss_subscribe
await log_event(db, "feature", "rss_subscribe", metadata={"feed_url": feed.url})

# rss_unsubscribe
await log_event(db, "feature", "rss_unsubscribe", metadata={"feed_id": feed_id})

# feed_item_promoted
await log_event(db, "feature", "feed_item_promoted", metadata={
    "feed_id": feed_id, "item_id": item_id
})
```

**Step 2: Commit**

```bash
git add bookmark-manager/src/routers/feeds.py
git commit -m "feat(bookmark-manager): log RSS feature events"
```

---

## Phase 5: Instrument Balance

### Task 5.1: Add Feature Event Logging

**Files:**
- Modify: `balance/src/routers/` (various)

**Step 1: Add logging for feature usage**

```python
# stats_viewed (in stats router)
await log_event(db, "feature", "stats_viewed", metadata={"period": period})

# settings_changed (in settings router)
await log_event(db, "feature", "settings_changed", metadata={
    "setting": setting_name,
    "old_value": old_value,
    "new_value": new_value
})

# meditation_logged
await log_event(db, "feature", "meditation_logged", metadata={
    "duration": duration_minutes,
    "time_of_day": time_of_day
})

# exercise_logged
await log_event(db, "feature", "exercise_logged", metadata={
    "type": exercise_type,
    "duration": duration_minutes,
    "intensity": intensity
})

# pulse_logged
await log_event(db, "feature", "pulse_logged", metadata={
    "feeling": feeling,
    "had_connection": had_connection
})
```

**Step 2: Commit**

```bash
git add balance/src/
git commit -m "feat(balance): log feature usage events for analytics"
```

---

## Phase 6: Frontend Tracking

### Task 6.1: Create Shared Analytics JS Module

**Files:**
- Create: `shared/js/analytics.js`

**Step 1: Create the module**

```javascript
// shared/js/analytics.js
// Lightweight page view and time-on-page tracking

(function() {
  const SERVICE = document.body.dataset.service || 'unknown';
  const pageLoadTime = Date.now();
  const currentPage = window.location.pathname;

  // Log page view on load
  fetch('/api/events', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      event_type: 'navigation',
      name: 'page_view',
      metadata: {
        page: currentPage,
        referrer: document.referrer
      }
    })
  }).catch(() => {}); // Fail silently

  // Log time on page when leaving
  window.addEventListener('beforeunload', function() {
    const duration = Date.now() - pageLoadTime;
    navigator.sendBeacon('/api/events', JSON.stringify({
      event_type: 'navigation',
      name: 'page_exit',
      duration_ms: duration,
      metadata: {
        page: currentPage
      }
    }));
  });
})();
```

**Step 2: Commit**

```bash
git add shared/js/analytics.js
git commit -m "feat(shared): add frontend analytics tracking module"
```

---

### Task 6.2: Add Events API Endpoint to Each Service

**Files:**
- Modify: `kasten/src/main.py`
- Modify: `canvas/src/main.py`
- Modify: `bookmark-manager/src/main.py`
- Modify: `balance/src/main.py`

**Step 1: Add POST /api/events endpoint to each service**

```python
from pydantic import BaseModel
from typing import Optional

class EventRequest(BaseModel):
    event_type: str
    name: str
    outcome: Optional[str] = None
    duration_ms: Optional[int] = None
    metadata: Optional[dict] = None

@app.post("/api/events")
async def log_event_endpoint(event: EventRequest, db=Depends(get_db)):
    await log_event(
        db,
        event.event_type,
        event.name,
        event.outcome,
        event.duration_ms,
        event.metadata
    )
    return {"status": "ok"}
```

**Step 2: Commit**

```bash
git add */src/main.py
git commit -m "feat(all): add POST /api/events endpoint for frontend tracking"
```

---

### Task 6.3: Include Analytics JS in Base Templates

**Files:**
- Modify: `kasten/src/templates/base.html`
- Modify: `canvas/src/templates/base.html`
- Modify: `bookmark-manager/src/templates/base.html`
- Modify: `balance/src/templates/base.html`

**Step 1: Add to each base template before closing </body>**

```html
<body data-service="kasten"> <!-- or canvas, bookmark, balance -->
  ...
  <script src="/static/js/analytics.js"></script>
</body>
```

**Step 2: Ensure analytics.js is served from shared**

Either symlink or copy to each service's static folder, or serve from shared.

**Step 3: Commit**

```bash
git add */src/templates/base.html
git commit -m "feat(all): include analytics.js in all service templates"
```

---

## Phase 7: Setup Cron and First Analysis

### Task 7.1: Add Cron Job

**Step 1: Add to crontab**

```bash
crontab -e
```

Add line:
```
0 8 * * 6 cd /home/ags/knowledge-system && python3 scripts/weekly_analytics_export.py >> /var/log/analytics-export.log 2>&1
```

**Step 2: Verify cron is set**

```bash
crontab -l | grep analytics
```

---

### Task 7.2: Run First Export and Verify

**Step 1: Run manually**

```bash
python scripts/weekly_analytics_export.py
```

**Step 2: Check output**

```bash
ls -la analytics/
cat analytics/weekly-*.json | python -m json.tool | head -50
```

**Step 3: Commit any final changes**

```bash
git add .
git commit -m "feat: complete usage analytics implementation"
```

---

## Verification Checklist

After all phases complete:

- [ ] Each service has `events` table in SQLite
- [ ] `shared/events.py` exists and is importable
- [ ] Kasten logs: `note_created`, `note_viewed`, `entry_point_used`, `random_note_used`, `source_viewed`
- [ ] Canvas logs: `quote_received`, `note_sent_to_kasten`, workspace events
- [ ] Bookmark Manager logs: `bookmark_created`, `bookmark_processed`, `bookmark_expired`, RSS events
- [ ] Balance logs: feature events (stats, settings, meditation, exercise, pulse)
- [ ] All services have POST /api/events endpoint
- [ ] All templates include analytics.js
- [ ] Weekly export script runs and produces valid JSON
- [ ] Cron job is scheduled for Saturday 8am

---

## Saturday Ritual (Week 1+)

1. Open Claude Code
2. Say: "Read analytics/weekly-YYYY-MM-DD.json and generate the weekly usage report"
3. Review report sections: targets, effectiveness, correlations, feature health
4. Decide what to change
5. Implement changes
6. Repeat next Saturday
