# balance/src/routers/events.py
"""Events API for analytics export."""
from fastapi import APIRouter
from ..database import get_db
import json

router = APIRouter(prefix="/api", tags=["events"])

SERVICE_NAME = "balance"


@router.get("/events")
async def get_events(since: str = None):
    """Get analytics events, optionally filtered by timestamp."""
    query = "SELECT timestamp, event_type, name, metadata FROM events"
    params = ()

    if since:
        query += " WHERE timestamp > ?"
        params = (since,)

    query += " ORDER BY timestamp"

    async with get_db() as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        events = []
        for row in rows:
            events.append({
                "timestamp": row[0],
                "event_type": row[1],
                "name": row[2],
                "metadata": json.loads(row[3]) if row[3] else None
            })

        return {"service": SERVICE_NAME, "events": events}
