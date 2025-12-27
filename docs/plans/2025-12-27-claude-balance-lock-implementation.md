# Claude Code + Balance Lock Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Lock Claude Code behind active Pomodoro sessions, with terminal-based session quick-start.

**Architecture:** Extend Balance API with 3 new endpoints, add `claude_used` tracking column, create Python hook script that calls Balance API and prompts for session start when blocked.

**Tech Stack:** Python 3.11, FastAPI, SQLite, urllib (stdlib for hook - no deps)

**Design Reference:** `docs/plans/2025-12-27-claude-balance-lock-design.md`

---

## Task 1: Add claude_used Column to Database

**Files:**
- Modify: `balance/src/database.py:20-29`

**Step 1: Add column to sessions table schema**

In `balance/src/database.py`, update the sessions table definition:

```python
-- Sessions (Pomodoro)
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK (type IN ('expected', 'personal')),
    intention TEXT,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    distractions TEXT CHECK (distractions IN ('none', 'some', 'many')),
    did_the_thing BOOLEAN,
    rabbit_hole BOOLEAN,
    claude_used BOOLEAN DEFAULT FALSE
);
```

**Step 2: Add migration for existing databases**

Add after the CREATE TABLE statements, before the INSERT OR IGNORE:

```python
-- Migration: add claude_used column if missing
ALTER TABLE sessions ADD COLUMN claude_used BOOLEAN DEFAULT FALSE;
```

Note: SQLite ignores ALTER TABLE if column exists when wrapped in try/catch, but we'll use a different approach - check and add:

Actually, simpler: SQLite's `ALTER TABLE ADD COLUMN` fails if column exists. We'll wrap it in a try block in Python. Update init_db:

```python
async def init_db(db_url: str = None):
    """Initialize database with schema."""
    url = db_url or get_database_url()
    async with aiosqlite.connect(url) as db:
        await db.executescript("""
            -- Sessions (Pomodoro)
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK (type IN ('expected', 'personal')),
                intention TEXT,
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                distractions TEXT CHECK (distractions IN ('none', 'some', 'many')),
                did_the_thing BOOLEAN,
                rabbit_hole BOOLEAN,
                claude_used BOOLEAN DEFAULT FALSE
            );

            -- ... rest of tables unchanged ...
        """)

        # Migration: add claude_used if missing (for existing DBs)
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN claude_used BOOLEAN DEFAULT FALSE")
        except Exception:
            pass  # Column already exists

        await db.commit()
```

**Step 3: Verify by running the app**

```bash
cd balance && DATABASE_URL=./data/balance.db python -c "import asyncio; from src.database import init_db; asyncio.run(init_db())"
```

Expected: No errors

**Step 4: Commit**

```bash
git add balance/src/database.py
git commit -m "feat(balance): add claude_used column to sessions table"
```

---

## Task 2: Add Response Models for New Endpoints

**Files:**
- Modify: `balance/src/models.py`

**Step 1: Add SessionActive response model**

Add to `balance/src/models.py`:

```python
# Claude Code integration models
class SessionInfo(BaseModel):
    id: int
    type: str
    intention: Optional[str]
    remaining_seconds: int


class SessionActiveResponse(BaseModel):
    allowed: bool
    reason: Optional[Literal["no_session", "on_break"]] = None
    break_remaining: Optional[int] = None
    session: Optional[SessionInfo] = None


class QuickStartRequest(BaseModel):
    type: Literal["expected", "personal"]
    intention: str


class QuickStartResponse(BaseModel):
    success: bool
    session_id: Optional[int] = None
    reason: Optional[str] = None
    remaining: Optional[int] = None


class MarkClaudeUsedResponse(BaseModel):
    marked: bool
```

**Step 2: Commit**

```bash
git add balance/src/models.py
git commit -m "feat(balance): add models for Claude Code integration endpoints"
```

---

## Task 3: Add /api/session/active Endpoint

**Files:**
- Modify: `balance/src/routers/sessions.py`
- Modify: `balance/tests/test_sessions.py`

**Step 1: Write failing tests**

Add to `balance/tests/test_sessions.py`:

```python
async def test_session_active_no_session():
    """Test /api/session/active when no session is active."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/session/active")
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False
        assert data["reason"] == "no_session"


async def test_session_active_with_session():
    """Test /api/session/active when a session is active."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start a session
        await client.post("/api/sessions/start", json={
            "type": "expected",
            "intention": "Test task"
        })

        response = await client.get("/api/session/active")
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        assert data["session"]["type"] == "expected"
        assert data["session"]["intention"] == "Test task"
        assert data["session"]["remaining_seconds"] > 0


async def test_session_active_on_break():
    """Test /api/session/active when on break."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start and end a session to trigger break
        await client.post("/api/sessions/start", json={"type": "expected"})
        await client.post("/api/sessions/end", json={
            "distractions": "none",
            "did_the_thing": True
        })

        response = await client.get("/api/session/active")
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False
        assert data["reason"] == "on_break"
        assert data["break_remaining"] > 0
```

**Step 2: Run tests to verify they fail**

```bash
cd balance && DATABASE_URL=./data/test.db python -m pytest tests/test_sessions.py::test_session_active_no_session -v
```

Expected: FAIL - endpoint not found

**Step 3: Implement the endpoint**

Add to `balance/src/routers/sessions.py`:

```python
from ..models import (
    SessionStart, SessionEnd, Session,
    BreakCheck, CanStart,
    SessionActiveResponse, SessionInfo  # Add these imports
)
```

Then add the endpoint:

```python
@router.get("/session/active")
async def check_session_active() -> SessionActiveResponse:
    """Check if Claude Code is allowed (active session, not on break).

    Used by Claude Code hook to determine if it should proceed.
    """
    # Check if on break first
    state = await get_app_state()
    if state["break_until"]:
        break_until = datetime.fromisoformat(state["break_until"])
        now = datetime.now()
        if now < break_until:
            remaining = int((break_until - now).total_seconds())
            return SessionActiveResponse(
                allowed=False,
                reason="on_break",
                break_remaining=remaining
            )
        else:
            # Break expired, clear it
            async with get_db() as db:
                await db.execute("UPDATE app_state SET break_until = NULL WHERE id = 1")
                await db.commit()

    # Check for active session
    session = await get_current_session()
    if not session:
        return SessionActiveResponse(allowed=False, reason="no_session")

    # Calculate remaining time
    settings = await get_settings()
    started_at = datetime.fromisoformat(session["started_at"])
    session_duration = settings["session_duration"] * 60
    end_time = started_at + timedelta(seconds=session_duration)
    remaining = max(0, int((end_time - datetime.now()).total_seconds()))

    return SessionActiveResponse(
        allowed=True,
        session=SessionInfo(
            id=session["id"],
            type=session["type"],
            intention=session["intention"],
            remaining_seconds=remaining
        )
    )
```

**Step 4: Run tests to verify they pass**

```bash
cd balance && DATABASE_URL=./data/test.db python -m pytest tests/test_sessions.py::test_session_active_no_session tests/test_sessions.py::test_session_active_with_session tests/test_sessions.py::test_session_active_on_break -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add balance/src/routers/sessions.py balance/tests/test_sessions.py
git commit -m "feat(balance): add /api/session/active endpoint for Claude Code hook"
```

---

## Task 4: Add /api/session/quick-start Endpoint

**Files:**
- Modify: `balance/src/routers/sessions.py`
- Modify: `balance/tests/test_sessions.py`

**Step 1: Write failing tests**

Add to `balance/tests/test_sessions.py`:

```python
async def test_quick_start_success():
    """Test quick-starting a session from terminal."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/session/quick-start", json={
            "type": "personal",
            "intention": "Fix bug"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["session_id"] is not None

        # Verify session was created
        current = await client.get("/api/sessions/current")
        assert current.json()["active"] is True
        assert current.json()["session"]["intention"] == "Fix bug"


async def test_quick_start_on_break():
    """Test quick-start fails when on break."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a break
        await client.post("/api/sessions/start", json={"type": "expected"})
        await client.post("/api/sessions/end", json={
            "distractions": "none",
            "did_the_thing": True
        })

        # Try to quick-start
        response = await client.post("/api/session/quick-start", json={
            "type": "personal",
            "intention": "Another task"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["reason"] == "on_break"
        assert data["remaining"] > 0


async def test_quick_start_already_in_session():
    """Test quick-start fails when already in session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start a session
        await client.post("/api/sessions/start", json={"type": "expected"})

        # Try to quick-start another
        response = await client.post("/api/session/quick-start", json={
            "type": "personal",
            "intention": "Another task"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["reason"] == "session_active"
```

