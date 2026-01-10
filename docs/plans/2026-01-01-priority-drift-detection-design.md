# Priority Drift Detection — Design

Extends Balance with priority tracking for Expected sessions, enabling drift detection between stated priorities and actual time allocation.

## Problem

"My biggest thing currently is to catch up at work and start seriously learning for my exams and then start my thesis — but instead I have more fun working on the knowledge system."

Balance tracks Expected vs Personal sessions, but doesn't know *what* Expected work is being done. Without priority context, it can't surface when behavior drifts from stated goals.

## Solution

1. **Priority list** — Define 2-4 ranked priorities in Settings
2. **Priority tagging** — Expected sessions must select a priority
3. **Drift insight** — Stats shows biggest misalignment with pattern context

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Priority storage | Fixed list in settings | Forces explicit declaration of what matters |
| Personal sessions | No priority tagging | Personal = curiosity-driven, not goal-aligned |
| Insight format | Single biggest drift | "Tell me where my biggest problem is" — not a dashboard |
| Pattern context | Show weeks of drift | "This is week 3 of Thesis being deprioritized" |
| Suggestions | None | Show the problem, don't prescribe solutions |

## Data Model

### New Table: Priorities

```sql
CREATE TABLE priorities (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    rank INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    archived_at TEXT
);
```

### New Table: Priority Changes (for tracking)

```sql
CREATE TABLE priority_changes (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,  -- 'added', 'removed', 'reordered'
    priority_name TEXT NOT NULL,
    old_rank INTEGER,
    new_rank INTEGER
);
```

### Sessions Table Change

```sql
ALTER TABLE sessions ADD COLUMN priority_id INTEGER REFERENCES priorities(id);
```

Only populated for `type = 'expected'`. Personal sessions have `priority_id = NULL`.

## API Endpoints

```
# Priorities
GET  /api/priorities              → [{id, name, rank, session_count}, ...]
POST /api/priorities              {name} → creates at lowest rank
PUT  /api/priorities/reorder      {order: [id, id, id]} → updates ranks
DELETE /api/priorities/:id        → archives (if has sessions) or deletes

# Stats (extended)
GET  /api/stats/drift             → {biggest_drift, weeks_drifting, breakdown}
```

## UI Changes

### Timer Page — Start Session Flow

**Current flow:**
```
[Expected] [Personal] → intention input → Start
```

**New flow for Expected:**
```
[Expected] [Personal]
       ↓
[Expected selected]
       ↓
Priority dropdown appears:
┌─────────────────────────┐
│ Select priority...    ▾ │
└─────────────────────────┘
       ↓
┌─────────────────────────┐
│ Thesis              #1  │
│ Work catchup        #2  │
│ Exams               #3  │
└─────────────────────────┘
       ↓
[Priority selected]
       ↓
Intention input (optional) → Start
```

**Implementation:**
- Add priority dropdown below type selection (uses shared `.dropdown` component)
- Dropdown only visible when Expected is selected
- Start button disabled until priority selected
- Intention field becomes optional when priority provides context

### Settings Page — Priorities Section

Add new section above existing timer settings:

```
┌─────────────────────────────────────────┐
│ PRIORITIES                              │
│                                         │
│ Use arrows to reorder.                  │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ 1  Thesis           2 sessions  ▲▼ │ │
│ │ 2  Work catchup     1 session   ▲▼ │ │
│ │ 3  Knowledge-system 8 sessions  ▲▼ │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [+ Add Priority]                        │
│ Max 4 priorities                        │
└─────────────────────────────────────────┘
```

**Implementation:**
- Uses shared `.priority-list` component with arrow reorder
- Session count shows all-time for that priority
- Add button opens inline input (not modal)
- Archive action available via long-press or secondary menu

### Stats Page — Drift Alert

Add drift alert section above existing stats:

```
┌─────────────────────────────────────────┐
│ BIGGEST DRIFT                           │
│                                         │
│ Thesis is priority #1 but got [2]       │
│ sessions. Knowledge-system (priority    │
│ #3) got [8].                            │
│                                         │
│ ─────────────────────────────────────── │
│ This is week 3 of Thesis being          │
│ deprioritized.                          │
└─────────────────────────────────────────┘
```

**Below existing stats, add priority breakdown:**

```
EXPECTED SESSIONS BY PRIORITY

#1  Thesis           ████░░░░░░  18%
#2  Work catchup     ██░░░░░░░░   9%
#3  Knowledge-system ████████░░  73%
```

**Implementation:**
- Drift alert uses new `.drift-alert` component (add to shared library)
- Only shows if there's meaningful drift (>20% misalignment from rank order)
- Weeks count tracks consecutive weeks where #1 priority isn't #1 in sessions
- Breakdown uses horizontal bars showing percentage of Expected sessions

## Components to Add

### Drift Alert (shared component)

```css
.drift-alert { border: 2px solid var(--color-border); padding: 1.5rem; }
.drift-alert__header { font-size: var(--font-size-xs); text-transform: uppercase; }
.drift-alert__main { font-size: var(--font-size-lg); line-height: 1.5; }
.drift-alert__context { font-size: var(--font-size-sm); color: var(--color-muted); }
.drift-alert__stat { display: inline-block; padding: 0.25rem 0.5rem; border: 1px solid; }
```

### Already Added

- `.priority-list` — Reorderable list with up/down arrows
- `.dropdown__item--with-meta` — Dropdown items with secondary info

## Migration

For existing sessions without `priority_id`:
- Leave as NULL (they predate priority tracking)
- Stats calculations exclude sessions without priority_id from drift analysis
- Or: Add "Uncategorized" virtual priority for historical data

## Edge Cases

| Case | Behavior |
|------|----------|
| No priorities defined | Hide priority dropdown, Expected sessions work as before |
| Only 1 priority | No drift possible, hide drift alert |
| All sessions are Personal | Show "No Expected sessions this week" in stats |
| Priority archived mid-week | Continue showing in stats, just can't select for new sessions |
| Priority deleted | Only allowed if zero sessions attached |

## Mockup Reference

Live mockup at `/mockup` route in Balance app shows:
- Stats cockpit with drift alert
- Start session with priority dropdown
- Settings with priority list

## Implementation Order

1. Database schema (priorities table, sessions.priority_id)
2. API endpoints for priorities CRUD
3. Settings page — priority list management
4. Timer page — priority dropdown for Expected
5. Stats page — drift calculation and display
6. Drift alert component (move to shared library)

## Non-Goals

- No priority suggestions ("you should work on Thesis")
- No notifications when drifting
- No goal-setting features (just tracking)
- No time-based priority scheduling
