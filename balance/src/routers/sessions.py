from fastapi import APIRouter, HTTPException, Response
from datetime import datetime, timedelta
import logging
import os

from ..database import get_db
import json

logger = logging.getLogger(__name__)
_DEBUG_BREAK = os.getenv("BALANCE_DEBUG_BREAK") == "1"


def _debug_break(msg: str):
    if _DEBUG_BREAK:
        logger.info(msg)

from ..models import (
    SessionStart, SessionEnd, Session,
    BreakCheck, CanStart,
    SessionActiveResponse, SessionInfo,
    QuickStartRequest, QuickStartResponse,
    MarkClaudeUsedResponse,
    SessionAnalysisCreate
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

    # Validate youtube-specific requirements
    if data.type == "youtube":
        if not data.duration_minutes:
            raise HTTPException(400, "YouTube sessions require duration_minutes")
        if data.duration_minutes not in (15, 30, 45, 60):
            raise HTTPException(400, "Duration must be 15, 30, 45, or 60 minutes")

        # Unblock YouTube via NextDNS (skip if not configured)
        try:
            from ..services.nextdns import get_nextdns_service
            nextdns = get_nextdns_service()
            await nextdns.unblock_youtube()
        except ValueError:
            pass  # NextDNS not configured, skip
        except Exception as e:
            raise HTTPException(500, f"Failed to unlock YouTube: {str(e)}")

    async with get_db() as db:
        cursor = await db.execute(
            """INSERT INTO sessions (type, intention, priority_id, next_up_id, duration_minutes, started_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (data.type, data.intention, data.priority_id, data.next_up_id, data.duration_minutes, datetime.now().isoformat())
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
        # Find most recent session that needs questionnaire data
        # This handles both:
        # 1. Active session (ended_at IS NULL) - normal case
        # 2. Session ended by scheduler (ended_at set, but did_the_thing IS NULL)
        cursor = await db.execute(
            """SELECT id, type FROM sessions
               WHERE did_the_thing IS NULL
               ORDER BY started_at DESC LIMIT 1"""
        )
        current = await cursor.fetchone()

        if not current:
            raise HTTPException(400, "No session awaiting questionnaire")

        session_id = current[0]

        # Update session with questionnaire answers (set ended_at if not already set)
        await db.execute(
            """UPDATE sessions
               SET ended_at = COALESCE(ended_at, ?),
                   distractions = ?, did_the_thing = ?, rabbit_hole = ?
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
            _debug_break(f"/api/sessions/end rabbit_hole=True extend break_until={new_break_until.isoformat()}")

        await db.commit()

    return {"status": "ok", "session_id": session_id}


@router.post("/sessions/timer-complete")
async def timer_complete():
    """Called when session timer hits 0. Starts break immediately."""
    # Get current session (may have been ended by scheduler, check for missing questionnaire)
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT id, type FROM sessions
               WHERE did_the_thing IS NULL
               ORDER BY started_at DESC LIMIT 1"""
        )
        current = await cursor.fetchone()

        if not current:
            raise HTTPException(400, "No session awaiting completion")

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
    _debug_break(
        f"/api/sessions/timer-complete set break_until={break_until.isoformat()} "
        f"duration={break_duration} is_long_break={is_long_break} cycle_position={cycle_position}"
    )

    return {
        "break_duration": break_duration,
        "cycle_position": cycle_position,
        "is_long_break": is_long_break,
        "break_until": break_until.isoformat(),
        "break_until_ts": int(break_until.timestamp())
    }


@router.post("/sessions/abandon")
async def abandon_session():
    """Abandon the current session without completing."""
    current = await get_current_session()
    if not current:
        raise HTTPException(400, "No active session")

    # Block YouTube if abandoning a YouTube session
    if current["type"] == "youtube":
        try:
            from ..services.nextdns import get_nextdns_service
            nextdns = get_nextdns_service()
            await nextdns.block_youtube()
        except ValueError:
            pass  # NextDNS not configured
        except Exception as e:
            logger.error(f"Failed to block YouTube on abandon: {e}")

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

    # Calculate remaining time (YouTube uses custom duration)
    settings = await get_settings()
    started_at = datetime.fromisoformat(session["started_at"])
    if session.get("duration_minutes"):
        session_duration = session["duration_minutes"] * 60
    else:
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
    _debug_break(
        f"/api/status enter now={now.isoformat()} break_until={state['break_until']}"
    )

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
            _debug_break(
                f"/api/status mode=session_ended (break running, questionnaire pending) "
                f"remaining={remaining} break_until={state['break_until']}"
            )
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
            _debug_break(
                f"/api/status mode=break remaining={remaining} break_until={state['break_until']}"
            )
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
            _debug_break("/api/status break expired -> cleared break_until")

    # Check for active session
    session = await get_current_session()
    if session:
        started_at = datetime.fromisoformat(session["started_at"])
        # YouTube uses custom duration, others use default
        if session.get("duration_minutes"):
            session_duration = session["duration_minutes"] * 60
        else:
            session_duration = settings["session_duration"] * 60
        end_time = started_at + timedelta(seconds=session_duration)

        if now < end_time:
            remaining = int((end_time - now).total_seconds())
            _debug_break(
                f"/api/status mode=session remaining={remaining} session_id={session['id']}"
            )
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
            _debug_break(
                f"/api/status mode=session_ended (session expired) session_id={session['id']}"
            )
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
    _debug_break("/api/status mode=idle")
    return {
        "mode": "idle",
        "remaining_seconds": settings["session_duration"] * 60,
        "end_timestamp": None,
        "server_timestamp": server_timestamp,
        "total_duration": settings["session_duration"] * 60,
    }


@router.get("/stats/drift")
async def get_drift_stats():
    """Get priority drift statistics for the current week."""
    async with get_db() as db:
        # Get priorities
        cursor = await db.execute("""
            SELECT id, name, rank FROM priorities
            WHERE archived_at IS NULL ORDER BY rank
        """)
        priorities = await cursor.fetchall()

        if len(priorities) < 2:
            return {"biggest_drift": None, "breakdown": [], "weeks_drifting": 0}

        # Get session counts per priority (this week)
        week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        cursor = await db.execute("""
            SELECT priority_id, COUNT(*) as count
            FROM sessions
            WHERE type = 'expected'
              AND priority_id IS NOT NULL
              AND started_at >= ?
            GROUP BY priority_id
        """, (week_start,))
        counts = {row[0]: row[1] for row in await cursor.fetchall()}

        total = sum(counts.values()) or 1

        # Build breakdown
        breakdown = []
        for p_id, p_name, p_rank in priorities:
            count = counts.get(p_id, 0)
            pct = round(count / total * 100) if total > 0 else 0
            breakdown.append({
                "id": p_id,
                "name": p_name,
                "rank": p_rank,
                "session_count": count,
                "pct": pct
            })

        # Find biggest drift (#1 priority should have most sessions)
        biggest_drift = None
        if breakdown:
            by_rank = sorted(breakdown, key=lambda x: x["rank"])
            by_pct = sorted(breakdown, key=lambda x: x["pct"], reverse=True)

            if by_rank[0]["id"] != by_pct[0]["id"]:
                biggest_drift = {
                    "priority": by_rank[0]["name"],
                    "rank": by_rank[0]["rank"],
                    "pct": by_rank[0]["pct"],
                    "instead": by_pct[0]["name"],
                    "instead_rank": by_pct[0]["rank"],
                    "instead_pct": by_pct[0]["pct"]
                }

        return {
            "biggest_drift": biggest_drift,
            "breakdown": breakdown,
            "weeks_drifting": 0  # TODO: track consecutive weeks
        }


@router.get("/sessions/unanalyzed")
async def get_unanalyzed_sessions():
    """Get sessions with claude_used=true that haven't been analyzed."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT s.id, s.type, s.intention, s.priority_id,
                   s.started_at, s.ended_at,
                   p.name as priority_name, p.rank as priority_rank
            FROM sessions s
            LEFT JOIN priorities p ON s.priority_id = p.id
            LEFT JOIN session_analyses sa ON s.id = sa.session_id
            WHERE s.claude_used = 1
              AND s.ended_at IS NOT NULL
              AND sa.id IS NULL
            ORDER BY s.started_at DESC
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@router.post("/sessions/{session_id}/analysis")
async def store_session_analysis(session_id: int, data: SessionAnalysisCreate):
    """Store analysis results for a session."""
    async with get_db() as db:
        now = datetime.now().isoformat()
        cursor = await db.execute(
            """INSERT INTO session_analyses (
                session_id, analyzed_at, projects_used, prompt_count,
                intention_alignment, alignment_detail, scope_behavior,
                scope_detail, project_switches, tool_appropriate_count,
                tool_questionable_count, tool_questionable_examples,
                red_flags, one_line_summary, severity, raw_response
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id, now,
                json.dumps(data.projects_used), data.prompt_count,
                data.intention_alignment, data.alignment_detail,
                data.scope_behavior, data.scope_detail, data.project_switches,
                data.tool_appropriate_count, data.tool_questionable_count,
                json.dumps(data.tool_questionable_examples),
                json.dumps(data.red_flags), data.one_line_summary,
                data.severity, data.raw_response
            )
        )
        await db.commit()
        return {"id": cursor.lastrowid, "session_id": session_id}


@router.get("/stats/effectiveness")
async def get_effectiveness_stats():
    """Get aggregated effectiveness stats from last 7 days."""
    async with get_db() as db:
        # Get last 7 days of analyses
        week_start = (datetime.now() - timedelta(days=7)).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        cursor = await db.execute("""
            SELECT intention_alignment, scope_behavior, red_flags,
                   tool_questionable_count, one_line_summary, session_id
            FROM session_analyses
            WHERE analyzed_at >= ?
            ORDER BY analyzed_at DESC
        """, (week_start,))
        rows = await cursor.fetchall()

        if not rows:
            return {
                "total_analyzed": 0,
                "alignment_breakdown": {},
                "scope_breakdown": {},
                "avg_questionable_prompts": 0,
                "common_red_flags": [],
                "recent_summaries": []
            }

        # Count alignments
        alignment_counts = {}
        scope_counts = {}
        total_questionable = 0
        all_flags = []
        summaries = []

        for row in rows:
            alignment = row[0]
            scope = row[1]
            flags = json.loads(row[2]) if row[2] else []
            questionable = row[3] or 0
            summary = row[4]
            session_id = row[5]

            alignment_counts[alignment] = alignment_counts.get(alignment, 0) + 1
            scope_counts[scope] = scope_counts.get(scope, 0) + 1
            total_questionable += questionable
            all_flags.extend(flags)
            if summary:
                summaries.append({"session_id": session_id, "summary": summary})

        # Count flag occurrences
        flag_counts = {}
        for flag in all_flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1

        common_flags = sorted(
            [{"flag": k, "count": v} for k, v in flag_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:5]

        return {
            "total_analyzed": len(rows),
            "alignment_breakdown": alignment_counts,
            "scope_breakdown": scope_counts,
            "avg_questionable_prompts": round(total_questionable / len(rows), 1),
            "common_red_flags": common_flags,
            "recent_summaries": summaries[:3]
        }
