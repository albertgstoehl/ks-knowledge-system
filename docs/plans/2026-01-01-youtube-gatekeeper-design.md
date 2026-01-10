# YouTube Gatekeeper Design

## Problem

YouTube's UX is designed to maximize attention through infinite feeds, autoplay, and recommendations. This makes it unsuitable for intentional learning, but valuable for explorative discovery when used with constraints.

Failure pattern: passive consumption without reflection, pulled by infinite feeds, losing time awareness.

Success pattern: intentional entry → consume → capture insight → exit.

## Solution

Use Balance as a gatekeeper for YouTube access. YouTube sessions become a time-boxed activity type with:
- Stated intention before starting
- Fixed duration (15/30/45/60 min)
- Hard block via NextDNS when time expires
- Server-side enforcement (works even if browser is closed)

## User Flow

### Starting a YouTube Session

1. Open Balance (balance.gstoehl.dev)
2. Select "YouTube" session type (alongside Expected/Personal)
3. Enter intention: "What are you looking for?" (required)
4. Select duration: 15 / 30 / 45 / 60 min
5. Click "Start" → Balance calls NextDNS API → youtube.com unblocks
6. Timer starts, user explores YouTube on any device

### During the Session

- Balance shows countdown timer (same UI as Focus sessions)
- YouTube accessible on all devices (DNS-level unblock)
- User can save videos to bookmark-manager

### When Timer Ends

- Server-side scheduler detects expiry
- Calls NextDNS API → youtube.com blocks immediately
- No soft prompts, no grace period
- Session logged with intention and duration
- Break begins (same as after Focus sessions)

## Technical Architecture

### NextDNS Integration

YouTube is blocked by default via NextDNS denylist. Balance toggles this:

```
# Unblock (session start)
DELETE /profiles/{profile_id}/denylist/youtube.com

# Block (session end)
PUT /profiles/{profile_id}/denylist
Body: { "id": "youtube.com", "active": true }
```

Configuration via environment variables:
- `NEXTDNS_API_KEY`
- `NEXTDNS_PROFILE_ID`

### Server-Side Scheduler

APScheduler runs background jobs to enforce session expiry and evening cutoff **for ALL session types**, not just YouTube. This ensures breaks are set even if the browser is closed mid-session.

1. **Session expiry check** (every 30 seconds)
   - Find ALL sessions past their end time (expected, personal, youtube)
   - For YouTube: call NextDNS block
   - Mark session ended
   - Set break_until (enforces break even without client callback)

2. **Evening cutoff** (every minute)
   - Check current time vs evening_cutoff setting
   - Enable evening mode when cutoff passes

```python
# balance/src/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def check_expired_sessions():
    """Enforce session end + break for ALL session types."""
    for session in await db.get_active_sessions():
        if now >= session.end_time:
            if session.type == "youtube":
                await nextdns.block_youtube()
            await db.mark_session_ended(session.id)
            await db.set_break_until(now + break_duration)

async def check_evening_cutoff():
    settings = await db.get_settings()
    if now >= cutoff and not app_state.evening_mode:
        app_state.evening_mode = True

def start_scheduler():
    scheduler.add_job(check_expired_sessions, IntervalTrigger(seconds=30))
    scheduler.add_job(check_evening_cutoff, IntervalTrigger(minutes=1))
    scheduler.start()
```

**On startup:** Also runs `check_expired_sessions()` to catch any sessions that expired during pod restart.

### Data Model

Extend session types:

```python
class SessionType(str, Enum):
    EXPECTED = "expected"
    PERSONAL = "personal"
    YOUTUBE = "youtube"
```

YouTube sessions use existing fields:
- `intention` — "What are you looking for?"
- `duration` — Variable (15/30/45/60 min), not fixed pomodoro length
- `priority_id` — NULL (not applicable)

### API Changes

```
POST /api/sessions/start
Body: { "type": "youtube", "intention": "...", "duration": 30 }
Response: { "end_timestamp": ..., "duration": 30 }
# Side effect: calls NextDNS unblock

# Session end triggered by scheduler, not client
# Scheduler calls NextDNS block when end_timestamp passes
```

## UI Changes

### Home Page

Add YouTube as third session type:

```html
<div class="button-group type-selection">
  <button class="btn btn--option active" data-type="expected">Expected</button>
  <button class="btn btn--option" data-type="personal">Personal</button>
  <button class="btn btn--option" data-type="youtube">YouTube</button>
</div>
```

When YouTube selected:
- Hide priority dropdown
- Change intention label to "What are you looking for?"
- Show duration picker:

```html
<div id="duration-section" class="duration-section">
  <label class="label">Duration</label>
  <div class="button-group duration-options">
    <button class="btn btn--option" data-duration="15">15m</button>
    <button class="btn btn--option active" data-duration="30">30m</button>
    <button class="btn btn--option" data-duration="45">45m</button>
    <button class="btn btn--option" data-duration="60">60m</button>
  </div>
</div>
```

### Active Session Page

Same as current, badge shows "YouTube" instead of Expected/Personal.

### Session End Page

Different questions for YouTube:
- Skip "Distractions?"
- Skip "Did you do the thing?"
- Optional: "Save anything good?" (yes/no) for stats

Then break begins as normal.

## Edge Cases

### NextDNS API Failure on Start

- Show error: "Couldn't unlock YouTube. Try again."
- Don't start session
- User can retry or do Focus session instead

### NextDNS API Failure on End

- Retry 3 times with 1s delays
- If still fails: log error, session ends locally
- Safety reset: on any session start, try to block YouTube first

### Pod Restart Mid-Session

- On startup, scheduler checks for expired YouTube sessions
- Immediately blocks YouTube if any found
- Resumes normal interval checks

### User Never Returns to Balance

- Scheduler runs server-side, independent of browser
- YouTube gets blocked when timer expires regardless

## Out of Scope

- Tracking which bookmarks were saved during YouTube session
- SSE for real-time client updates (polling is sufficient)
- Daily/weekly YouTube time limits
- Per-video unlock flow

## Related Notes

- 251226a: Explorative Learning
- 251225b: YouTube For Unintentional Learning