**Step 2: Run tests to verify they fail**

```bash
cd balance && DATABASE_URL=./data/test.db python -m pytest tests/test_sessions.py::test_quick_start_success -v
```

Expected: FAIL - endpoint not found

**Step 3: Implement the endpoint**

Add imports to `balance/src/routers/sessions.py`:

```python
from ..models import (
    SessionStart, SessionEnd, Session,
    BreakCheck, CanStart,
    SessionActiveResponse, SessionInfo,
    QuickStartRequest, QuickStartResponse  # Add these
)
```

Add the endpoint:

```python
@router.post("/session/quick-start")
async def quick_start_session(data: QuickStartRequest) -> QuickStartResponse:
    """Start a session from terminal (for Claude Code hook).

    Returns success/failure without raising HTTP exceptions,
    so the hook can handle the response gracefully.
    """
    # Check if on break
    state = await get_app_state()
    if state["break_until"]:
        break_until = datetime.fromisoformat(state["break_until"])
        now = datetime.now()
        if now < break_until:
            remaining = int((break_until - now).total_seconds())
            return QuickStartResponse(
                success=False,
                reason="on_break",
                remaining=remaining
            )

    # Check if already in session
    current = await get_current_session()
    if current:
        return QuickStartResponse(success=False, reason="session_active")

    # Check can-start constraints (evening cutoff, hard max)
    can_start = await check_can_start()
    if not can_start.allowed:
        return QuickStartResponse(success=False, reason=can_start.reason)

    # Create the session
    async with get_db() as db:
        cursor = await db.execute(
            """INSERT INTO sessions (type, intention, started_at)
               VALUES (?, ?, ?)""",
            (data.type, data.intention, datetime.now().isoformat())
        )
        session_id = cursor.lastrowid
        await db.commit()

    return QuickStartResponse(success=True, session_id=session_id)
```

**Step 4: Run tests to verify they pass**

```bash
cd balance && DATABASE_URL=./data/test.db python -m pytest tests/test_sessions.py::test_quick_start_success tests/test_sessions.py::test_quick_start_on_break tests/test_sessions.py::test_quick_start_already_in_session -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add balance/src/routers/sessions.py balance/tests/test_sessions.py
git commit -m "feat(balance): add /api/session/quick-start endpoint for terminal session creation"
```

---

## Task 5: Add /api/session/mark-claude-used Endpoint

**Files:**
- Modify: `balance/src/routers/sessions.py`
- Modify: `balance/tests/test_sessions.py`

**Step 1: Write failing tests**

Add to `balance/tests/test_sessions.py`:

```python
async def test_mark_claude_used():
    """Test marking a session as using Claude."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start a session
        await client.post("/api/sessions/start", json={
            "type": "expected",
            "intention": "Test"
        })

        # Mark as using Claude
        response = await client.post("/api/session/mark-claude-used")
        assert response.status_code == 200
        data = response.json()
        assert data["marked"] is True

        # Call again - should still succeed (idempotent)
        response2 = await client.post("/api/session/mark-claude-used")
        assert response2.status_code == 200
        assert response2.json()["marked"] is True


async def test_mark_claude_used_no_session():
    """Test mark-claude-used fails when no session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/session/mark-claude-used")
        assert response.status_code == 200
        data = response.json()
        assert data["marked"] is False
```

**Step 2: Run tests to verify they fail**

```bash
cd balance && DATABASE_URL=./data/test.db python -m pytest tests/test_sessions.py::test_mark_claude_used -v
```

Expected: FAIL - endpoint not found

**Step 3: Implement the endpoint**

Add import to `balance/src/routers/sessions.py`:

