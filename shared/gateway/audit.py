"""Audit logging for gateway requests."""

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

import aiosqlite


def _get_db_path() -> Path:
    """Get database path, allowing override for tests."""
    return Path(os.getenv("GATEWAY_AUDIT_DB_PATH", "/tmp/gateway/audit.db"))


async def init_audit_db() -> None:
    """Initialize audit database."""
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                endpoint TEXT,
                method TEXT,
                client_ip TEXT,
                params TEXT,
                status_code INTEGER,
                error TEXT
            )
            """
        )
        await db.commit()


async def log_request(
    endpoint: str,
    method: str,
    client_ip: str,
    params: dict[str, Any],
    status_code: int,
    error: Optional[str] = None,
) -> None:
    """Log a gateway request."""
    db_path = _get_db_path()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO audit_log
               (timestamp, endpoint, method, client_ip, params, status_code, error)
               VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                time.time(),
                endpoint,
                method,
                client_ip,
                json.dumps(params),
                status_code,
                error,
            ),
        )
        await db.commit()


async def get_recent_logs(limit: int = 100) -> list[dict]:
    """Get recent audit log entries, newest first."""
    db_path = _get_db_path()
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            SELECT timestamp, endpoint, method, client_ip, status_code, error
               FROM audit_log ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "timestamp": row[0],
                "endpoint": row[1],
                "method": row[2],
                "client_ip": row[3],
                "status_code": row[4],
                "error": row[5],
            }
            for row in rows
        ]
