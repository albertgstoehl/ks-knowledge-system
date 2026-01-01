# Balance — Personal Rhythm Tracker

A life compass disguised as a Pomodoro timer. Tracks focus, body, connection, and mood — oriented around your north star, not productivity metrics.

## Philosophy

> "It doesn't matter cosmically, and that's freeing. You're not optimizing for some objective truth. You're just building a life you enjoy living."

This app is not about maximizing output. It's a mirror that helps you see if you're drifting from the life you want. The tracking serves the life goal, not the other way around.

**Design principles:**
- **Identity-based, not outcome-based** — "You're building a practice" not "5/7 complete"
- **No shame** — "Welcome back" not "Streak broken"
- **Metrics serve the goal** — High focus + no connection = drifting away
- **Simple inputs, rich insights** — Few taps, but meaningful correlations
- **Hard constraints where needed** — Breaks are enforced, not suggested
- **Sometimes the best feature is the one you don't build** — Restraint over complexity

---

## Your North Star

The app centers around a user-defined life goal:

> Quality time with family and healthy relationships. Community. Being present. Not taking myself too seriously. Exploring the unexplored. Learning, solving problems, and having fun.

All analytics orient around this. The question isn't "how productive were you?" but "are you living aligned with what matters to you?"

---

## Data Model

### Core Tables

```
Sessions
├── id
├── type: 'expected' | 'personal'
├── intention: string (3 words max)
├── priority_id: int | null (FK to Priorities, for expected sessions)
├── started_at: timestamp
├── ended_at: timestamp | null
├── distractions: 'none' | 'some' | 'many'
├── did_the_thing: boolean
├── rabbit_hole: boolean | null
└── claude_used: boolean (for transcript analysis)

Priorities
├── id
├── name: string
├── rank: int (1 = highest priority)
├── created_at: timestamp
└── archived_at: timestamp | null

Meditation
├── id
├── logged_at: timestamp
├── occurred_at: timestamp | null (override if logged later)
├── time_of_day: 'morning' | 'afternoon' | 'evening' | null
└── duration_minutes: int

Exercise
├── id
├── logged_at: timestamp
├── type: 'cardio' | 'strength'
├── duration_minutes: int
└── intensity: 'light' | 'medium' | 'hard'

DailyPulse
├── id
├── date: date
├── feeling: 'heavy' | 'okay' | 'light'
├── had_connection: boolean
└── connection_type: 'friend' | 'family' | 'partner' | null
```

### Tracking Tables

```
SessionAnalyses (transcript analysis results)
├── id
├── session_id: FK to Sessions
├── analyzed_at: timestamp
├── intention_alignment: 'aligned' | 'pivoted' | 'drifted'
├── scope_behavior: 'focused' | 'expanded' | 'rabbit_hole'
├── red_flags: JSON array
├── one_line_summary: string
└── severity: 'none' | 'minor' | 'notable' | 'significant'

NudgeEvents
├── id
├── timestamp
├── type: 'daily_cap' | 'weekly_rest' | 'rabbit_hole' | 'holiday'
└── response: 'stopped' | 'continued'

LimitChanges
├── id
├── timestamp
├── setting: string
├── old_value
└── new_value

InsightEvents
├── id
├── shown_at: timestamp
├── insight_type: string
├── insight_text: string
├── acknowledged: boolean
└── followed: boolean | null

Settings
├── daily_cap: int (default 10)
├── hard_max: int (default 16)
├── evening_cutoff: time (default 19:00)
├── rabbit_hole_check: int (default 3)
└── weekly_rest_min: int (default 1)

AppState
├── break_until: timestamp | null
├── check_in_mode: boolean
└── north_star: text
```

---

## Features

### 1. Focus Sessions (Pomodoro)

**Timing:** 25 min work / 5 min break / 15 min every 4th break

