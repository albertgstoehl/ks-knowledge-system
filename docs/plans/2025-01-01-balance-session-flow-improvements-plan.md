# Balance Session Flow Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix Balance session flow so breaks start immediately on timer end, cycle resets after natural rest, and rabbit hole check actually works.

**Architecture:** Modify session endpoints to separate timer completion (starts break) from questionnaire submission (gates next session). Add smart cycle reset logic based on time since last session. Wire existing rabbit-hole endpoint to frontend.

**Tech Stack:** Python/FastAPI backend, vanilla JS frontend, SQLite database

---

### Task 1: Add timer-complete endpoint

**Files:**
- Modify: `balance/src/routers/sessions.py`
- Modify: `balance/src/models.py`

**Step 1: Add TimerComplete response model**

In `balance/src/models.py`, add after line ~75:

```python
class TimerCompleteResponse(BaseModel):
    break_duration: int
    cycle_position: int
    is_long_break: bool
    break_until: datetime
```

**Step 2: Add helper to get cycle position with smart reset**

In `balance/src/routers/sessions.py`, add helper function:

```python
async def get_cycle_position_smart() -> int:
    """Get cycle position, resetting if naturally rested."""
    settings = await get_settings()
    long_break_minutes = settings["long_break"]

    async with get_db() as db:
        # Get last completed session
        cursor = await db.execute(
            """SELECT ended_at FROM sessions
               WHERE ended_at IS NOT NULL
               ORDER BY ended_at DESC LIMIT 1"""
        )
        row = await cursor.fetchone()

        if row and row[0]:
            last_ended = datetime.fromisoformat(row[0])
            time_since = datetime.now() - last_ended

            # If rested longer than long break, reset cycle
            if time_since > timedelta(minutes=long_break_minutes):
                return 0

        # Count today's completed sessions for cycle position
        today = datetime.now().date().isoformat()
        cursor = await db.execute(
            """SELECT COUNT(*) FROM sessions
               WHERE date(ended_at) = ? AND ended_at IS NOT NULL""",
            (today,)
        )
        count = (await cursor.fetchone())[0]
        return count % 4
```

**Step 3: Add timer-complete endpoint**

In `balance/src/routers/sessions.py`, add endpoint:

```python
@router.post("/sessions/timer-complete")
async def timer_complete():
    """Called when session timer hits 0. Starts break immediately."""
    # Get current session
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, type FROM sessions WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1"
        )
        current = await cursor.fetchone()

        if not current:
            raise HTTPException(400, "No active session")

    settings = await get_settings()
    cycle_position = await get_cycle_position_smart()

    # Every 4th session (position 3) gets long break
    is_long_break = (cycle_position == 3)
    break_duration = settings["long_break"] if is_long_break else settings["short_break"]

    # Set break_until immediately
    break_until = datetime.now() + timedelta(minutes=break_duration)

    async with get_db() as db:
        await db.execute(
            "UPDATE app_state SET break_until = ? WHERE id = 1",
            (break_until.isoformat(),)
        )
        await db.commit()

    return {
        "break_duration": break_duration,
        "cycle_position": cycle_position,
        "is_long_break": is_long_break,
        "break_until": break_until.isoformat()
    }
```

**Step 4: Test manually**

```bash
curl -X POST http://localhost:8005/api/sessions/start \
  -H "Content-Type: application/json" \
  -d '{"type": "expected", "intention": "test"}'

# Wait or manually trigger timer complete
curl -X POST http://localhost:8005/api/sessions/timer-complete

# Should return break info, check app_state has break_until set
```

**Step 5: Commit**

```bash
git add balance/src/routers/sessions.py balance/src/models.py
git commit -m "feat(balance): add timer-complete endpoint for immediate breaks"
```

---

### Task 2: Modify session end to be questionnaire-only

**Files:**
- Modify: `balance/src/routers/sessions.py`
- Modify: `balance/src/models.py`

**Step 1: Add rabbit_hole field to SessionEnd model**

In `balance/src/models.py`, modify `SessionEnd` class:

```python
class SessionEnd(BaseModel):
    distractions: str  # 'none', 'some', 'many'
    did_the_thing: bool
    rabbit_hole: Optional[bool] = None
```

**Step 2: Modify end_session to handle rabbit hole and not set break**

