# balance/src/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import logging

from .database import get_db

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def get_settings(db):
    """Get current settings."""
    cursor = await db.execute("SELECT * FROM settings WHERE id = 1")
    row = await cursor.fetchone()
    return dict(row)


async def ensure_youtube_blocked(db_url: str = None):
    """Ensure YouTube is blocked unless there's an active YouTube session.

    Called on startup to enforce default-blocked state.
    """
    try:
        async with get_db(db_url) as db:
            # Check for active YouTube session
            cursor = await db.execute("""
                SELECT id FROM sessions
                WHERE type = 'youtube' AND ended_at IS NULL
            """)
            active_youtube = await cursor.fetchone()

            if not active_youtube:
                try:
                    from .services.nextdns import get_nextdns_service, NextDNSError
                    nextdns = get_nextdns_service()
                    await nextdns.block_youtube()
                    logger.info("Startup: YouTube blocked (no active session)")
                except ValueError:
                    logger.warning("NextDNS not configured, skipping startup block")
                except Exception as e:
                    logger.error(f"Failed to block YouTube on startup: {e}")
            else:
                logger.info(f"Startup: Active YouTube session {active_youtube['id']}, keeping unblocked")
    except Exception as e:
        logger.error(f"Error ensuring YouTube blocked: {e}")


async def check_expired_sessions(db_url: str = None):
    """Check for ALL expired sessions, end them, and set breaks.

    This ensures breaks are enforced even if the browser is closed mid-session.
    For YouTube sessions, also blocks YouTube via NextDNS.
    """
    try:
        async with get_db(db_url) as db:
            settings = await get_settings(db)
            default_duration = settings["session_duration"]  # minutes
            short_break = settings["short_break"]

            # Find all active sessions (no ended_at)
            cursor = await db.execute("""
                SELECT id, type, started_at, duration_minutes
                FROM sessions
                WHERE ended_at IS NULL
            """)
            sessions = await cursor.fetchall()

            now = datetime.now()
            for session in sessions:
                started = datetime.fromisoformat(session["started_at"])

                # YouTube uses custom duration, others use default
                if session["duration_minutes"]:
                    duration_mins = session["duration_minutes"]
                else:
                    duration_mins = default_duration

                end_time = started + timedelta(minutes=duration_mins)

                if now >= end_time:
                    logger.info(f"Session {session['id']} ({session['type']}) expired, enforcing end")

                    # For YouTube: block via NextDNS
                    if session["type"] == "youtube":
                        try:
                            from .services.nextdns import get_nextdns_service, NextDNSError
                            nextdns = get_nextdns_service()
                            await nextdns.block_youtube()
                            logger.info(f"Blocked YouTube for expired session {session['id']}")
                        except ValueError:
                            logger.warning("NextDNS not configured, skipping block")
                        except Exception as e:
                            logger.error(f"Failed to block YouTube: {e}")

                    # Mark session as ended
                    await db.execute(
                        "UPDATE sessions SET ended_at = ? WHERE id = ?",
                        (now.isoformat(), session["id"])
                    )

                    # Set break ONLY if not already set (timer-complete may have set it)
                    cursor = await db.execute("SELECT break_until FROM app_state WHERE id = 1")
                    state = await cursor.fetchone()
                    existing_break = state["break_until"] if state else None

                    if existing_break:
                        existing_break_time = datetime.fromisoformat(existing_break)
                        if existing_break_time > now:
                            # Break already running from timer-complete, don't overwrite
                            logger.info(f"Session {session['id']} ended, break already set until {existing_break}")
                        else:
                            # Old break expired, set new one
                            break_until = now + timedelta(minutes=short_break)
                            await db.execute(
                                "UPDATE app_state SET break_until = ? WHERE id = 1",
                                (break_until.isoformat(),)
                            )
                            logger.info(f"Break set until {break_until.isoformat()}")
                    else:
                        # No break set, set one
                        break_until = now + timedelta(minutes=short_break)
                        await db.execute(
                            "UPDATE app_state SET break_until = ? WHERE id = 1",
                            (break_until.isoformat(),)
                        )
                        logger.info(f"Break set until {break_until.isoformat()}")

                    await db.commit()
    except Exception as e:
        logger.error(f"Error checking expired sessions: {e}")


async def check_evening_cutoff(db_url: str = None):
    """Check if evening cutoff has passed and set evening mode."""
    try:
        async with get_db(db_url) as db:
            cursor = await db.execute("SELECT evening_cutoff FROM settings WHERE id = 1")
            row = await cursor.fetchone()
            if not row:
                return

            cutoff_str = row["evening_cutoff"]
            cutoff_hour, cutoff_min = map(int, cutoff_str.split(":"))

            now = datetime.now()
            cutoff_time = now.replace(hour=cutoff_hour, minute=cutoff_min, second=0, microsecond=0)

            if now >= cutoff_time:
                # Check if already in evening mode today
                cursor = await db.execute("SELECT check_in_mode FROM app_state WHERE id = 1")
                state = await cursor.fetchone()
                if not state["check_in_mode"]:
                    await db.execute(
                        "UPDATE app_state SET check_in_mode = TRUE WHERE id = 1"
                    )
                    await db.commit()
                    logger.info("Evening cutoff reached, enabled check-in mode")
    except Exception as e:
        logger.error(f"Error checking evening cutoff: {e}")


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(
        check_expired_sessions,
        IntervalTrigger(seconds=30),
        id="session_expiry_check",
        replace_existing=True
    )
    scheduler.add_job(
        check_evening_cutoff,
        IntervalTrigger(minutes=1),
        id="evening_cutoff_check",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started with session expiry (30s) and evening cutoff (1m) checks")


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")
