# Session Paste Feature Design

**Date:** 2026-01-14
**Status:** Approved

## Problem

Current session logging requires structured data entry (exercise, sets, reps, weight). Users log sessions via WhatsApp assistant which produces summaries like:

```
BENCH PRESS (2026-01-12)
- Set 1: 2 reps × 70kg
- Set 2: 4 reps × 42.5kg
- Set 3: 6 reps × 42.5kg
- Set 4: 4 reps × 42.5kg (note: could've done ~5 reps)

PULLUPS
- Set 1: 8 reps × bodyweight
- Set 2: 4.5 reps × bodyweight (more fatigued, need longer rest)
```

These summaries contain valuable context notes that structured logging loses.

## Solution

Replace structured logging with raw text storage. Paste WhatsApp summary, save, done.

## Data Model

New table replacing `Session`/`SetEntry`:

```python
class SessionLog(Base):
    __tablename__ = "session_logs"

    id = Column(Integer, primary_key=True)
    session_date = Column(Date, nullable=False)
    raw_text = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
```

## API

### POST /api/sessions/log

Log a new session from pasted text.

```json
// Request
{
  "text": "BENCH PRESS (2026-01-12)\n...",
  "date": "2026-01-12"  // Optional override
}

// Response
{
  "id": 1,
  "session_date": "2026-01-12",
  "created_at": "2026-01-14T18:30:00"
}
```

### GET /api/context

Returns plan and all session logs for workflow assistant.

```json
{
  "plan": {
    "id": 2,
    "title": "Upper-Body Hypertrophy + Running",
    "markdown": "..."
  },
  "sessions": [
    {
      "id": 1,
      "date": "2026-01-12",
      "text": "BENCH PRESS (2026-01-12)\n..."
    }
  ]
}
```

Sessions sorted newest-first.

## UI

Log page (`/log`):

```
┌─────────────────────────────────────────┐
│  Log Session                            │
│  ┌───────────────────────────────────┐  │
│  │ [textarea - paste WhatsApp here]  │  │
│  └───────────────────────────────────┘  │
│                                         │
│  Date: [2026-01-12] (auto-detected)     │
│                                         │
│  [Save Session]                         │
│                                         │
│  ─────────────────────────────────────  │
│  Recent Sessions                        │
│  • 2026-01-12 - BENCH PRESS, PULLUPS   │
│  • 2026-01-10 - SQUATS, RDL            │
└─────────────────────────────────────────┘
```

**Behavior:**
- Paste text into textarea
- Date auto-parsed from first `(YYYY-MM-DD)` pattern
- Date editable via input field before save
- Falls back to today if no date found
- Recent sessions list shows date + first exercise names

## Date Parsing

```python
import re
from datetime import date

def parse_session_date(text: str) -> date:
    match = re.search(r'\((\d{4}-\d{2}-\d{2})\)', text)
    if match:
        return date.fromisoformat(match.group(1))
    return date.today()
```

## Migration

- Keep existing `Session`, `SetEntry`, `Exercise` tables (unused but preserved)
- New `SessionLog` table for all new logs
- Context endpoint returns from `SessionLog` only

## Implementation Tasks

1. Add `SessionLog` model to `models.py`
2. Create migration to add `session_logs` table
3. Add `POST /api/sessions/log` endpoint
4. Update `GET /api/context` to return session logs
5. Update `/log` UI with textarea and date picker
6. Add recent sessions list to log page
