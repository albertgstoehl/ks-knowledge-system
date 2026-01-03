from fastapi import APIRouter

from ..database import get_db
from ..models import NextUp, NextUpList

router = APIRouter(prefix="/api/nextup", tags=["nextup"])

MAX_ITEMS = 5


@router.get("", response_model=NextUpList)
async def list_nextup() -> NextUpList:
    """List all Next Up items, sorted by due_date (nulls last), then created_at."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT n.id, n.text, n.due_date, n.priority_id, n.created_at,
                   p.name as priority_name,
                   COUNT(s.id) as session_count
            FROM next_up n
            LEFT JOIN priorities p ON p.id = n.priority_id
            LEFT JOIN sessions s ON s.next_up_id = n.id
            GROUP BY n.id
            ORDER BY
                n.due_date IS NULL,
                n.due_date,
                n.created_at
        """)
        rows = await cursor.fetchall()
        items = [
            NextUp(
                id=row[0],
                text=row[1],
                due_date=row[2],
                priority_id=row[3],
                created_at=row[4],
                priority_name=row[5],
                session_count=row[6]
            )
            for row in rows
        ]
        return NextUpList(items=items, count=len(items), max=MAX_ITEMS)
