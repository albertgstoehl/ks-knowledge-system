from fastapi import APIRouter, HTTPException, Response
from datetime import datetime, timedelta

from ..database import get_db
from ..models import (
    SessionStart, SessionEnd, Session,
    BreakCheck, CanStart,
    SessionActiveResponse, SessionInfo,
    QuickStartRequest, QuickStartResponse,
    MarkClaudeUsedResponse
)

router = APIRouter(prefix="/api", tags=["sessions"])


async def get_current_session():
    """Get the current active session (not ended)."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_settings():
    """Get current settings."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM settings WHERE id = 1")
        row = await cursor.fetchone()
        return dict(row)


async def get_app_state():
    """Get current app state."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM app_state WHERE id = 1")
        row = await cursor.fetchone()
        return dict(row)


async def set_break(duration_minutes: int):
    """Set break until time."""
    break_until = datetime.now() + timedelta(minutes=duration_minutes)
    async with get_db() as db:
        await db.execute(
            "UPDATE app_state SET break_until = ? WHERE id = 1",
            (break_until.isoformat(),)
        )
        await db.commit()


async def get_today_session_count():
    """Get number of sessions completed today."""
    today = datetime.now().date().isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT COUNT(*) as count FROM sessions
               WHERE date(started_at) = ? AND ended_at IS NOT NULL""",
            (today,)
        )
        row = await cursor.fetchone()
        return row["count"]


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


