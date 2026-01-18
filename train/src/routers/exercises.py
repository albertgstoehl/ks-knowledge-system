from fastapi import APIRouter, Depends
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models import Exercise, SetEntry, Session

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@router.get("")
async def list_exercises(db: AsyncSession = Depends(get_db)):
    """Get all exercises with their most recent set."""
    exercises_result = await db.execute(
        select(Exercise).order_by(Exercise.name)
    )
    exercises = exercises_result.scalars().all()

    result = []
    for exercise in exercises:
        # Get last set for this exercise
        last_set_result = await db.execute(
            select(SetEntry, Session)
            .join(Session, Session.id == SetEntry.session_id)
            .where(SetEntry.exercise_id == exercise.id)
            .order_by(desc(SetEntry.id))
            .limit(1)
        )
        last_set_row = last_set_result.first()

        # Get total sets count
        count_result = await db.execute(
            select(func.count(SetEntry.id)).where(SetEntry.exercise_id == exercise.id)
        )
        total_sets = count_result.scalar() or 0

        exercise_data = {
            "id": exercise.id,
            "name": exercise.name,
            "muscle_groups": exercise.muscle_groups,
            "total_sets": total_sets,
            "last_set": None,
        }

        if last_set_row:
            set_entry, session = last_set_row
            exercise_data["last_set"] = {
                "weight": set_entry.weight,
                "reps": set_entry.reps,
                "rir": set_entry.rir,
                "date": str(session.started_at.date()) if session.started_at else None,
            }

        result.append(exercise_data)

    return result
