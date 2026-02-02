"""SQLite-backed rate limiting."""

import os
import time
from pathlib import Path

import aiosqlite

DB_PATH: Path = None


def _get_db_path() -> Path:
    """Get database path, allowing override for tests."""
    return Path(os.getenv("GATEWAY_DB_PATH", "/tmp/gateway/ratelimit.db"))


async def init_ratelimit_db() -> None:
    """Initialize rate limit database."""
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS rate_limits (
                key TEXT PRIMARY KEY,
                count INTEGER DEFAULT 0,
                window_start REAL
            )
            """
        )
        await db.commit()


async def check_rate_limit(
    endpoint: str,
    client_id: str,
    limit: int,
    window_seconds: int,
) -> bool:
    """
    Check if request is allowed under rate limit.

    Returns True if allowed, False if rate limited.
    """
    db_path = _get_db_path()
    key = f"{endpoint}:{client_id}"
    now = time.time()

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT count, window_start FROM rate_limits WHERE key = ?",
            (key,),
        )
        row = await cursor.fetchone()

        if row is None:
            await db.execute(
                "INSERT INTO rate_limits (key, count, window_start) VALUES (?, 1, ?)",
                (key, now),
            )
            await db.commit()
            return True

        count, window_start = row

        if now - window_start > window_seconds:
            await db.execute(
                "UPDATE rate_limits SET count = 1, window_start = ? WHERE key = ?",
                (now, key),
            )
            await db.commit()
            return True

        if count >= limit:
            return False

        await db.execute(
            "UPDATE rate_limits SET count = count + 1 WHERE key = ?",
            (key,),
        )
        await db.commit()
        return True


def parse_rate_limit(rate_str: str) -> tuple[int, int]:
    """
    Parse rate limit string into (count, seconds).

    Examples:
        "20/hour" -> (20, 3600)
        "100/minute" -> (100, 60)
    """
    count_str, period = rate_str.split("/")
    periods = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }
    return int(count_str), periods.get(period, 3600)