async def get_consecutive_personal_count():
    """Get consecutive personal sessions (for rabbit hole detection)."""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT type FROM sessions
               WHERE ended_at IS NOT NULL
               ORDER BY ended_at DESC LIMIT 10"""
        )
        rows = await cursor.fetchall()

        count = 0
        for row in rows:
            if row["type"] == "personal":
                count += 1
            else:
                break
        return count


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

    # Check if can start (evening cutoff, hard max)
    can_start = await check_can_start()
    if not can_start.allowed:
        raise HTTPException(400, can_start.reason)

    # Check if on break
    state = await get_app_state()
    if state["break_until"]:
        break_until = datetime.fromisoformat(state["break_until"])
        if datetime.now() < break_until:
            raise HTTPException(400, "Currently on break")

    async with get_db() as db:
        cursor = await db.execute(
            """INSERT INTO sessions (type, intention, started_at)
               VALUES (?, ?, ?)""",
            (data.type, data.intention, datetime.now().isoformat())
        )
        session_id = cursor.lastrowid
        await db.commit()

        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        return dict(row)


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


@router.post("/sessions/abandon")
async def abandon_session():
    """Abandon the current session without completing."""
    current = await get_current_session()
    if not current:
        raise HTTPException(400, "No active session")

    async with get_db() as db:
        await db.execute("DELETE FROM sessions WHERE id = ?", (current["id"],))
        await db.commit()

    return {"status": "abandoned"}


@router.get("/sessions/current")
async def get_current():
    """Get current session if any."""
    session = await get_current_session()
    if not session:
        return {"active": False}
    return {"active": True, "session": session}


@router.get("/check")
async def check_break() -> BreakCheck:
    """Check if currently on break (for Traefik middleware)."""
    state = await get_app_state()

    if not state["break_until"]:
        return BreakCheck(on_break=False, remaining_seconds=0)

    break_until = datetime.fromisoformat(state["break_until"])
    now = datetime.now()

    if now >= break_until:
        # Break is over, clear it
        async with get_db() as db:
            await db.execute("UPDATE app_state SET break_until = NULL WHERE id = 1")
            await db.commit()
        return BreakCheck(on_break=False, remaining_seconds=0)

    remaining = int((break_until - now).total_seconds())
    return BreakCheck(on_break=True, remaining_seconds=remaining)


@router.get("/auth-check")
async def auth_check():
    """ForwardAuth endpoint for Traefik middleware.

    Returns 200 if not on break (allow request).
    Returns 302 redirect to balance break page if on break (block request).
    """
    state = await get_app_state()

    if not state["break_until"]:
        return Response(status_code=200)

    break_until = datetime.fromisoformat(state["break_until"])
    now = datetime.now()

    if now >= break_until:
        # Break is over, clear it
        async with get_db() as db:
            await db.execute("UPDATE app_state SET break_until = NULL WHERE id = 1")
            await db.commit()
        return Response(status_code=200)

    # On break - redirect to balance break page
    return Response(
        status_code=302,
        headers={"Location": "https://balance.gstoehl.dev/"}
    )


@router.get("/can-start")
async def check_can_start() -> CanStart:
    """Check if a new session can be started."""
    settings = await get_settings()

    # Check evening cutoff
    now = datetime.now()
    cutoff_hour, cutoff_min = map(int, settings["evening_cutoff"].split(":"))
    cutoff_time = now.replace(hour=cutoff_hour, minute=cutoff_min, second=0)

    if now >= cutoff_time:
        return CanStart(allowed=False, reason=f"Evening cutoff ({settings['evening_cutoff']})")

    # Check hard max
    today_count = await get_today_session_count()
    if today_count >= settings["hard_max"]:
        return CanStart(allowed=False, reason=f"Daily maximum reached ({settings['hard_max']})")

    return CanStart(allowed=True)


@router.get("/sessions/today")
async def get_today_sessions():
    """Get all sessions from today."""
    today = datetime.now().date().isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT * FROM sessions WHERE date(started_at) = ? ORDER BY started_at""",
            (today,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@router.get("/sessions/rabbit-hole-check")
async def check_rabbit_hole():
    """Check if rabbit hole alert should show."""
    settings = await get_settings()
    count = await get_consecutive_personal_count()

    return {
        "should_alert": count >= settings["rabbit_hole_check"],
        "consecutive_count": count,
        "threshold": settings["rabbit_hole_check"]
    }


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


@router.get("/status")
async def get_full_status():
    """Get complete timer status with server timestamp for accurate sync.

    This endpoint is the source of truth for client-side timer calculations.
    Returns server_timestamp so client can calculate time offset.
    """
    now = datetime.now()
    server_timestamp = now.timestamp()

    # Check break status
    state = await get_app_state()
    settings = await get_settings()

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

    if state["break_until"]:
        break_until = datetime.fromisoformat(state["break_until"])
        if now < break_until:
            remaining = int((break_until - now).total_seconds())
            return {
                "mode": "break",
                "remaining_seconds": remaining,
                "end_timestamp": break_until.timestamp(),
                "server_timestamp": server_timestamp,
                "total_duration": settings["short_break"] * 60,  # Could be long break
            }
        else:
            # Break expired, clear it
            async with get_db() as db:
                await db.execute("UPDATE app_state SET break_until = NULL WHERE id = 1")
                await db.commit()

    # Check for active session
    session = await get_current_session()
    if session:
        started_at = datetime.fromisoformat(session["started_at"])
        session_duration = settings["session_duration"] * 60
        end_time = started_at + timedelta(seconds=session_duration)

        if now < end_time:
            remaining = int((end_time - now).total_seconds())
            return {
                "mode": "session",
                "remaining_seconds": remaining,
                "end_timestamp": end_time.timestamp(),
                "server_timestamp": server_timestamp,
                "total_duration": session_duration,
                "session": {
                    "id": session["id"],
                    "type": session["type"],
                    "intention": session["intention"],
                    "started_at": session["started_at"],
                }
            }
        else:
            # Session expired - should show end page
            return {
                "mode": "session_ended",
                "remaining_seconds": 0,
                "end_timestamp": end_time.timestamp(),
                "server_timestamp": server_timestamp,
                "total_duration": session_duration,
                "session": {
                    "id": session["id"],
                    "type": session["type"],
                    "intention": session["intention"],
                    "started_at": session["started_at"],
                }
            }

    # Idle - no active session or break
    return {
        "mode": "idle",
        "remaining_seconds": settings["session_duration"] * 60,
        "end_timestamp": None,
        "server_timestamp": server_timestamp,
        "total_duration": settings["session_duration"] * 60,
    }
