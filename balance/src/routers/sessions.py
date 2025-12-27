from fastapi import APIRouter, HTTPException, Response
from datetime import datetime, timedelta

from ..database import get_db
from ..models import (
    SessionStart, SessionEnd, Session,
    BreakCheck, CanStart
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
    """Start a new Pomodoro session."""
    # Check if already in session
    current = await get_current_session()
    if current:
        raise HTTPException(400, "Session already in progress")

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
    """End the current session and start break."""
    current = await get_current_session()
    if not current:
        raise HTTPException(400, "No active session")

    settings = await get_settings()

    # Determine break length (long break every 4th session)
    today_count = await get_today_session_count()
    is_long_break = (today_count + 1) % 4 == 0
    break_duration = settings["long_break"] if is_long_break else settings["short_break"]

    async with get_db() as db:
        await db.execute(
            """UPDATE sessions
               SET ended_at = ?, distractions = ?, did_the_thing = ?, rabbit_hole = ?
               WHERE id = ?""",
            (datetime.now().isoformat(), data.distractions,
             data.did_the_thing, data.rabbit_hole, current["id"])
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (current["id"],))
        row = await cursor.fetchone()

    # Set break
    await set_break(break_duration)

    return dict(row)


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
