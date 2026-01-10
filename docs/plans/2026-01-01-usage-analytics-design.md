# Usage Analytics — Target-Centric Self-Surveillance

A lightweight analytics system to understand how you use your knowledge system, optimize for note production, and identify unnecessary features.

## Philosophy

> "CIA yourself" — collect everything about your own usage, analyze weekly, iterate the system.

**Principles:**
1. **Target-centric** — All metrics orient around the goal: connected notes in Kasten
2. **Lightweight** — SQLite events, not a heavy analytics platform
3. **Self-hosted** — Data never leaves the VPS
4. **Weekly ritual** — Saturday afternoon analysis with Claude, then iterate
5. **Subtract, don't add** — Use data to remove friction and dead features

---

## Targets

### Primary: Connected Notes
Notes in Kasten that link to other notes. Orphan notes are okay, but connected notes indicate real knowledge building.

### Secondary: Throughput
Bookmarks processed (triaged, read, decided on) — even if no note results. Processing is valuable; expiry without processing is waste.

### Quality Hierarchy

```
Connected Note     ████████████  Best — knowledge integrated
Orphan Note        ████████      Good — captured, not connected
Processed, no note ██████        Fine — read, decided not worth keeping
Expired unprocessed ██           Waste — friction or overload signal
```

---

## Data Model

### Central Events Table

