from fastapi import APIRouter, HTTPException
from datetime import datetime, date

from ..database import get_db
from ..models import MeditationLog, ExerciseLog, PulseLog

router = APIRouter(prefix="/api", tags=["logging"])


def get_time_of_day(dt: datetime = None) -> str:
    """Derive time of day from datetime."""
    if dt is None:
        dt = datetime.now()
    hour = dt.hour
    if hour < 12:
        return "morning"
    elif hour < 17:
        return "afternoon"
    else:
        return "evening"


@router.post("/meditation")
async def log_meditation(data: MeditationLog):
    """Log a meditation session."""
    now = datetime.now()
    occurred_at = data.occurred_at or now
    time_of_day = data.time_of_day or get_time_of_day(occurred_at)

    async with get_db() as db:
        cursor = await db.execute(
            """INSERT INTO meditation (logged_at, occurred_at, time_of_day, duration_minutes)
               VALUES (?, ?, ?, ?)""",
            (now.isoformat(), occurred_at.isoformat(), time_of_day, data.duration_minutes)
        )
        meditation_id = cursor.lastrowid
        await db.commit()

        cursor = await db.execute("SELECT * FROM meditation WHERE id = ?", (meditation_id,))
        row = await cursor.fetchone()
        return dict(row)


@router.get("/meditation")
async def get_meditation_logs(days: int = 7):
    """Get meditation logs for the past N days."""
    cutoff = datetime.now().date().isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT * FROM meditation
               WHERE date(logged_at) >= date(?, '-' || ? || ' days')
               ORDER BY logged_at DESC""",
            (cutoff, days)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@router.post("/exercise")
async def log_exercise(data: ExerciseLog):
    """Log an exercise session."""
    now = datetime.now()

    async with get_db() as db:
        cursor = await db.execute(
            """INSERT INTO exercise (logged_at, type, duration_minutes, intensity)
               VALUES (?, ?, ?, ?)""",
            (now.isoformat(), data.type, data.duration_minutes, data.intensity)
        )
        exercise_id = cursor.lastrowid
        await db.commit()

        cursor = await db.execute("SELECT * FROM exercise WHERE id = ?", (exercise_id,))
        row = await cursor.fetchone()
        return dict(row)


@router.get("/exercise")
async def get_exercise_logs(days: int = 7):
    """Get exercise logs for the past N days."""
    cutoff = datetime.now().date().isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT * FROM exercise
               WHERE date(logged_at) >= date(?, '-' || ? || ' days')
               ORDER BY logged_at DESC""",
            (cutoff, days)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@router.post("/pulse")
async def log_pulse(data: PulseLog):
    """Log daily pulse (mood and connection)."""
    today = date.today().isoformat()

    async with get_db() as db:
        # Check if already logged today
        cursor = await db.execute(
            "SELECT id FROM daily_pulse WHERE date = ?", (today,)
        )
        existing = await cursor.fetchone()

        if existing:
            # Update existing
            await db.execute(
                """UPDATE daily_pulse
                   SET feeling = ?, had_connection = ?, connection_type = ?
                   WHERE date = ?""",
                (data.feeling, data.had_connection, data.connection_type, today)
            )
            pulse_id = existing["id"]
        else:
            # Create new
            cursor = await db.execute(
                """INSERT INTO daily_pulse (date, feeling, had_connection, connection_type)
                   VALUES (?, ?, ?, ?)""",
                (today, data.feeling, data.had_connection, data.connection_type)
            )
            pulse_id = cursor.lastrowid

        await db.commit()

        cursor = await db.execute("SELECT * FROM daily_pulse WHERE id = ?", (pulse_id,))
        row = await cursor.fetchone()
        return dict(row)


@router.get("/pulse")
async def get_pulse_logs(days: int = 7):
    """Get pulse logs for the past N days."""
    today = date.today().isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT * FROM daily_pulse
               WHERE date >= date(?, '-' || ? || ' days')
               ORDER BY date DESC""",
            (today, days)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@router.get("/pulse/today")
async def get_today_pulse():
    """Get today's pulse if logged."""
    today = date.today().isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM daily_pulse WHERE date = ?", (today,)
        )
        row = await cursor.fetchone()
        if row:
            return {"logged": True, "pulse": dict(row)}
        return {"logged": False}


