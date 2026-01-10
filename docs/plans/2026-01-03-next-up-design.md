# Next Up - Task Capture for Balance

A minimal todo inbox built into Balance for capturing tasks where you do focused work.

## Problem

- Ideas pop up mid-session that would derail focus
- Need to capture fleeting thoughts without breaking flow
- Want visibility into what's due without a complex task manager
- Need constraint to avoid backlog accumulation

## Solution

**Next Up** - A unified list of max 5 items visible on Balance home screen.

### Core Behavior

- **Max 5 items** - Hard limit. Forces processing.
- **No states** - Items exist or they don't. Delete = done.
- **Quick capture** - Input always visible, type and enter.
- **Optional due date** - Add when ready to commit.
- **Optional priority link** - Connect to ongoing priority if relevant.
- **Sorted by date** - Dated items first (ascending), then undated by created_at.

### What It's NOT

- Not a task manager (no projects, tags, recurring tasks)
- Not an archive (no "completed" history)
- Not synced anywhere (stays in Balance)

## Data Model

```sql
NextUp
├── id: int
├── text: string
├── due_date: date | null
├── priority_id: FK to Priorities | null
├── created_at: timestamp
└── position: int (for manual reorder if needed)

Sessions (existing, add column)
├── ... existing fields ...
└── next_up_id: FK to NextUp | null
```

**Constraint:** Max 5 rows in table. Insert fails if already 5 items.

## Session Integration

**Expected sessions require task selection:**

1. User taps "Expected"
2. Must select a task from Next Up list
3. Task text becomes session intention
4. Session logs with `next_up_id` foreign key

**Personal sessions remain free-form** - no task required.

**Session history per task:** Edit screen shows "2 sessions · 50 min total"

## UI

### Home Screen

```
┌─────────────────────────────────┐
│ + Add task...                   │
│ Press Enter · 2 slots left      │
├─────────────────────────────────┤
│ NEXT UP                         │
│ ┌─────────────────────────────┐ │
│ │ Do taxes           Jan 7  ✕ │ │
│ │ Deploy X     Work · Jan 8 ✕ │ │
│ │ Chapter 3   Thesis· Jan 10✕ │ │
│ │ 4. empty slot               │ │
│ │ 5. empty slot               │ │
│ └─────────────────────────────┘ │
│                                 │
│ [Expected] [Personal]           │
│ Select task to start Expected   │
│ [Start Session] (disabled)      │
└─────────────────────────────────┘
```

### Timer Screen (Mini Capture)

```
┌─────────────────────────────────┐
│         EXPECTED · WORK         │
│            21:34                │
│         Deploy feature X        │
│                                 │
│    + Quick capture...           │
│    Thought? Capture it, stay    │
│    focused.                     │
│                                 │
│        [Abandon session]        │
└─────────────────────────────────┘
```

### Edit Task Screen

- Text (required)
- Due date (optional)
- Priority link (optional dropdown)
- Session history ("2 sessions · 50 min")
- Delete button

## Components Used

All from existing shared library:

| Need | Component |
|------|-----------|
| Task list | `.priority-list` (no arrows, dates instead of rank) |
| Capture input | `.input` |
| Toggle | `.btn--option` |
| Priority dropdown | `.dropdown` |
| Section header | `.view-header` |

**No new components required.**

## API Endpoints

```
GET  /api/nextup              # List all (max 5)
POST /api/nextup              # Create (fails if 5 exist)
PUT  /api/nextup/{id}         # Update text, date, priority
DELETE /api/nextup/{id}       # Remove

# Session start updated to accept next_up_id
POST /api/sessions/start      # Add next_up_id field for Expected
```

## Constraints as Features

| Constraint | Why |
|------------|-----|
| Max 5 items | Forces Pareto - only 5 things can be "next" |
| No states | Simplicity - exists or gone |
| Delete only | No "done" state to manage |
| Expected requires task | No vague work |
| Visible empty slots | Shows capacity, creates pressure to use or fill |

## Future Considerations (Not Now)

- Drag to reorder within dated/undated groups
- "Promote to priority" action
- Due date reminders (probably not - goes against Balance philosophy)

## Mockup

Available at `/mockup` in Balance dev mode. Screens:
- Home + Next Up
- Timer (with capture)
- Edit Task