Each service writes to its own `events` table with identical schema:

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),

    -- Classification
    event_type TEXT NOT NULL,  -- 'target' | 'feature' | 'navigation' | 'session'
    name TEXT NOT NULL,        -- e.g., 'note_created', 'rss_subscribe_clicked'

    -- Outcome tracking
    outcome TEXT,              -- 'completed' | 'abandoned' | null
    duration_ms INTEGER,       -- For timed actions

    -- Context
    metadata TEXT,             -- JSON blob for flexible data

    -- Indexing
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_type_name ON events(event_type, name);
```

### Metadata Schema by Event Type

**Target events:**
```json
{
  "note_created": {
    "note_id": "1230a",
    "source_bookmark_id": 456,
    "link_count": 3,
    "created_via": "canvas",
    "time_from_bookmark_ms": 86400000
  },
  "bookmark_processed": {
    "bookmark_id": 456,
    "outcome": "note_created",  // or "dismissed", "quote_only"
    "days_in_inbox": 3
  }
}
```

**Feature events:**
```json
{
  "feature_used": {
    "feature_id": "rss_subscribe",
    "from_page": "feeds",
    "completed": true
  }
}
```

**Navigation events:**
```json
{
  "page_view": {
    "page": "inbox",
    "referrer": "home",
    "time_on_page_ms": 45000
  }
}
```

---

## Events to Track

### Bookmark Manager

| Event Name | Type | When | Metadata |
|------------|------|------|----------|
| `bookmark_created` | target | URL saved | source (telegram/rss/manual), is_thesis, is_pinned |
| `bookmark_processed` | target | Moved/deleted/quote pushed | outcome, days_in_inbox |
| `bookmark_expired` | target | Auto-deleted by expiry | days_in_inbox, was_viewed |
| `quote_pushed` | target | Quote sent to Canvas | bookmark_id, quote_length |
| `page_view` | navigation | Page opened | page (inbox/pins/thesis/feeds), time_on_page |
| `rss_subscribe` | feature | Feed added | feed_url, completed |
| `rss_unsubscribe` | feature | Feed removed | feed_id |
| `feed_item_promoted` | feature | RSS item → bookmark | feed_id, item_id |
| `retry_scrape` | feature | Re-scrape triggered | bookmark_id, success |
| `move_to_pins` | feature | Bookmark pinned | bookmark_id |
| `move_to_thesis` | feature | Marked as thesis | bookmark_id |
| `zotero_sync` | feature | Zotero sync triggered | papers_synced |

### Canvas

| Event Name | Type | When | Metadata |
|------------|------|------|----------|
| `quote_received` | target | Quote arrives from BM | bookmark_id, quote_length |
| `draft_edited` | session | Draft content changed | char_count, edit_duration |
| `note_extracted` | target | Note parsed from draft | note_count, with_parent |
| `note_sent_to_kasten` | target | Note created in Kasten | note_id, source_bookmark_id |
| `page_view` | navigation | Page opened | page (draft/workspace) |
| `workspace_note_added` | feature | Note added to graph | note_id |
| `workspace_connection` | feature | Edge created | from_id, to_id, label |
| `parent_selected` | feature | Parent picker used | parent_id, search_used |
| `parent_skipped` | feature | Parent picker dismissed | - |

### Kasten

| Event Name | Type | When | Metadata |
|------------|------|------|----------|
| `note_created` | target | New note saved | note_id, parent_id, source_id, link_count |
| `note_viewed` | navigation | Note opened | note_id, from_note_id (if followed link) |
| `link_followed` | navigation | Wiki link clicked | from_note, to_note |
| `entry_point_used` | navigation | Started from entry point | note_id |
| `random_note_used` | feature | "Feeling lucky" clicked | landed_on |
| `source_viewed` | feature | Source detail opened | source_id |
| `reindex_triggered` | feature | Manual reindex | notes_indexed |

### Balance

| Event Name | Type | When | Metadata |
|------------|------|------|----------|
| `session_started` | session | Pomodoro begun | type (expected/personal), intention |
| `session_completed` | session | Pomodoro finished | duration, distractions, did_the_thing |
| `session_abandoned` | session | Pomodoro quit early | duration, reason |
| `break_started` | session | Break enforced | break_type (short/long) |
| `meditation_logged` | feature | Meditation recorded | duration, time_of_day |
| `exercise_logged` | feature | Exercise recorded | type, duration, intensity |
| `pulse_logged` | feature | Evening check-in | feeling, had_connection |
| `page_view` | navigation | Page opened | page (timer/stats/settings/log) |
| `stats_viewed` | feature | Analytics opened | period (week/month/compass) |
| `settings_changed` | feature | Limit modified | setting, old_value, new_value |

---

## Calculated Metrics

### Weekly Targets Report

| Metric | Calculation | Target |
|--------|-------------|--------|
| **Notes created** | COUNT(note_created) | ↑ trending |
| **Connected note rate** | notes with link_count > 0 / total notes | > 70% |
| **Conversion rate** | notes / bookmarks saved | > 20% |
| **Processing rate** | (processed + expired) / saved | 100% |
| **Decay rate** | expired / saved | < 30% |
| **Avg time to process** | AVG(processed_at - saved_at) | < 4 days |
| **Link density** | SUM(link_count) / COUNT(notes) | > 2 |

### Session Effectiveness Report (from Transcript Analysis)

| Metric | Calculation | Target |
|--------|-------------|--------|
| **Alignment rate** | aligned sessions / total analyzed | > 80% |
| **Drift rate** | drifted sessions / total analyzed | < 10% |
| **Focus rate** | focused scope / total analyzed | > 70% |
| **Tool appropriateness** | appropriate / (appropriate + questionable) | > 90% |
| **Red flag frequency** | sessions with red flags / total | < 20% |

### Cross-Correlation Insights

These combine transcript analysis with usage events:

| Pattern | Query | Insight |
|---------|-------|---------|
| **Drift → Output** | Sessions marked "drifted" vs notes created that day | Does drift kill productivity? |
| **Alignment → Notes** | Sessions marked "aligned" vs connected notes | Does focus produce quality? |
| **Scope creep → Features** | "expanded" sessions vs feature usage | What features enable creep? |
| **Rabbit hole → Kasten** | "rabbit_hole" sessions vs Kasten navigation | Exploration without capture? |
| **Claude overuse → Speed** | High prompt count vs time-to-process | Does Claude help or slow down? |
| **Red flags → Completion** | Sessions with red flags vs did_the_thing | Do warnings predict failure? |
| **Distractions → Alignment** | Distraction rating vs intention alignment | Are they correlated? |

### Feature Health Report

| Signal | Query | Action |
|--------|-------|--------|
| **Dead features** | Features with 0 events in 30 days | Remove candidate |
| **Abandoned features** | High click, low completion rate | Fix friction or remove |
| **One-time features** | Used exactly once ever | Remove candidate |
| **Declining features** | Week-over-week usage drop > 50% | Investigate |

### Behavioral Patterns

| Pattern | Query | Insight |
|---------|-------|---------|
| **Best note-creation time** | GROUP BY hour, COUNT(note_created) | When synthesis works |
| **Session type effectiveness** | notes created after expected vs personal | Which mode is productive |
| **Processing day** | GROUP BY weekday, COUNT(bookmark_processed) | When you triage |
| **Meditation → focus correlation** | JOIN meditation with session distractions | Does meditation help? |

---

## Implementation

### Per-Service Changes

Each service gets:

1. **events.py** — Event logging helper
```python
# services/shared/events.py
import json
from datetime import datetime
from aiosqlite import Connection

