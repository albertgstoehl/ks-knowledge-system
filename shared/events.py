# shared/events.py
"""Shared event logging helper for analytics across all services."""
import json
from datetime import datetime


async def log_event(db, event_type: str, name: str, metadata: dict = None):
    """Log an analytics event.

    Works with both SQLAlchemy AsyncSession and aiosqlite connections.

    Args:
        db: SQLAlchemy AsyncSession or aiosqlite connection
        event_type: 'funnel' or 'feature'
        name: Event name like 'bookmark_created', 'rss_subscribe'
        metadata: Optional dict of additional context
    """
    timestamp = datetime.utcnow().isoformat()
    metadata_json = json.dumps(metadata) if metadata else None

    # Check if this is a SQLAlchemy session (has 'bind' attribute) or aiosqlite
    if hasattr(db, 'bind'):
        # SQLAlchemy AsyncSession - use text()
        from sqlalchemy import text
        await db.execute(
            text("INSERT INTO events (timestamp, event_type, name, metadata) VALUES (:ts, :et, :n, :m)"),
            {"ts": timestamp, "et": event_type, "n": name, "m": metadata_json}
        )
        await db.commit()
    else:
        # aiosqlite connection - use positional params
        await db.execute(
            "INSERT INTO events (timestamp, event_type, name, metadata) VALUES (?, ?, ?, ?)",
            (timestamp, event_type, name, metadata_json)
        )
        await db.commit()
