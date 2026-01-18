# Train UI Redesign

**Date:** 2026-01-18  
**Status:** Approved  
**Goal:** Mobile-first workout logging with plan-driven exercises, quick set entry, and progression tracking

## Problem

Current Train UI is a non-functional prototype:
- Start Workout button does nothing
- No integration with new API endpoints (`/api/context`, `/api/sessions`, `/api/sets`)
- Custom CSS instead of shared components
- No pre-filled exercises from plan
- No progression graphs

## Design

### App Structure

Three tabs via bottom nav:
- **Today** - workout mode (idle → active → done)
- **History** - exercise progression graphs
- **Plan** - rendered markdown plan

```
┌─────────────────────────────────┐
│         [CONTENT]               │
├─────────────────────────────────┤
│   TODAY  │  HISTORY  │  PLAN    │
└─────────────────────────────────┘
```

### Today Tab - Idle State

Shows today's workout template from plan with last logged values per exercise.

```
┌─────────────────────────────────┐
│  PUSH DAY                       │
│  Week 1 · Last: 2 days ago      │
├─────────────────────────────────┤
│  ┌─────────────────────────┐    │
│  │ Barbell Bench Press     │    │
│  │ Last: 55kg × 6 @ RIR 2  │    │
│  └─────────────────────────┘    │
│  ┌─────────────────────────┐    │
│  │ Incline DB Press        │    │
│  │ Last: 17.5kg × 8 @ RIR 2│    │
│  └─────────────────────────┘    │
│  ┌─────────────────────────┐    │
│  │ Cable Flyes             │    │
│  │ Last: 10kg × 12 @ RIR 0 │    │
│  └─────────────────────────┘    │
│           ...                   │
├─────────────────────────────────┤
│      [ START WORKOUT ]          │
├─────────────────────────────────┤
│   TODAY  │  HISTORY  │  PLAN    │
└─────────────────────────────────┘
```

**Data source:** Parse plan markdown for today's template, fetch last sets via `/api/sets`

### Today Tab - Active Workout

Free list navigation - tap any exercise to expand and log.

```
┌─────────────────────────────────┐
│  PUSH · 4/16 sets               │
├─────────────────────────────────┤
│  ┌─────────────────────────┐    │
│  │ ✓ Barbell Bench (4/4)   │    │
│  └─────────────────────────┘    │
│  ┌─────────────────────────┐    │
│  │ ▶ Incline DB Press      │    │
│  │   Last: 17.5kg × 8      │    │
│  │                         │    │
│  │   [17.5] kg [8] reps [2]│    │
│  │                         │    │
│  │   [ LOG SET ]           │    │
│  │                         │    │
│  │   Sets: 20×6, 17.5×8    │    │
│  │                         │    │
│  │   Notes: ___________    │    │
│  └─────────────────────────┘    │
│  ┌─────────────────────────┐    │
│  │ ○ Cable Flyes (0/3)     │    │
│  │   Last: 10kg × 12       │    │
│  └─────────────────────────┘    │
│           ...                   │
├─────────────────────────────────┤
│      [ END WORKOUT ]            │
├─────────────────────────────────┤
│   TODAY  │  HISTORY  │  PLAN    │
└─────────────────────────────────┘
```

**Features:**
- Sticky header with session progress (sets logged / total)
- Tap any exercise to expand
- Pre-filled inputs from last logged set (adjust + tap to log)
- Shows sets logged this session
- Note field always visible when expanded
- End Workout button (danger style)

**API calls:**
- `POST /api/sessions/start` on Start Workout
- `POST /api/sets` on Log Set
- `POST /api/sessions/end` on End Workout

### History Tab

Exercise progression graphs - focus on trends, not individual sessions.

```
┌─────────────────────────────────┐
│  HISTORY                        │
├─────────────────────────────────┤
│  ┌─────────────────────────┐    │
│  │ Barbell Bench Press   ▼ │    │
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │ ▲                       │    │
│  │ 57.5 ─ ─ ─ ─ ─ ─ ─ ●    │    │
│  │ 55   ─ ─ ─ ● ● ● ●      │    │
│  │ 52.5 ─ ● ●              │    │
│  │ 50   ●                  │    │
│  │      ├─┼─┼─┼─┼─┼─┼─►    │    │
│  │      W1  W2  W3  W4     │    │
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │ Best: 55kg × 6          │    │
│  │ Trend: +5kg in 4 weeks  │    │
│  │ Volume: 16 sets total   │    │
│  └─────────────────────────┘    │
│                                 │
│  Recent sets:                   │
│  Jan 17: 55×6, 55×6, 55×6, 55×6│
│  Jan 13: 52.5×6, 52.5×7...     │
│                                 │
├─────────────────────────────────┤
│   TODAY  │  HISTORY  │  PLAN    │
└─────────────────────────────────┘
```

