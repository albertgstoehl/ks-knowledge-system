from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models import Session, Exercise, SetEntry

router = APIRouter(prefix="/api/sets", tags=["sets"])


class SetCreate(BaseModel):
    session_id: int
    exercise_name: str
    weight: float
    reps: int
    rir: int | None = None


@router.post("")
async def create_set(payload: SetCreate, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Exercise).where(Exercise.name == payload.exercise_name))
    exercise = result.scalars().first()
    if not exercise:
        exercise = Exercise(name=payload.exercise_name)
        session.add(exercise)
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
