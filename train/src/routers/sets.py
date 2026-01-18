from typing import Optional
from fastapi import APIRouter, Depends
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models import Session, Exercise, SetEntry

router = APIRouter(prefix="/api/sets", tags=["sets"])


@router.get("")
async def list_sets(
    session_id: Optional[int] = None,
    exercise_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List sets with optional filters."""
    query = (
        select(SetEntry, Exercise, Session)
        .join(Exercise, Exercise.id == SetEntry.exercise_id)
        .join(Session, Session.id == SetEntry.session_id)
    )

    if session_id:
        query = query.where(SetEntry.session_id == session_id)
    if exercise_name:
        query = query.where(Exercise.name == exercise_name)

    query = query.order_by(desc(SetEntry.id))
    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "id": set_entry.id,
            "session_id": set_entry.session_id,
            "exercise_name": exercise.name,
            "weight": set_entry.weight,
            "reps": set_entry.reps,
            "rir": set_entry.rir,
            "order": set_entry.set_order,
        }
        for set_entry, exercise, session_row in rows
    ]


class SetCreate(BaseModel):
    session_id: int
    exercise_name: str
    weight: float
    reps: int
    rir: int | None = None
    notes: str | None = None
    muscle_groups: list[str] | None = None


@router.post("")
async def create_set(payload: SetCreate, session: AsyncSession = Depends(get_db)):
    import json
    result = await session.execute(select(Exercise).where(Exercise.name == payload.exercise_name))
    exercise = result.scalars().first()
    if not exercise:
        muscle_groups_json = json.dumps(payload.muscle_groups) if payload.muscle_groups else None
        exercise = Exercise(name=payload.exercise_name, muscle_groups=muscle_groups_json)
        session.add(exercise)
        await session.flush()
    elif payload.muscle_groups and not exercise.muscle_groups:
        # Update muscle groups if provided and not already set
        exercise.muscle_groups = json.dumps(payload.muscle_groups)
        await session.flush()

    order_count = await session.execute(
        select(SetEntry).where(SetEntry.session_id == payload.session_id, SetEntry.exercise_id == exercise.id)
    )
    set_order = len(order_count.scalars().all()) + 1

    entry = SetEntry(
        session_id=payload.session_id,
        exercise_id=exercise.id,
        weight=payload.weight,
        reps=payload.reps,
        rir=payload.rir,
        notes=payload.notes,
        set_order=set_order,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)

    return {
        "id": entry.id,
        "session_id": entry.session_id,
        "exercise_name": exercise.name,
        "weight": entry.weight,
        "reps": entry.reps,
        "rir": entry.rir,
        "order": entry.set_order,
    }


@router.get("")
async def list_sets(
    session_id: Optional[int] = None,
    since: Optional[date] = None,
    session: AsyncSession = Depends(get_db),
):
    query = (
        select(SetEntry, Exercise, Session)
        .join(Exercise, Exercise.id == SetEntry.exercise_id)
        .join(Session, Session.id == SetEntry.session_id)
        .order_by(desc(SetEntry.id))
    )

    if session_id:
        query = query.where(SetEntry.session_id == session_id)
    if since:
        query = query.where(Session.started_at >= datetime.combine(since, datetime.min.time()))

    result = await session.execute(query)
    rows = result.all()

    return [
        {
            "id": set_entry.id,
            "session_id": set_entry.session_id,
            "exercise_name": exercise.name,
            "muscle_groups": exercise.muscle_groups,
            "weight": set_entry.weight,
            "reps": set_entry.reps,
            "rir": set_entry.rir,
            "order": set_entry.set_order,
        }
        for set_entry, exercise, session_row in rows
    ]


@router.get("/recent")
async def recent_sets(session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(SetEntry, Exercise, Session)
        .join(Exercise, Exercise.id == SetEntry.exercise_id)
        .join(Session, Session.id == SetEntry.session_id)
        .order_by(desc(SetEntry.id))
        .limit(20)
    )
    rows = result.all()
    return [
        {
            "id": set_entry.id,
            "session_id": set_entry.session_id,
            "exercise_name": exercise.name,
            "weight": set_entry.weight,
            "reps": set_entry.reps,
            "rir": set_entry.rir,
            "order": set_entry.set_order,
        }
        for set_entry, exercise, session_row in rows
    ]