**Features:**
- Dropdown to select exercise
- Line graph showing weight progression over weeks
- Stats: best set, trend, total volume
- Recent sets for reference

**API calls:**
- `GET /api/sets` with exercise filter
- `GET /api/sessions` for date grouping

### Plan Tab

Rendered markdown plan using shared `.markdown-content` component.

```
┌─────────────────────────────────┐
│  PLAN                           │
├─────────────────────────────────┤
│                                 │
│  # Upper-Body Hypertrophy       │
│                                 │
│  **Goal:** Hypertrophy          │
│  **Duration:** 6 weeks          │
│                                 │
│  ## Day A - Push                │
│                                 │
│  | Exercise     | Sets | Reps | │
│  |--------------|------|------| │
│  | Bench Press  | 4    | 6-10 | │
│  | Incline DB   | 3    | 8-12 | │
│  | Cable Flyes  | 3    | 12-15| │
│  | ...          |      |      | │
│                                 │
│  ## Day B - Pull                │
│  ...                            │
│                                 │
├─────────────────────────────────┤
│   TODAY  │  HISTORY  │  PLAN    │
└─────────────────────────────────┘
```

**API calls:**
- `GET /api/context` → `plan.markdown`

## New Shared Components

### 1. `.markdown-content`

Styled container for rendered markdown content. Move from bookmark-manager's `.source-content`.

```css
.markdown-content {
    background: var(--color-bg);
    padding: var(--space-md);
    border: 2px solid var(--color-border);
    font-size: var(--font-size-base);
    line-height: 1.6;
    overflow-y: auto;
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3 {
    margin-top: var(--space-lg);
    margin-bottom: var(--space-sm);
}

.markdown-content table {
    width: 100%;
    border-collapse: collapse;
    margin: var(--space-md) 0;
}

.markdown-content th,
.markdown-content td {
    border: 1px solid var(--color-border);
    padding: var(--space-sm);
    text-align: left;
}

.markdown-content ul,
.markdown-content ol {
    padding-left: var(--space-lg);
    margin: var(--space-sm) 0;
}
```

### 2. `.chart` / `.chart--line`

Simple SVG line chart for progression graphs. Brutalist style: black lines, no fills, monospace labels.

```css
.chart {
    width: 100%;
    height: 200px;
    border: 2px solid var(--color-border);
    padding: var(--space-sm);
}

.chart__line {
    fill: none;
    stroke: var(--color-text);
    stroke-width: 2;
}

.chart__point {
    fill: var(--color-text);
}

.chart__axis {
    stroke: var(--color-border);
    stroke-width: 1;
}

.chart__label {
    font-family: var(--font-mono);
    font-size: var(--font-size-xs);
    fill: var(--color-muted);
}
```

JavaScript helper in `shared/js/components.js`:
```javascript
function renderLineChart(container, data, options) {
    // data: [{x: date, y: weight}, ...]
    // Generates SVG with line, points, axes, labels
}
```

## Existing Components Used

| Component | Usage |
|-----------|-------|
| `{{ ui.bottom_nav() }}` | Three-tab navigation |
| `{{ ui.card() }}` | Exercise rows (collapsible) |
| `{{ ui.button() }}` | Start Workout, Log Set, End Workout |
| `{{ ui.input() }}` | Weight, reps, RIR inputs |
| `{{ ui.textarea() }}` | Exercise notes |
| `{{ ui.dropdown() }}` | Exercise selector in History |
| `.action-panel` | Fixed bottom button area |

## Data Flow

### Today Tab
1. Load: `GET /api/context` → parse plan for today's template
2. Load: `GET /api/sets?since=30d` → get last logged per exercise
3. Start: `POST /api/sessions/start` with `plan_id`
4. Log: `POST /api/sets` with pre-filled values
5. End: `POST /api/sessions/end` with notes

### History Tab
1. Load: `GET /api/sets` → group by exercise
2. Select: Filter sets for selected exercise
3. Render: Chart + stats + recent sets

### Plan Tab
1. Load: `GET /api/context` → `plan.markdown`
2. Render: Markdown → HTML via server or JS

## API Changes Needed

### New endpoint: `GET /api/exercises`
Return list of exercises with last logged set:
```json
[
    {
        "name": "Barbell Bench Press",
        "last_set": {"weight": 55, "reps": 6, "rir": 2, "date": "2026-01-17"},
        "total_sets": 16
    }
]
```

### Extend: `GET /api/sets`
Add `exercise_name` filter:
```
GET /api/sets?exercise_name=Barbell+Bench+Press
```

## Mobile Considerations

- Bottom nav only (header hidden on mobile)
- Touch targets minimum 48px
- Pre-filled inputs reduce typing
- One-tap log set
- Expandable cards for exercise detail
- Fixed action panel for primary actions

## Out of Scope

- Offline support (future)
- Exercise autocomplete (uses plan exercises only)
- Custom exercise additions during workout
- Volume vs target comparison (future iteration)
