# System-Wide Analytics Design

Usage analytics across all knowledge system services to identify what features are actually used and track the knowledge funnel.

## Philosophy

> "CIA yourself" — Full surveillance of your own system usage, analyzed weekly with Python (no mental math), to find dead features and optimize the knowledge flow.

**Principles:**
1. **Per-service events tables** — Each service owns its data
2. **API-based export** — Services expose `/api/events`, script aggregates
3. **Target-centric** — Core metric is notes in Kasten
4. **Python analysis** — All calculations via code, no mental math from Claude
5. **Weekly ritual** — Saturday export + analysis session

---

## Architecture

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Bookmark Manager│  │     Canvas      │  │     Kasten      │  │     Balance     │
│   events table  │  │   events table  │  │   events table  │  │   events table  │
│  GET /api/events│  │  GET /api/events│  │  GET /api/events│  │  GET /api/events│
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │                    │
         └────────────────────┴────────────────────┴────────────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────┐
                        │  weekly_analytics_export │
                        │     (Python script)      │
                        └──────────────┬───────────┘
                                       │
                                       ▼
                        ┌──────────────────────────┐
                        │ analytics/weekly-DATE.json│
                        └──────────────┬───────────┘
                                       │
                                       ▼
                        ┌──────────────────────────┐
                        │  Saturday Analysis with  │
                        │  Claude + Python scripts │
                        └──────────────────────────┘
```

---

## Data Model

### Events Table (identical in all 4 services)

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    event_type TEXT NOT NULL,  -- 'funnel' | 'feature'
    name TEXT NOT NULL,        -- e.g., 'bookmark_created', 'rss_subscribe'
    metadata TEXT              -- JSON blob for context
);

CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_name ON events(name);
```

### Shared Helper

```python
# shared/events.py
import json
from datetime import datetime

async def log_event(db, event_type: str, name: str, metadata: dict = None):
    await db.execute(
        "INSERT INTO events (timestamp, event_type, name, metadata) VALUES (?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), event_type, name,
         json.dumps(metadata) if metadata else None)
    )
    await db.commit()
```

---

## Events to Track

### Funnel Events (Knowledge Flow)

**Bookmark Manager:**
| Event | When | Metadata |
|-------|------|----------|
| `bookmark_created` | URL saved | `{source: "telegram/rss/manual", is_thesis, is_pinned}` |
| `bookmark_expired` | Auto-deleted after 7 days | `{days_in_inbox, was_viewed}` |
| `quote_pushed` | Quote sent to Canvas | `{bookmark_id, quote_length}` |

**Canvas:**
| Event | When | Metadata |
|-------|------|----------|
| `quote_received` | Quote arrives from BM | `{bookmark_id}` |
| `note_sent_to_kasten` | Note created in Kasten | `{note_id, has_parent, source_id}` |

**Kasten:**
| Event | When | Metadata |
|-------|------|----------|
| `note_created` | New note saved | `{note_id, parent_id, source_id, link_count}` |
| `link_followed` | Wiki link clicked | `{from_note, to_note}` |

### Feature Events (Usage Tracking)

**Bookmark Manager:**
| Event | Feature |
|-------|---------|
| `rss_subscribe` | Added a feed |
| `rss_unsubscribe` | Removed a feed |
| `feed_item_promoted` | RSS item → bookmark |
| `retry_scrape` | Re-scrape clicked |
| `move_to_pins` | Bookmark pinned |
| `move_to_thesis` | Marked as thesis |
| `zotero_sync` | Sync triggered |
| `backup_created` | Manual backup |

**Canvas:**
| Event | Feature |
|-------|---------|
| `draft_edited` | Draft saved (debounced) |
| `workspace_note_added` | Note added to graph |
| `workspace_connection_created` | Edge created |
| `parent_selected` | Parent picker used |
| `parent_skipped` | Parent picker dismissed |

**Kasten:**
| Event | Feature |
|-------|---------|
| `entry_point_used` | Started from entry point |
| `random_note_used` | "Feeling lucky" clicked |
| `source_viewed` | Source detail opened |
| `reindex_triggered` | Manual reindex |