```python
from ..models import (
    SessionStart, SessionEnd, Session,
    BreakCheck, CanStart,
    SessionActiveResponse, SessionInfo,
    QuickStartRequest, QuickStartResponse,
    MarkClaudeUsedResponse  # Add this
)
```

Add the endpoint:

```python
@router.post("/session/mark-claude-used")
async def mark_claude_used() -> MarkClaudeUsedResponse:
    """Mark the current session as using Claude Code.

    Called by hook when Claude proceeds. Idempotent.
    """
    session = await get_current_session()
    if not session:
        return MarkClaudeUsedResponse(marked=False)

    async with get_db() as db:
        await db.execute(
            "UPDATE sessions SET claude_used = TRUE WHERE id = ?",
            (session["id"],)
        )
        await db.commit()

    return MarkClaudeUsedResponse(marked=True)
```

**Step 4: Run tests to verify they pass**

```bash
cd balance && DATABASE_URL=./data/test.db python -m pytest tests/test_sessions.py::test_mark_claude_used tests/test_sessions.py::test_mark_claude_used_no_session -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add balance/src/routers/sessions.py balance/tests/test_sessions.py
git commit -m "feat(balance): add /api/session/mark-claude-used endpoint for analytics"
```

---

## Task 6: Create Claude Code Hook Script

**Files:**
- Create: `scripts/claude-hooks/balance-check.py`

**Step 1: Create directory structure**

```bash
mkdir -p scripts/claude-hooks
```

**Step 2: Create the hook script**

Create `scripts/claude-hooks/balance-check.py`:

```python
#!/usr/bin/env python3
"""Claude Code hook to enforce Balance session requirement.

Blocks Claude Code unless an active Pomodoro session is running.
Prompts user to start a session if none is active.
"""

import sys
import json
from urllib.request import urlopen, Request
from urllib.error import URLError

BALANCE_URL = "https://balance.gstoehl.dev"


def api_get(endpoint: str) -> dict:
    """GET request to Balance API."""
    try:
        with urlopen(f"{BALANCE_URL}{endpoint}", timeout=5) as response:
            return json.loads(response.read().decode())
    except URLError as e:
        print(f"Can't reach Balance: {e}", file=sys.stderr)
        sys.exit(2)


def api_post(endpoint: str, data: dict) -> dict:
    """POST request to Balance API."""
    try:
        req = Request(
            f"{BALANCE_URL}{endpoint}",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except URLError as e:
        print(f"Can't reach Balance: {e}", file=sys.stderr)
        sys.exit(2)


def prompt_start_session() -> bool:
    """Prompt user to start a session. Returns True if session started."""
    print("\n" + "━" * 45)
    print("No active session.")
    print()

    # Ask to start
    try:
        answer = input("Start one now? [y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if answer != "y":
        return False

    # Get type
    print()
    try:
        type_input = input("Type: [E]xpected / [P]ersonal: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if type_input in ("e", "expected"):
        session_type = "expected"
    elif type_input in ("p", "personal"):
        session_type = "personal"
    else:
        print("Invalid type. Use 'e' or 'p'.")
        return False

    # Get intention
    print()
    try:
        intention = input("Intention (3 words): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if not intention:
        print("Intention required.")
        return False

    # Start the session
    result = api_post("/api/session/quick-start", {
        "type": session_type,
        "intention": intention
    })

    if result.get("success"):
        print()
        print("Session started. 25:00 remaining.")
        print("━" * 45 + "\n")
        return True
    else:
        reason = result.get("reason", "unknown error")
        if reason == "on_break":
            remaining = result.get("remaining", 0)
            mins, secs = divmod(remaining, 60)
            print(f"Break in progress. {mins}:{secs:02d} remaining.")
        else:
            print(f"Can't start session: {reason}")
        print("━" * 45 + "\n")
        return False


def main():
    # Check session status
    status = api_get("/api/session/active")

    if status.get("allowed"):
        # Session active - mark Claude usage and proceed
        api_post("/api/session/mark-claude-used", {})
        sys.exit(0)

    # Not allowed - check reason
    reason = status.get("reason")

    if reason == "on_break":
        remaining = status.get("break_remaining", 0)
        mins, secs = divmod(remaining, 60)
        print(f"\n━━━ Break in progress. {mins}:{secs:02d} remaining. ━━━\n", file=sys.stderr)
        sys.exit(2)

    # No session - prompt to start one
    if prompt_start_session():
        # Session started successfully - mark and proceed
        api_post("/api/session/mark-claude-used", {})
        sys.exit(0)
    else:
        print("Start a session to use Claude.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
```