In `balance/src/routers/sessions.py`, update `end_session` function:

```python
@router.post("/sessions/end")
async def end_session(data: SessionEnd):
    """Submit questionnaire for completed session. Break already started via timer-complete."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, type FROM sessions WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1"
        )
        current = await cursor.fetchone()

        if not current:
            raise HTTPException(400, "No active session to end")

        session_id = current[0]

        # Update session with questionnaire answers
        await db.execute(
            """UPDATE sessions
               SET ended_at = ?, distractions = ?, did_the_thing = ?, rabbit_hole = ?
               WHERE id = ?""",
            (datetime.now().isoformat(), data.distractions,
             data.did_the_thing, data.rabbit_hole, session_id)
        )

        # If rabbit_hole acknowledged, extend break to long break
        if data.rabbit_hole:
            settings = await get_settings()
            new_break_until = datetime.now() + timedelta(minutes=settings["long_break"])
            await db.execute(
                "UPDATE app_state SET break_until = ? WHERE id = 1",
                (new_break_until.isoformat(),)
            )

        await db.commit()

    return {"status": "ok", "session_id": session_id}
```

**Step 3: Commit**

```bash
git add balance/src/routers/sessions.py balance/src/models.py
git commit -m "feat(balance): session end is now questionnaire-only, supports rabbit_hole"
```

---

### Task 3: Add questionnaire_pending check to session start

**Files:**
- Modify: `balance/src/routers/sessions.py`

**Step 1: Modify start_session to check questionnaire done**

In `balance/src/routers/sessions.py`, add check at start of `start_session`:

```python
@router.post("/sessions/start")
async def start_session(data: SessionStart):
    """Start a new focus session."""
    # Check for pending questionnaire (session with no ended_at)
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT id FROM sessions
               WHERE ended_at IS NULL
               ORDER BY started_at DESC LIMIT 1"""
        )
        pending = await cursor.fetchone()
        if pending:
            raise HTTPException(400, "Complete questionnaire for previous session first")

    # ... rest of existing validation (break check, etc.)
```

**Step 2: Update status endpoint to include questionnaire_pending**

In `balance/src/routers/sessions.py`, modify the `/api/status` endpoint to add a new mode:

```python
# After checking for break, before checking for active session, add:

# Check for session needing questionnaire (timer done but no ended_at)
async with get_db() as db:
    cursor = await db.execute(
        """SELECT id, type, intention, started_at FROM sessions
           WHERE ended_at IS NULL
           ORDER BY started_at DESC LIMIT 1"""
    )
    pending_session = await cursor.fetchone()

# If on break AND have pending questionnaire, return session_ended mode
if state["break_until"] and pending_session:
    break_until = datetime.fromisoformat(state["break_until"])
    if now < break_until:
        remaining = int((break_until - now).total_seconds())
        return {
            "mode": "session_ended",
            "remaining_seconds": remaining,
            "end_timestamp": break_until.timestamp(),
            "server_timestamp": server_timestamp,
            "total_duration": settings["short_break"] * 60,
            "session": {
                "id": pending_session[0],
                "type": pending_session[1],
                "intention": pending_session[2],
            },
            "questionnaire_pending": True
        }
```

**Step 3: Commit**

```bash
git add balance/src/routers/sessions.py
git commit -m "feat(balance): block new session until questionnaire done"
```

---

### Task 4: Frontend - call timer-complete on timer end

**Files:**
- Modify: `balance/src/static/js/timer.js`

**Step 1: Add timerComplete method**

In `balance/src/static/js/timer.js`, add method to Balance object:

```javascript
async timerComplete() {
  try {
    const response = await fetch('/api/sessions/timer-complete', {
      method: 'POST'
    });

    if (!response.ok) {
      console.error('Failed to complete timer');
      return;
    }

    const data = await response.json();

    // Update break timing
    this.endTimestamp = new Date(data.break_until).getTime() / 1000;
    this.totalDuration = data.break_duration * 60;

    // Check for rabbit hole if personal session
    if (this.sessionType === 'personal') {
      await this.checkRabbitHole();
    }

    // Show end page (questionnaire) with break running
    this.showPage('end');
    this.updateEndUI();
    this.startTick(); // Continue ticking for break countdown

  } catch (err) {
    console.error('Timer complete error:', err);
  }
},
```