**Session flow:**
1. Pick type: `[Expected]` `[Personal]`
   - Expected = external accountability (thesis, work, friend's project)
   - Personal = internal accountability (curiosity-driven)
2. Write intention (3 words max): "Fix API bug"
3. Timer runs (dark mode, minimal UI)
4. Session ends → Rate distractions: `[None]` `[Some]` `[Many]`
5. Did you do the thing? `[Yes]` `[No]`
6. Break enforced (hard lockout)

**Rabbit hole check:** After 3 consecutive Personal sessions, alert:
- "Still on original goal, or rabbit hole?"
- Options: `[Still on track]` `[Went down rabbit hole]` `[Take longer break]`

### 2. Break Enforcement

**Hard lockout.** During breaks:
- Balance app shows break screen with countdown
- Bookmark Manager, Canvas, Kasten are blocked via Traefik middleware
- No skip button. Must wait.

**Suggestions during break:**
- Look out a window
- Get water
- Stretch

### 3. Limits

| Limit | Type | Default | Behavior |
|-------|------|---------|----------|
| Daily cap | Soft | 10 | Nudge, can continue |
| Daily max | Hard | 16 | Lockout, no sessions |
| Evening cutoff | Hard | 19:00 | No new sessions after |
| Weekly rest | Soft | 1 day | Nudge if no rest days |

Limit changes are tracked. Analytics shows: "When daily cap was 8, mood averaged Light 65% of days."

### 4. Meditation Logging

**Inputs:**
- Duration (quick buttons: 5, 10, 15, 20 min)
- Time of day (auto-derived from timestamp, optional override)

**No friction:** Default is "now". One tap to log.

### 5. Exercise Logging

**Inputs:**
- Type: `[Cardio]` `[Strength]`
- Duration (quick buttons: 15, 30, 45, 60 min)
- Intensity: `[Light]` `[Medium]` `[Hard]`

### 6. Evening Check-in

**Once per day, pull-only (not pushed):**
1. How did today feel? `[Heavy]` `[Okay]` `[Light]`
2. Meaningful time with someone? `[Yes]` `[No]`
3. If yes, who? (optional): `[Friend]` `[Family]` `[Partner]`

**Naming rationale:**
- "Heavy/Okay/Light" instead of "Bad/Okay/Good"
- Non-judgmental — some days are heavy, that's not a failure
- Embodied — you feel weight in your chest, lightness in your step

---

## Analytics & Insights

### Notification Philosophy

**Zero push notifications.** The system watches silently. It only speaks when:
1. You're about to hurt yourself (overwork alerts, break enforcement)
2. You ask (open analytics)
3. Once a week (Sunday afternoon, pull-only digest)

### Priority Drift Detection

Stats page shows a single drift alert when behavior doesn't match stated priorities:

**Priority drift** (when priorities are imbalanced):
> **Thesis** is priority #1 but got **20%** of sessions. **Work** (#2) got **80%**.

**Personal drift** (when Personal > Expected):
> **Expected** got only **35%** of sessions. **Personal** got **65%**.

Hierarchy: Personal drift shown first (bigger issue), then priority drift.

### Weekly Digest (Pull-Only)

Available Sunday afternoon. One page showing:
- Summary: sessions, rest days, connection days
- Mood sparkline (7 bars, one per day)
- Breakdown: Expected/Personal ratio, did-the-thing rate
- **One insight** (not twelve): "On days you meditated, distractions were 40% lower"
- Patterns observed
- GitHub-style monthly activity grid

### Life Compass (All-Time View)

**North Star** at top — editable, always visible

**Six dimensions** with alignment indicators:
| Dimension | What it measures |
|-----------|------------------|
| Present | Meditation frequency + low-distraction sessions |
| Connected | Days with meaningful connection logged |
| Exploring | Personal sessions + intentional rabbit holes |
| Learning | Sessions completed + did-the-thing ratio |
| Light | Mood trend (inverse of Heavy days) |
| Rested | Rest days + respecting limits |

**Current signals:**
- Drift warnings: "Light-hearted is suffering. 9 Heavy days this month."
- Alignment signals: "Connected is strong. 18/28 days."

**Confirmed patterns** (with confidence %):
- Morning meditation → 40% fewer distractions (94% confidence, 23 observations)
- 3+ days no connection → Heavy mood increases (87%, 8 observations)
- Exercise → better focus next day (82%, 31 observations)
- Working weekends → Heavy within 3 days (78%, 6 observations)

**What works for you:**
- Leads to Light days: Morning meditation + connection + ≤8 sessions
- Leads to Heavy days: Isolation + weekend work + skipped exercise

**Your best weeks have:**
- At least 1 rest day
- 3+ morning meditations
- Connection logged 4+ days
- No weekend work
- Daily cap respected

### Pattern Detection

**Claude Agent SDK integration:** Weekly analysis job processes data to discover correlations. Patterns require 5+ observations before surfacing. Confidence increases with more data.

**Types of insights:**
- Correlations (X → Y relationships)
- Behavioral patterns (time-of-day, day-of-week)
- Limit effectiveness (how settings affect mood)
- Drift detection (isolation streaks, overwork patterns)
- Holiday suggestions ("5 weeks without a light week — consider rest")

---

## Spiral Protection

When someone is struggling, they stop logging. The system goes silent exactly when they need it most.

### Absence Detection

No activity for 3+ days → App shifts to **Check-in Mode**:
- No timer, no stats, no judgment
- Opens with: "Hey. No pressure. Just checking in."
- One question: "How are you?" `[Heavy]` `[Okay]` `[Light]`
- Response: "Noted. That's all for now."
- Option: "Switch to full mode"

### No Guilt UI

After absence:
- No "Streak broken" messages
- No "You missed X days"
- Just: "Welcome back."
- First week back has low expectations

### Pause Feature

Manual "Pause tracking" button. When used:
- "How long?" (1 week / 2 weeks / indefinite)
- "Reminder to check in?" (Yes / No)
- System respects pause, can gently ping later if requested

---

## Architecture

### New Service: `balance/`

```
bookmark-manager/  → bookmark.gstoehl.dev
canvas/            → canvas.gstoehl.dev
kasten/            → kasten.gstoehl.dev
balance/           → balance.gstoehl.dev  ← new
```

**Tech stack:** Python 3.11, FastAPI, SQLite, Jinja2, vanilla JS (same as other services)

### Break Enforcement via Traefik Middleware

```
┌─────────────────────────────────────────────────────┐
│                    TRAEFIK                          │
│  ┌───────────────────────────────────────────────┐  │
│  │   ForwardAuth Middleware → balance/api/check  │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
    bookmark        canvas         kasten
```

Every request to knowledge system services hits Balance first:
- `GET /api/check` → `{on_break: true/false, remaining_seconds: int}`
- If on break → redirect to break screen
- If not → pass through

### API Endpoints

```
# Timer
POST /api/sessions/start     {type, intention}
POST /api/sessions/end       {distractions, did_the_thing}
POST /api/sessions/abandon

# Break check (for Traefik middleware)
GET  /api/check              → {on_break, remaining_seconds}
GET  /api/can-start          → {allowed, reason}

# Logging
POST /api/meditation         {duration_minutes, time_of_day?}
POST /api/exercise           {type, duration_minutes, intensity}
POST /api/pulse              {feeling, had_connection, connection_type?}

# Analytics
GET  /api/weekly-digest
GET  /api/life-compass
GET  /api/patterns

# Settings
GET  /api/settings
PUT  /api/settings           (tracks changes in LimitChanges table)

# State
GET  /api/state              → {check_in_mode, north_star}
PUT  /api/state/pause        {duration, reminder}
```

---

## UI Screens

### Desktop + Mobile Mockups

All screens have mobile-optimized versions with:
- 375px viewport
- Safe area padding
- Touch-friendly targets (min 44px)
- Fixed bottom navigation

| Screen | Purpose |
|--------|---------|
| Timer Home | Start session, pick type, write intention |
| Active Session | Dark mode countdown with progress ring |
| Break Lockout | Enforced break with suggestions |
| Session End | Distractions + did-the-thing |
| Evening Check-in | Mood + connection (dark, calm) |
| Check-in Mode | Minimal UI for spiral protection |
| Quick Log | Meditation/exercise entry |
| Weekly Digest | Stats, mood chart, patterns |
| Rabbit Hole Alert | 3-session check-in |
| Settings | Limits, timing, toggles |
| Life Compass | North Star + all patterns + dimensions |

**Mockups location:** `/tmp/balance-ui/`

---

## Habit Design Principles

Based on research into ethical nudging and habit formation:

### Do

- **Identity framing:** "You're building a practice" not "Achievement unlocked"
- **Celebrate showing up:** "You came back. That matters."
- **Soft sparklines:** Small trends, not big pressure numbers
- **Weekly view > daily:** Reduces "I failed today" feeling
- **Micro-commitments:** 3-word intention, one-tap logging

### Don't

- **No gamification:** No points, badges, or leaderboards
- **No shame language:** No "streak broken", "you're behind"
- **No push notifications:** Pull-only engagement
- **No daily pressure:** Weekly rhythm, not daily demands
- **No comparison:** Only compare to your own baseline

### Friction Design

- **Remove friction from good behaviors:** One tap to log meditation
- **Add friction to harmful patterns:** Must wait full break, can't skip
- **Gentle friction for reflection:** 3-word intention forces focus

---

## Implementation Notes

### Claude Agent SDK Integration

Weekly analysis job to discover patterns:
- Runs locally (data never leaves system)
- Processes all tables to find correlations
- Outputs patterns with confidence levels
- Stores in InsightEvents for surfacing

### Traefik Configuration

ForwardAuth middleware pointing to Balance API:
```yaml
http:
  middlewares:
    balance-check:
      forwardAuth:
        address: "http://balance:8000/api/check"

  routers:
    bookmark:
      middlewares:
        - balance-check
    canvas:
      middlewares:
        - balance-check
    kasten:
      middlewares:
        - balance-check
```

### Environment Variables

```
DATABASE_URL          # SQLite path
KASTEN_URL            # For any cross-service needs
BOOKMARK_URL          # For any cross-service needs
```

---

## Future Considerations

- Voice input for intentions (reduces typing friction)
- Watch/widget for quick logging
- Integration with calendar for context
- Export to other formats (CSV, JSON)

---

## Summary

Balance is a personal rhythm tracker that:
1. Uses Pomodoro technique with hard break enforcement
2. Tracks meditation, exercise, mood, and connection
3. Orients all analytics around a user-defined life goal
4. Discovers personal patterns through Claude Agent SDK analysis
5. Protects against burnout with limits and spiral detection
6. Never shames, never pushes, only mirrors

The goal isn't optimization. It's alignment with the life you want to live.
