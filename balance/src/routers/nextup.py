from fastapi import APIRouter, HTTPException

from ..database import get_db
from ..models import NextUp, NextUpList, NextUpCreate

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


@router.post("", response_model=NextUp)
async def create_nextup(data: NextUpCreate) -> NextUp:
    """Create a new Next Up item. Fails if already at max capacity."""
    async with get_db() as db:
        # Check count
        cursor = await db.execute("SELECT COUNT(*) FROM next_up")
        count = (await cursor.fetchone())[0]
        if count >= MAX_ITEMS:
            raise HTTPException(status_code=400, detail=f"Maximum {MAX_ITEMS} items allowed")

        # Validate priority if provided
        priority_name = None
        if data.priority_id:
            cursor = await db.execute(
                "SELECT name FROM priorities WHERE id = ? AND archived_at IS NULL",
                (data.priority_id,)
            )
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="Priority not found")
            priority_name = row[0]

        # Insert
        cursor = await db.execute(
            "INSERT INTO next_up (text, due_date, priority_id) VALUES (?, ?, ?)",
            (data.text, data.due_date, data.priority_id)
        )
        await db.commit()
        item_id = cursor.lastrowid

        # Fetch created item
        cursor = await db.execute(
            "SELECT id, text, due_date, priority_id, created_at FROM next_up WHERE id = ?",
            (item_id,)
        )
        row = await cursor.fetchone()

        return NextUp(
            id=row[0],
            text=row[1],
            due_date=row[2],
            priority_id=row[3],
            created_at=row[4],
            priority_name=priority_name,
            session_count=0
        )