**Step 2: Modify tick handler to call timerComplete**

In `balance/src/static/js/timer.js`, modify the tick handler where it detects timer complete:

```javascript
// In startTick(), replace the session complete section:
// Timer complete - go to end page
if (remaining <= 0) {
  this.stopTick();
  // OLD: this.showPage('end'); this.updateEndUI();
  // NEW: Call timer-complete endpoint
  this.timerComplete();
}
```

**Step 3: Commit**

```bash
git add balance/src/static/js/timer.js
git commit -m "feat(balance): call timer-complete when session ends"
```

---

### Task 5: Frontend - rabbit hole check

**Files:**
- Modify: `balance/src/static/js/timer.js`
- Modify: `balance/src/templates/_content_index.html`

**Step 1: Add checkRabbitHole method**

In `balance/src/static/js/timer.js`, add to Balance object:

```javascript
async checkRabbitHole() {
  try {
    const response = await fetch('/api/sessions/rabbit-hole');
    const data = await response.json();

    this.showRabbitHolePrompt = data.should_alert;
    this.consecutivePersonalCount = data.consecutive_count;
  } catch (err) {
    console.error('Rabbit hole check error:', err);
    this.showRabbitHolePrompt = false;
  }
},
```

**Step 2: Add rabbit hole state**

In `balance/src/static/js/timer.js`, add to Balance object state:

```javascript
// Add to state section at top
showRabbitHolePrompt: false,
consecutivePersonalCount: 0,
selectedRabbitHole: null,
```

**Step 3: Add rabbit hole UI to end page template**

In `balance/src/templates/_content_index.html`, add after did-thing-options div (around line 90):

```html
<div class="question-group rabbit-hole-group" id="rabbit-hole-group" style="display: none;">
  <label class="question-label">3 personal sessions in a row. Still on track?</label>
  <div class="button-group binary-options" id="rabbit-hole-options">
    <button class="btn btn--option" data-value="no">Still on track</button>
    <button class="btn btn--option" data-value="yes">Rabbit hole, take a break</button>
  </div>
</div>
```

**Step 4: Wire up rabbit hole UI**

In `balance/src/static/js/timer.js`, add to bindEvents:

```javascript
// Rabbit hole options
this.el.rabbitHoleOptions = document.getElementById('rabbit-hole-options');
this.el.rabbitHoleGroup = document.getElementById('rabbit-hole-group');

this.el.rabbitHoleOptions?.querySelectorAll('.btn--option').forEach(btn => {
  btn.addEventListener('click', () => {
    this.el.rabbitHoleOptions.querySelectorAll('.btn--option').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    this.selectedRabbitHole = btn.dataset.value === 'yes';
    this.checkEndComplete();
  });
});
```

**Step 5: Update updateEndUI to show/hide rabbit hole**

In `balance/src/static/js/timer.js`, add to updateEndUI:

```javascript
// Show rabbit hole prompt if needed
if (this.showRabbitHolePrompt && this.el.rabbitHoleGroup) {
  this.el.rabbitHoleGroup.style.display = 'block';
  this.selectedRabbitHole = null;
} else if (this.el.rabbitHoleGroup) {
  this.el.rabbitHoleGroup.style.display = 'none';
  this.selectedRabbitHole = false; // Not needed, auto-pass
}
```

**Step 6: Update checkEndComplete to require rabbit hole answer**

In `balance/src/static/js/timer.js`, modify checkEndComplete:

```javascript
checkEndComplete() {
  const baseComplete = this.selectedDistractions && this.selectedDidThing !== null;
  const rabbitHoleComplete = !this.showRabbitHolePrompt || this.selectedRabbitHole !== null;
  this.el.continueBtn.disabled = !(baseComplete && rabbitHoleComplete);
},
```

**Step 7: Update endSession to send rabbit_hole**

In `balance/src/static/js/timer.js`, modify endSession:

```javascript
async endSession() {
  try {
    const response = await fetch('/api/sessions/end', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        distractions: this.selectedDistractions,
        did_the_thing: this.selectedDidThing,
        rabbit_hole: this.selectedRabbitHole || false
      })
    });
    // ... rest unchanged
```

**Step 8: Commit**