**Step 3: Make executable**

```bash
chmod +x scripts/claude-hooks/balance-check.py
```

**Step 4: Test manually (requires Balance running)**

```bash
python3 scripts/claude-hooks/balance-check.py
```

Expected: Either prompts for session (if none active) or exits 0 (if session active)

**Step 5: Commit**

```bash
git add scripts/claude-hooks/balance-check.py
git commit -m "feat: add Claude Code hook script for Balance integration"
```

---

## Task 7: Create Installation Script

**Files:**
- Create: `scripts/claude-hooks/install.sh`

**Step 1: Create installation script**

Create `scripts/claude-hooks/install.sh`:

```bash
#!/bin/bash
# Install Claude Code Balance hook

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_DIR="$HOME/.claude/hooks"

echo "Installing Balance hook for Claude Code..."

# Create hooks directory
mkdir -p "$HOOK_DIR"

# Create symlink
ln -sf "$SCRIPT_DIR/balance-check.py" "$HOOK_DIR/balance-check.py"

echo "Symlink created: $HOOK_DIR/balance-check.py -> $SCRIPT_DIR/balance-check.py"

# Check if settings.json exists
SETTINGS_FILE="$HOME/.claude/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
    echo ""
    echo "Found existing $SETTINGS_FILE"
    echo "Add this to your hooks configuration:"
else
    echo ""
    echo "Create $SETTINGS_FILE with:"
fi

cat << 'EOF'

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
EOF

echo ""
echo "Done! Restart Claude Code to activate."
```

**Step 2: Make executable**

```bash
chmod +x scripts/claude-hooks/install.sh
```

**Step 3: Commit**

```bash
git add scripts/claude-hooks/install.sh
git commit -m "feat: add installation script for Claude Code Balance hook"
```

---

## Task 8: Run All Tests

**Step 1: Run full test suite**

```bash
cd balance && DATABASE_URL=./data/test.db python -m pytest tests/ -v
```

Expected: All tests PASS

**Step 2: Manual end-to-end test**

1. Start Balance locally:
   ```bash
   cd balance && DATABASE_URL=./data/balance.db uvicorn src.main:app --reload --port 8005
   ```

2. Test the hook (in another terminal, with BALANCE_URL pointed to localhost):
   ```bash
   BALANCE_URL=http://localhost:8005 python3 scripts/claude-hooks/balance-check.py
   ```

3. Verify it prompts for session, can start one, then exits 0

**Step 3: Commit test database cleanup (if any)**

```bash
git status
# If test.db was created, add to .gitignore if not already
```

---

## Task 9: Update Documentation

**Files:**
- Modify: `CLAUDE.md` (add hooks section)

**Step 1: Add hooks documentation to CLAUDE.md**

Add to the Balance section in `CLAUDE.md`:

```markdown
| Claude Code integration | `docs/plans/2025-12-27-claude-balance-lock-design.md` |
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Claude Code Balance integration to CLAUDE.md"
```

---

## Summary

**Tasks completed:**
1. Database: Added `claude_used` column with migration
2. Models: Added response models for new endpoints
3. API: `/api/session/active` - check if Claude allowed
4. API: `/api/session/quick-start` - start session from terminal
5. API: `/api/session/mark-claude-used` - track Claude usage
6. Hook: `scripts/claude-hooks/balance-check.py` - enforces session requirement
7. Install: `scripts/claude-hooks/install.sh` - symlinks and shows config
8. Tests: Full coverage for new endpoints
9. Docs: Updated CLAUDE.md

**Post-implementation:**
- Run `scripts/claude-hooks/install.sh` to set up the hook
- Add the hook config to `~/.claude/settings.json`
- Deploy updated Balance to production
- Restart Claude Code to activate