**Balance:**
| Event | Feature |
|-------|---------|
| `youtube_session_started` | YouTube gatekeeper used |
| `nextup_created` | Task added to Next Up |
| `nextup_completed` | Task picked for session |

---

## API Endpoint

Each service exposes:

```
GET /api/events?since=2026-01-01T00:00:00
```

Response:
```json
{
  "service": "bookmark-manager",
  "events": [
    {
      "timestamp": "2026-01-03T14:30:00",
      "event_type": "funnel",
      "name": "bookmark_created",
      "metadata": {"source": "telegram", "is_thesis": false}
    }
  ]
}
```

Implementation (~15 lines per service):

```python
@router.get("/events")
async def get_events(since: str = None):
    query = "SELECT * FROM events"
    params = ()
    if since:
        query += " WHERE timestamp > ?"
        params = (since,)
    async with get_db() as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return {
            "service": SERVICE_NAME,
            "events": [dict(r) for r in rows]
        }
```

---

## Weekly Export Script

```python
# scripts/weekly_analytics_export.py
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

def export_weekly():
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()

    all_events = []
    for service, url in SERVICES.items():
        resp = httpx.get(f"{url}?since={week_ago}")
        data = resp.json()
        for e in data['events']:
            e['service'] = service
            all_events.append(e)

    all_events.sort(key=lambda e: e['timestamp'])

    output = {
        'period': {'start': week_ago, 'end': datetime.now().isoformat()},
        'events': all_events
    }

    Path('analytics').mkdir(exist_ok=True)
    outfile = f"analytics/weekly-{datetime.now():%Y-%m-%d}.json"
    Path(outfile).write_text(json.dumps(output, indent=2))
    print(f"Exported to {outfile}")
    return outfile

if __name__ == '__main__':
    export_weekly()
```

---

## Saturday Ritual

### 1. Export
```bash
python scripts/weekly_analytics_export.py
```

Or via cron (Saturday 8am):
```bash
0 8 * * 6 cd /home/ags/knowledge-system && python scripts/weekly_analytics_export.py
```

### 2. Analysis with Claude

Share `analytics/weekly-YYYY-MM-DD.json` and work together:

**Claude writes Python scripts to calculate:**
- Funnel conversion: bookmarks → quotes → notes
- Decay rate: expired / created
- Feature usage counts per service
- Dead features (0 usage)
- Time patterns (hour/day heatmaps)

**Together brainstorm:**
- Why certain features aren't used
- What friction exists in the funnel
- What to remove or simplify

### 3. Iterate
Based on analysis:
- Remove dead features
- Simplify friction points
- Adjust system design

---

## Calculated Metrics (via Python)

### Funnel Metrics
| Metric | Calculation |
|--------|-------------|
| Conversion rate | notes created / bookmarks created |
| Decay rate | bookmarks expired / bookmarks created |
| Quote usage | notes with source / quotes received |
| Connection rate | notes with links / total notes |

### Feature Health
| Signal | Query |
|--------|-------|
| Dead features | Events with 0 occurrences in 30 days |
| Declining features | Week-over-week drop > 50% |
| Never used | Features with 0 events ever |

### Time Patterns
| Pattern | Query |
|---------|-------|
| Peak hours | GROUP BY hour(timestamp), COUNT(*) |
| Active days | GROUP BY weekday, COUNT(*) |
| Service distribution | GROUP BY service, COUNT(*) |

---

## Implementation Plan

### Phase 1: Infrastructure
1. Add `events` table migration to all 4 services
2. Create `shared/events.py` helper
3. Add `GET /api/events` endpoint to all 4 services

### Phase 2: Instrument Services
4. Bookmark Manager: funnel + feature events
5. Canvas: funnel + feature events
6. Kasten: funnel + feature events
7. Balance: feature events (sessions already tracked)

### Phase 3: Export & Ritual
8. Create `scripts/weekly_analytics_export.py`
9. Test full flow
10. Set up Saturday cron
11. First analysis session

---

## Success Criteria

After 4 weeks:
1. **Data flowing** — All services logging events
2. **Dead features identified** — At least 2 features flagged for removal
3. **Funnel measured** — Know your bookmark → note conversion rate
4. **Habit formed** — Saturday analysis is automatic