```bash
git add balance/src/static/js/timer.js balance/src/templates/_content_index.html
git commit -m "feat(balance): wire up rabbit hole check UI"
```

---

### Task 6: Frontend - show break timer on end screen

**Files:**
- Modify: `balance/src/templates/_content_index.html`
- Modify: `balance/src/static/js/timer.js`

**Step 1: Add break countdown to end page template**

In `balance/src/templates/_content_index.html`, add at top of page-end div:

```html
<!-- Session End Page -->
<div id="page-end" class="page">
  <div class="container">
    <div class="break-countdown" id="end-break-countdown">
      <div class="break-label">Break time</div>
      <div class="timer__value" id="end-break-time">--:--</div>
    </div>

    <header class="page-header">
      <!-- existing content -->
```

**Step 2: Cache the new element**

In `balance/src/static/js/timer.js`, add to cacheElements:

```javascript
this.el.endBreakTime = document.getElementById('end-break-time');
```

**Step 3: Update tick to show break time on end page**

In `balance/src/static/js/timer.js`, modify startTick to handle end page:

```javascript
// Add to the tick interval, after the break page handling:
} else if (this.currentPage === 'end') {
  // Update break countdown on end screen
  if (this.el.endBreakTime) {
    this.el.endBreakTime.textContent = this.formatTime(remaining);
  }

  // When break ends on end screen, enable continue if questionnaire done
  if (remaining <= 0) {
    if (this.el.endBreakTime) {
      this.el.endBreakTime.textContent = 'Break complete';
    }
  }
}
```

**Step 4: Add CSS for break countdown on end screen**

In `balance/src/static/css/style.css`, add:

```css
/* Break countdown on end screen */
.break-countdown {
  text-align: center;
  padding: 1rem;
  margin-bottom: 1rem;
  background: var(--color-surface, #f5f5f5);
  border: 1px solid var(--color-border);
}

.break-countdown .break-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-muted);
  margin-bottom: 0.25rem;
}

.break-countdown .timer__value {
  font-size: 2rem;
}
```

**Step 5: Commit**

```bash
git add balance/src/templates/_content_index.html balance/src/static/js/timer.js balance/src/static/css/style.css
git commit -m "feat(balance): show break countdown on session end screen"
```

---

### Task 7: Handle session_ended mode in syncWithServer

**Files:**
- Modify: `balance/src/static/js/timer.js`

**Step 1: Add session_ended case to syncWithServer**

In `balance/src/static/js/timer.js`, add case in the switch statement:

```javascript
case 'session_ended':
  // Break is running, questionnaire pending
  this.currentSession = status.session;
  this.sessionType = status.session.type;
  this.intention = status.session.intention || '';
  this.endTimestamp = status.end_timestamp;
  this.totalDuration = status.total_duration;

  // Check rabbit hole for personal sessions
  if (this.sessionType === 'personal') {
    await this.checkRabbitHole();
  }

  this.showPage('end');
  this.updateEndUI();
  this.startTick();
  break;
```

**Step 2: Commit**

```bash
git add balance/src/static/js/timer.js
git commit -m "feat(balance): handle session_ended mode on page load"
```

---

### Task 8: Test all flows

**Step 1: Test immediate break on session end**

1. Start a session
2. Wait for timer (or set short duration in settings)
3. Verify: break countdown appears immediately on end screen
4. Fill questionnaire, verify can continue after break ends

**Step 2: Test smart cycle reset**

1. Complete 2 sessions normally
2. Wait longer than long_break duration (or adjust setting)
3. Start new session
4. Verify: short break triggers (not long break)

**Step 3: Test rabbit hole check**

1. Complete 3 consecutive personal sessions
2. On 3rd session end, verify rabbit hole prompt appears
3. Click "Rabbit hole, take a break"
4. Verify: break is extended to long break duration

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat(balance): complete session flow improvements"
```

---

## Files Changed Summary

| File | Changes |
|------|---------|
| `balance/src/models.py` | Add TimerCompleteResponse, rabbit_hole field |
| `balance/src/routers/sessions.py` | Add timer-complete, modify end/start/status |
| `balance/src/static/js/timer.js` | timerComplete, checkRabbitHole, session_ended mode |
| `balance/src/templates/_content_index.html` | Break countdown, rabbit hole UI |
| `balance/src/static/css/style.css` | Break countdown styles |