@router.get("/stats/week")
async def get_week_stats():
    """Get this week's activity summary."""
    today = date.today().isoformat()
    async with get_db() as db:
        # Meditation stats
        cursor = await db.execute(
            """SELECT COUNT(*) as count, COALESCE(SUM(duration_minutes), 0) as total_minutes
               FROM meditation
               WHERE date(logged_at) >= date(?, '-7 days')""",
            (today,)
        )
        med_row = await cursor.fetchone()

        # Exercise stats
        cursor = await db.execute(
            """SELECT COUNT(*) as count, COALESCE(SUM(duration_minutes), 0) as total_minutes
               FROM exercise
               WHERE date(logged_at) >= date(?, '-7 days')""",
            (today,)
        )
        ex_row = await cursor.fetchone()

        # Session stats
        cursor = await db.execute(
            """SELECT COUNT(*) as count,
                      SUM(CASE WHEN type = 'expected' THEN 1 ELSE 0 END) as expected,
                      SUM(CASE WHEN type = 'personal' THEN 1 ELSE 0 END) as personal
               FROM sessions
               WHERE date(started_at) >= date(?, '-7 days') AND ended_at IS NOT NULL""",
            (today,)
        )
        sess_row = await cursor.fetchone()

        return {
            "meditation_count": med_row["count"],
            "meditation_minutes": med_row["total_minutes"],
            "exercise_count": ex_row["count"],
            "exercise_minutes": ex_row["total_minutes"],
            "session_count": sess_row["count"],
            "expected_sessions": sess_row["expected"] or 0,
            "personal_sessions": sess_row["personal"] or 0
        }


@router.get("/stats/today")
async def get_today_stats():
    """Get today's activity summary."""
    today = date.today().isoformat()
    async with get_db() as db:
        # Sessions
        cursor = await db.execute(
            """SELECT COUNT(*) as count,
                      SUM(CASE WHEN type = 'expected' THEN 1 ELSE 0 END) as expected,
                      SUM(CASE WHEN type = 'personal' THEN 1 ELSE 0 END) as personal
               FROM sessions
               WHERE date(started_at) = ? AND ended_at IS NOT NULL""",
            (today,)
        )
        sess_row = await cursor.fetchone()

        # Meditation
        cursor = await db.execute(
            """SELECT COALESCE(SUM(duration_minutes), 0) as total
               FROM meditation WHERE date(logged_at) = ?""",
            (today,)
        )
        med_row = await cursor.fetchone()

        # Exercise
        cursor = await db.execute(
            """SELECT COALESCE(SUM(duration_minutes), 0) as total
               FROM exercise WHERE date(logged_at) = ?""",
            (today,)
        )
        ex_row = await cursor.fetchone()

        return {
            "sessions": sess_row["count"],
            "expected": sess_row["expected"] or 0,
            "personal": sess_row["personal"] or 0,
            "meditation_minutes": med_row["total"],
            "exercise_minutes": ex_row["total"]
        }


@router.get("/stats/month")
async def get_month_stats():
    """Get this month's activity summary."""
    today = date.today().isoformat()
    async with get_db() as db:
        # Meditation stats
        cursor = await db.execute(
            """SELECT COUNT(*) as count, COALESCE(SUM(duration_minutes), 0) as total_minutes
               FROM meditation
               WHERE date(logged_at) >= date(?, '-30 days')""",
            (today,)
        )
        med_row = await cursor.fetchone()

        # Exercise stats
        cursor = await db.execute(
            """SELECT COUNT(*) as count, COALESCE(SUM(duration_minutes), 0) as total_minutes
               FROM exercise
               WHERE date(logged_at) >= date(?, '-30 days')""",
            (today,)
        )
        ex_row = await cursor.fetchone()

        # Session stats
        cursor = await db.execute(
            """SELECT COUNT(*) as count,
                      SUM(CASE WHEN type = 'expected' THEN 1 ELSE 0 END) as expected,
                      SUM(CASE WHEN type = 'personal' THEN 1 ELSE 0 END) as personal
               FROM sessions
               WHERE date(started_at) >= date(?, '-30 days') AND ended_at IS NOT NULL""",
            (today,)
        )
        sess_row = await cursor.fetchone()

        return {
            "meditation_count": med_row["count"],
            "meditation_minutes": med_row["total_minutes"],
            "exercise_count": ex_row["count"],
            "exercise_minutes": ex_row["total_minutes"],
            "session_count": sess_row["count"],
            "expected_sessions": sess_row["expected"] or 0,
            "personal_sessions": sess_row["personal"] or 0
        }
