# Claude Code + Balance Lock Integration

Lock Claude Code behind active Pomodoro sessions. No session = no Claude.

## Problem

Claude Code is a powerful rabbit hole. "Just one more thing" becomes 4 hours of unfocused exploration. This integration forces intentionality — you must start a session and name what you're doing before Claude will help.

## Design

### States

| Balance State | Claude Code |
|---------------|-------------|
| Idle (no session) | Blocked |
| Active session | Allowed |
| On break | Blocked |

### User Experience

1. User runs `claude` or sends a message
2. Hook checks `balance.gstoehl.dev/api/session/active`
3. If no active session → prompt to start one (type + intention)
4. If active → proceed normally
5. If session ends mid-use → block on next interaction

When blocked, user sees:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No active session.

Start one now? [y/n]: y

Type: [E]xpected / [P]ersonal: e

Intention (3 words): Fix auth bug

Session started. 25:00 remaining.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Balance API Changes

### `GET /api/session/active`

Returns current session state for Claude Code hook:

```json
// Active session
{
  "allowed": true,
  "session": {
    "id": 42,
    "type": "expected",
    "intention": "Fix auth bug",
    "remaining_seconds": 847
  }
}

// No session or on break
{
  "allowed": false,
  "reason": "no_session" | "on_break",
  "break_remaining": 180  // only if on_break
}
```

### `POST /api/session/quick-start`

For terminal-initiated sessions:

```json
// Request
{
  "type": "expected" | "personal",
  "intention": "Fix auth bug"
}

// Response (success)
{
  "success": true,
  "session_id": 43
}

// Response (on break)
{
  "success": false,
  "reason": "on_break",
  "remaining": 180
}
```

### `POST /api/session/mark-claude-used`

Called by hook when session is active and Claude proceeds. Marks session for analytics.

```json
// Response
{ "marked": true }
```

Idempotent — can be called multiple times, only sets flag once.

---

## Database Changes

Add to `sessions` table:

```sql
ALTER TABLE sessions ADD COLUMN claude_used BOOLEAN DEFAULT FALSE;
```

---

## Claude Code Hook

### Source Location

**Version controlled:** `scripts/claude-hooks/balance-check.py`

**Installed via symlink:**
```bash
mkdir -p ~/.claude/hooks
ln -sf ~/knowledge-system/scripts/claude-hooks/balance-check.py ~/.claude/hooks/
```

### Claude Settings

`~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [{
          "type": "command",
          "command": "python3 ~/.claude/hooks/balance-check.py"
        }]
      }
    ]
  }
}
```

### Hook Behavior

1. Call `GET https://balance.gstoehl.dev/api/session/active`
2. If `allowed: true`:
   - Call `POST /api/session/mark-claude-used` (fire-and-forget)
   - Exit 0 (proceed)
3. If `allowed: false`:
   - Show interactive prompt for type + intention
   - If user starts session → call `POST /api/session/quick-start` → exit 0
   - If user declines → exit 2 (block) with message

---

## Edge Cases

**Balance unreachable:**
Hook fails to connect → block with message: "Can't reach Balance. Is the server running?" Exit 2. Fail closed, not open.

**Session ends mid-conversation:**
Next `UserPromptSubmit` hook fires → detects no active session → prompts to start new one. User can continue with fresh session or stop.

**Multiple terminals:**
All share same session state via API. Start in one terminal, use in another — works fine. Session is per-user, not per-terminal.

**Break screen bypass attempt:**
User tries to start new session during break → `quick-start` returns error. Hook shows: "Break in progress. 3:00 remaining." Exit 2.

**Network latency:**
Hook is synchronous — adds ~50-100ms per prompt. Acceptable for the intentionality benefit.

---

## Analytics Potential

With `claude_used` tracking:

- "X% of your sessions used Claude"
- "Claude sessions avg 2.1 distractions vs 1.4 without"
- "You complete 'did the thing' 78% with Claude vs 65% without"
- Pattern detection: "When you use Claude for Personal sessions, rabbit hole risk +40%"

---

## File Structure

```
balance/
├── src/
│   ├── routers/
│   │   └── sessions.py      # Add 3 endpoints
│   └── database.py          # Add claude_used column

scripts/
└── claude-hooks/
    └── balance-check.py     # New hook script
```

---

## Implementation Notes

- Hook script uses Python 3 (available on system)
- API calls use `requests` or `urllib` (stdlib preferred for fewer deps)
- Interactive prompts use stdin/stdout directly
- Balance API is on same VPS — no external network dependency
