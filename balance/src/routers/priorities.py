from fastapi import APIRouter

from ..database import get_db
from ..models import Priority

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