async def log_event(
    db: Connection,
    event_type: str,
    name: str,
    outcome: str = None,
    duration_ms: int = None,
    metadata: dict = None
):
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
```

2. **Migration** — Add events table to each service's SQLite database

3. **Instrumentation** — Add `log_event()` calls to endpoints and UI actions

### Frontend Tracking

For page views and durations, add a small JS snippet:

```javascript
// Track page view on load
const pageLoadTime = Date.now();
const currentPage = window.location.pathname;

// Send page view
fetch('/api/events', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    event_type: 'navigation',
    name: 'page_view',
    metadata: { page: currentPage }
  })
});

// Track time on page when leaving
window.addEventListener('beforeunload', () => {
  const duration = Date.now() - pageLoadTime;
  navigator.sendBeacon('/api/events', JSON.stringify({
    event_type: 'navigation',
    name: 'page_exit',
    duration_ms: duration,
    metadata: { page: currentPage }
  }));
});
```

### Weekly Export Script

```python
# scripts/weekly_analytics_export.py
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
        except sqlite3.OperationalError:
            # events table doesn't exist yet
            pass
        conn.close()

    # Export session analyses from Balance (transcript analysis results)
    balance_db = SERVICES['balance']
    if Path(balance_db).exists():
        conn = sqlite3.connect(balance_db)
        try:
            # Get session analyses
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

            # Get sessions with their outcomes
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
        except sqlite3.OperationalError:
            pass
        conn.close()

    # Sort events by timestamp
    export['events'].sort(key=lambda e: e['timestamp'])

    # Save for Claude analysis (in repo, gitignored)
    output_path = f'{BASE_PATH}/analytics/weekly-{datetime.utcnow().strftime("%Y-%m-%d")}.json'
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(export, f, indent=2)

    return output_path


if __name__ == '__main__':
    path = export_weekly_events()
    print(f"Exported to {path}")
