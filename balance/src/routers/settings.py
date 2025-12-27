from fastapi import APIRouter
from datetime import datetime

from ..database import get_db
from ..models import Settings, SettingsUpdate, AppState

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
async def get_settings() -> Settings:
    """Get current settings."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM settings WHERE id = 1")
        row = await cursor.fetchone()
        return Settings(**dict(row))


@router.put("/settings")
async def update_settings(data: SettingsUpdate):
    """Update settings and track changes."""
    async with get_db() as db:
        # Get current settings
        cursor = await db.execute("SELECT * FROM settings WHERE id = 1")
        current = dict(await cursor.fetchone())

        # Build update query dynamically
        updates = []
        params = []
        changes = []

        for field, value in data.model_dump(exclude_unset=True).items():
            if value is not None and current.get(field) != value:
                updates.append(f"{field} = ?")
                params.append(value)
                changes.append((field, str(current.get(field)), str(value)))

        if updates:
            # Update settings
            params.append(1)  # WHERE id = 1
            await db.execute(
                f"UPDATE settings SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )

            # Log changes
            now = datetime.now().isoformat()
            for setting, old_val, new_val in changes:
                await db.execute(
                    """INSERT INTO limit_changes (timestamp, setting, old_value, new_value)
                       VALUES (?, ?, ?, ?)""",
                    (now, setting, old_val, new_val)
                )

            await db.commit()

        # Return updated settings
        cursor = await db.execute("SELECT * FROM settings WHERE id = 1")
        row = await cursor.fetchone()
        return Settings(**dict(row))


@router.get("/state")
async def get_state() -> AppState:
    """Get current app state."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM app_state WHERE id = 1")
        row = await cursor.fetchone()
        data = dict(row)
        return AppState(
            break_until=datetime.fromisoformat(data["break_until"]) if data["break_until"] else None,
            check_in_mode=bool(data["check_in_mode"]),
            north_star=data["north_star"]
        )


from pydantic import BaseModel

class NorthStarUpdate(BaseModel):
    north_star: str


@router.put("/state/north-star")
async def update_north_star(data: NorthStarUpdate):
    """Update the north star goal."""
    async with get_db() as db:
        await db.execute(
            "UPDATE app_state SET north_star = ? WHERE id = 1",
            (data.north_star,)
        )
        await db.commit()
        return {"status": "updated", "north_star": data.north_star}


@router.put("/state/pause")
async def pause_tracking(duration_weeks: int = 1, reminder: bool = False):
    """Pause tracking for a period."""
    async with get_db() as db:
        await db.execute(
            "UPDATE app_state SET check_in_mode = 1 WHERE id = 1"
        )
        await db.commit()
        return {
            "status": "paused",
            "duration_weeks": duration_weeks,
            "reminder": reminder,
            "check_in_mode": True
        }


@router.put("/state/resume")
async def resume_tracking():
    """Resume normal tracking from check-in mode."""
    async with get_db() as db:
        await db.execute(
            "UPDATE app_state SET check_in_mode = 0 WHERE id = 1"
        )
        await db.commit()
        return {"status": "resumed", "check_in_mode": False}


@router.get("/limit-changes")
async def get_limit_changes(limit: int = 20):
    """Get history of limit changes."""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT * FROM limit_changes
               ORDER BY timestamp DESC
               LIMIT ?""",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
