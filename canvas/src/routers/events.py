# canvas/src/routers/events.py
"""Events API for analytics export."""
from fastapi import APIRouter
from sqlalchemy import select
from src.database import async_session_maker
from src.models import Event
import json

router = APIRouter(prefix="/api", tags=["events"])

SERVICE_NAME = "canvas"


@router.get("/events")
async def get_events(since: str = None):
    """Get analytics events, optionally filtered by timestamp."""
    async with async_session_maker() as session:
        query = select(Event)

        if since:
            query = query.where(Event.timestamp > since)

        query = query.order_by(Event.timestamp)

        result = await session.execute(query)
        rows = result.scalars().all()

        events = []
        for row in rows:
            timestamp = row.timestamp
            if hasattr(timestamp, 'isoformat'):
                timestamp = timestamp.isoformat()

            events.append({
                "timestamp": timestamp,
                "event_type": row.event_type,
                "name": row.name,
                "metadata": json.loads(row.event_metadata) if row.event_metadata else None
            })

        return {"service": SERVICE_NAME, "events": events}