```

---

## Saturday Ritual

### 1. Export (Automated)
Cron job runs Saturday morning:
```bash
0 8 * * 6 python /app/scripts/weekly_analytics_export.py
```

### 2. Analysis Session (With Claude)
Saturday afternoon, open Claude Code:

```
"Analyze this week's usage data and generate the weekly report"
```

Claude reads the JSON export and produces:

**Weekly Report Structure:**

1. **Target Progress**
   - Notes created (vs last week)
   - Connected note rate
   - Conversion funnel: bookmarks → quotes → notes
   - Processing speed trend
   - Link density trend

2. **Session Effectiveness** (from Transcript Analysis)
   - Alignment breakdown: aligned / pivoted / drifted
   - Scope breakdown: focused / expanded / rabbit_hole
   - Red flags detected this week
   - Tool appropriateness ratio
   - Worst session summary (most severe drift)

3. **Cross-Correlations**
   - Did aligned sessions produce more notes?
   - Did drift correlate with low output?
   - Meditation / exercise → focus correlation
   - Time of day patterns

4. **Feature Health**
   - Dead features (0 usage in 30 days)
   - Friction points (high abandon rate)
   - Most/least used features
   - Features only used during "drifted" sessions (enablers?)

5. **Recommendations**
   - Features to remove
   - Friction to address
   - Behavioral experiments to try next week
   - Settings to adjust (daily cap, etc.)

### 3. Iterate
Based on the report:
- Remove dead features
- Simplify high-friction flows
- Adjust settings/limits
- Update tracking if new questions emerge

---

## Privacy & Storage

- **All data stays on VPS** — No external analytics services
- **Retention:** Keep raw events for 90 days, aggregates forever
- **Cleanup cron:**
```sql
DELETE FROM events WHERE timestamp < datetime('now', '-90 days');
```

---

## Success Criteria

After 4 weeks of tracking:

1. **Clarity** — You know exactly which features you use
2. **Pruning** — At least 2 features removed as unnecessary
3. **Optimization** — Conversion rate (bookmark → note) improved
4. **Ritual** — Saturday analysis is a habit

---

## Implementation Plan

### Phase 1: Infrastructure (Day 1)

**1.1 Create shared events module**
- Create `shared/events.py` with `log_event()` async helper
- Handles SQLite writes with JSON metadata

**1.2 Add events table migration to all services**
- Add `events` table schema to each service's database init
- Bookmark Manager: `bookmark-manager/src/database.py`
- Canvas: `canvas/src/database.py`
- Kasten: `kasten/src/database.py`
- Balance: `balance/src/database.py`

**1.3 Create weekly export script**
- Create `scripts/weekly_analytics_export.py`
- Exports events + session_analyses + sessions to `analytics/weekly-YYYY-MM-DD.json`
- Add to cron: `0 8 * * 6` (Saturday 8am)

### Phase 2: Instrument Kasten (Day 2) — Closest to Target

**2.1 Backend events**
- `note_created` — POST /api/notes (with link_count, source_id)
- `note_viewed` — GET /api/notes/{id}
- `link_followed` — When clicked from another note
- `entry_point_used` — GET /api/notes/entry-points click
- `random_note_used` — Feeling lucky
- `source_viewed` — GET /api/sources/{id}

**2.2 Frontend tracking**
- Page view on load
- Time on page on exit

### Phase 3: Instrument Canvas (Day 3) — Synthesis Layer

**3.1 Backend events**
- `quote_received` — POST /api/quotes
- `draft_edited` — PUT /api/canvas (debounced, not every keystroke)
- `note_extracted` — When note parsed from draft
- `note_sent_to_kasten` — POST to Kasten API

**3.2 Feature events**
- `workspace_note_added`
- `workspace_connection_created`
- `parent_selected` / `parent_skipped`

### Phase 4: Instrument Bookmark Manager (Day 4) — Input Layer

**4.1 Target events**
- `bookmark_created` — POST /bookmarks (with source: telegram/rss/manual)
- `bookmark_processed` — When moved/deleted/quote pushed
- `bookmark_expired` — When auto-deleted by expiry job
- `quote_pushed` — POST /canvas/quotes

**4.2 Feature events**
- `rss_subscribe` / `rss_unsubscribe`
- `feed_item_promoted`
- `retry_scrape`
- `move_to_pins` / `move_to_thesis`
- `zotero_sync`

### Phase 5: Instrument Balance (Day 5) — Already Has Sessions

**5.1 Feature events** (sessions already tracked)
- `stats_viewed` — Which stats page opened
- `settings_changed` — Limit modifications
- `meditation_logged` / `exercise_logged` / `pulse_logged`

**5.2 Navigation events**
- Page views for timer/stats/settings/log

### Phase 6: Frontend Tracking (Day 6)

**6.1 Shared JS module**
- Create `shared/js/analytics.js`
- Page view tracking with referrer
- Time on page via `beforeunload`
- Beacon API for reliability

**6.2 Add to all service templates**
- Include in base templates
- Configure service name per template

### Phase 7: First Saturday Analysis (Day 7+)

**7.1 Run export**
```bash
python scripts/weekly_analytics_export.py
```

**7.2 Analyze with Claude**
```
Read analytics/weekly-2026-01-XX.json and generate the weekly report
```

**7.3 Iterate**
- Identify dead features
- Note friction points
- Plan changes for next week

---

## Open Questions

1. Should events be in a central database or per-service? (Current design: per-service for simplicity)
2. How to handle offline/failed event logging? (Probably: fire-and-forget, accept some loss)
3. Should we track Balance events separately since it's about work rhythm, not knowledge flow?
