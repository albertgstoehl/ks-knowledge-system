from datetime import datetime

from fastapi import APIRouter

from ..database import get_db
from ..models import Priority, PriorityCreate, PriorityReorder

router = APIRouter(prefix="/api", tags=["priorities"])


@router.get("/priorities")
async def list_priorities() -> list[Priority]:
    """List all active priorities ordered by rank."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT p.id, p.name, p.rank,
                   COUNT(s.id) as session_count
            FROM priorities p
            LEFT JOIN sessions s ON s.priority_id = p.id
            WHERE p.archived_at IS NULL
            GROUP BY p.id
            ORDER BY p.rank
        """)
        rows = await cursor.fetchall()
        return [
            Priority(
                id=row[0],
                name=row[1],
                rank=row[2],
                session_count=row[3]
            )
            for row in rows
        ]


@router.post("/priorities")
async def create_priority(data: PriorityCreate) -> Priority:
    """Create a new priority with auto-calculated rank."""
    async with get_db() as db:
        # Get next rank
        cursor = await db.execute(
            "SELECT MAX(rank) FROM priorities WHERE archived_at IS NULL"
        )
        row = await cursor.fetchone()
        next_rank = (row[0] or 0) + 1

        # Insert priority
        cursor = await db.execute(
            """INSERT INTO priorities (name, rank, created_at)
               VALUES (?, ?, ?)""",
            (data.name, next_rank, datetime.now().isoformat())
        )
        await db.commit()
        priority_id = cursor.lastrowid

        return Priority(
            id=priority_id,
            name=data.name,
            rank=next_rank,
            session_count=0
        )


@router.put("/priorities/reorder")
async def reorder_priorities(data: PriorityReorder):
    """Reorder priorities by updating their ranks."""
    async with get_db() as db:
        for rank, priority_id in enumerate(data.order, start=1):
            await db.execute(
                "UPDATE priorities SET rank = ? WHERE id = ?",
                (rank, priority_id)
            )
        await db.commit()
    return {"status": "ok"}
