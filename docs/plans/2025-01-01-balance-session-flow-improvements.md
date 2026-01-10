# Balance Session Flow Improvements

## Overview

Three improvements to Balance session handling:
1. Break starts immediately when session ends (not after questionnaire)
2. Break cycle resets if user naturally rested
3. Rabbit hole check prompts after consecutive personal sessions

---

## 1. Immediate Break on Session End

### Current (wrong)
```
Timer ends → Questionnaire → Break starts → Next session
```

### New
```
Timer ends → Break starts + Questionnaire shown
                    ↓
         Break ends + Questionnaire done → Next session available
```

### Implementation

**New endpoint:** `POST /api/sessions/timer-complete`
- Called when timer hits 0
- Sets `break_until` immediately
- Returns break duration

**Modified:** `POST /api/sessions/end`
- Now only submits questionnaire (distractions, did_the_thing)
- Sets `session.ended_at`

**Modified:** `POST /api/sessions/start`
- Checks BOTH conditions:
  - `break_until` has passed (or is null)
  - Last session has `ended_at` set (questionnaire done)

### State

| Field | Meaning |
|-------|---------|
| `break_until` | When break ends (set on timer complete) |
| `session.ended_at` | When questionnaire submitted (null until filled) |

---

## 2. Smart Break Cycle Reset

### Problem

Every 4th session triggers 15 min long break, even if user left for hours. User already rested - don't force another long break.

### Solution

On session start, check time since last session ended:
- If `time_since > long_break_duration` → reset cycle to 0
- Natural rest counts as rest

### Logic

```python
# In /api/sessions/start or timer-complete
last_session = get_last_completed_session()
if last_session and last_session.ended_at:
    time_since = now - last_session.ended_at
    if time_since > timedelta(minutes=settings.long_break):
        cycle_position = 0  # Fresh start
    else:
        cycle_position = get_todays_completed_count() % 4
else:
    cycle_position = 0

# In timer-complete, determine break duration
if cycle_position == 3:  # Every 4th
    break_duration = settings.long_break
else:
    break_duration = settings.short_break
```

---

## 3. Rabbit Hole Check

### Trigger

After N consecutive "personal" sessions (default: 3 from settings.rabbit_hole_check)

### Prompt

Shown on session end screen alongside questionnaire:

```
"Still on original goal, or rabbit hole?"

[Still on track]              [Rabbit hole, take a break]
   ↓                                    ↓
Normal break continues          Break extended to long_break
```

### Backend

Existing endpoint: `GET /api/sessions/rabbit-hole`
- Returns `{should_alert, consecutive_count, threshold}`

Modified: `POST /api/sessions/end`
- Accepts optional `rabbit_hole: boolean` field
- If `true`, extend `break_until` to long_break duration

### Frontend

On session end (for personal sessions):
1. Call `/api/sessions/rabbit-hole`
2. If `should_alert: true`, show rabbit hole prompt
3. User choice stored in `session.rabbit_hole`

### Counter Reset

Consecutive personal count resets when:
- User completes an "expected" session
- User acknowledges rabbit hole (took the longer break)

---

## API Changes Summary

| Endpoint | Change |
|----------|--------|
| `POST /api/sessions/timer-complete` | **New** - Timer hit 0, start break |
| `POST /api/sessions/end` | Modified - questionnaire only, accepts `rabbit_hole` |
| `POST /api/sessions/start` | Modified - check questionnaire done |
| `GET /api/sessions/rabbit-hole` | Existing - no change |
| `GET /api/status` | Modified - include `questionnaire_pending` flag |

---

## UI Changes

### Session End Screen

Shows during break (not before):
- Break countdown visible at top
- Questionnaire: distractions + did-the-thing
- Rabbit hole prompt (if applicable, for personal sessions)
- "Continue" button disabled until break ends

### Timer Page

- When timer hits 0, immediately transition to break + end screen
- Don't wait for user action to start break
