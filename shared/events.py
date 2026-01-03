# shared/events.py
"""Shared event logging helper for analytics across all services."""
import json
from datetime import datetime


async def log_event(db, event_type: str, name: str, metadata: dict = None):
    """Log an analytics event.

    Args:
        db: aiosqlite connection
        event_type: 'funnel' or 'feature'
        name: Event name like 'bookmark_created', 'rss_subscribe'
        metadata: Optional dict of additional context
    """
    await db.execute(
        "INSERT INTO events (timestamp, event_type, name, metadata) VALUES (?, ?, ?, ?)",
        (
            datetime.utcnow().isoformat(),
            event_type,
            name,
            json.dumps(metadata) if metadata else None
        )
    )
    await db.commit()
