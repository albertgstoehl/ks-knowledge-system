import json
from collections import defaultdict
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models import Plan, Session, SetEntry, Exercise

router = APIRouter(prefix="/api", tags=["context"])


@router.get("/context")
async def get_context(session: AsyncSession = Depends(get_db)):
    plan_result = await session.execute(select(Plan).order_by(Plan.created_at.desc()))
    plan = plan_result.scalars().first()

    if not plan:
        return {
            "plan": None,
            "sessions": [],
            "sets": [],
            "summary": {
                "weeks_on_plan": 0,
                "total_sessions": 0,
                "volume_by_muscle": {},
            },
        }

    try:
        with open(plan.markdown_path, "r", encoding="utf-8") as file:
            markdown = file.read()
    except FileNotFoundError:
        markdown = ""

    sessions_query = (
        select(Session)
        .where(Session.started_at >= plan.created_at)
        .order_by(Session.started_at.desc())
    )
    sessions_result = await session.execute(sessions_query)
    sessions = sessions_result.scalars().all()

    session_ids = [entry.id for entry in sessions]
    sets_data = []
    volume_by_muscle = defaultdict(int)

    if session_ids:
        sets_query = (
            select(SetEntry, Exercise)
            .join(Exercise, Exercise.id == SetEntry.exercise_id)
            .where(SetEntry.session_id.in_(session_ids))
            .order_by(SetEntry.id)
        )
        sets_result = await session.execute(sets_query)

        for set_entry, exercise in sets_result.all():
            sets_data.append(
                {
                    "session_id": set_entry.session_id,
                    "exercise_name": exercise.name,
                    "weight": set_entry.weight,
                    "reps": set_entry.reps,
                    "rir": set_entry.rir,
                    "notes": set_entry.notes,
                }
            )

            if exercise.muscle_groups:
                try:
                    muscles = json.loads(exercise.muscle_groups)
                    for muscle in muscles:
                        volume_by_muscle[muscle] += 1
                except (json.JSONDecodeError, TypeError):
                    volume_by_muscle[exercise.muscle_groups] += 1

    days_on_plan = (datetime.utcnow() - plan.created_at).days
    weeks_on_plan = max(1, days_on_plan // 7)

    return {
        "plan": {
            "id": plan.id,
            "title": plan.title,
            "markdown": markdown,
            "created_at": str(plan.created_at),
        },
        "sessions": [
            {
                "id": entry.id,
                "started_at": str(entry.started_at),
                "ended_at": str(entry.ended_at) if entry.ended_at else None,
                "template_key": entry.template_key,
                "notes": entry.notes,
                "plan_id": entry.plan_id,
            }
            for entry in sessions
        ],
        "sets": sets_data,
        "summary": {
            "weeks_on_plan": weeks_on_plan,
            "total_sessions": len(sessions),
            "volume_by_muscle": dict(volume_by_muscle),
        },
    }
