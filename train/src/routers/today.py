from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import RecoverySummary, Run

router = APIRouter(prefix="/api/today", tags=["today"])


@router.get("")
async def get_today_data(session: AsyncSession = Depends(get_db)):
    """Aggregate all data for TODAY view."""
    today = date.today()
    
    # Get today's recovery data
    recovery_result = await session.execute(
        select(RecoverySummary).where(RecoverySummary.date == today)
    )
    recovery = recovery_result.scalar_one_or_none()
    
    # Get weekly mileage (last 7 days)
    week_ago = today - timedelta(days=7)
    mileage_result = await session.execute(
        select(func.sum(Run.distance_km))
        .where(Run.date >= week_ago)
    )
    weekly_mileage = mileage_result.scalar() or 0
    
    # Get runs this week
    runs_result = await session.execute(
        select(Run)
        .where(Run.date >= week_ago)
        .order_by(Run.date)
    )
    runs_this_week = runs_result.scalars().all()
    
    # Get yesterday's run
    yesterday = today - timedelta(days=1)
    yesterday_result = await session.execute(
        select(Run).where(Run.date == yesterday)
    )
    yesterday_run = yesterday_result.scalar_one_or_none()
    
    # Race date (hardcoded for now, could be in settings)
    race_date = date(2026, 4, 15)  # ~10 weeks from Jan 31
    weeks_to_race = (race_date - today).days // 7
    
    return {
        "marathon": {
            "weeks_to_race": weeks_to_race,
            "readiness_score": recovery.readiness_score if recovery else None,
            "weekly_mileage": round(weekly_mileage, 1),
            "runs_this_week": len(runs_this_week),
            "target_runs_per_week": 3,
        },
        "yesterday_run": {
            "distance_km": yesterday_run.distance_km if yesterday_run else None,
            "pace": f"{int(yesterday_run.duration_minutes / yesterday_run.distance_km)}:{int((yesterday_run.duration_minutes / yesterday_run.distance_km % 1) * 60):02d}/km" if yesterday_run else None,
            "has_notes": yesterday_run.notes is not None if yesterday_run else False,
        } if yesterday_run else None,
        "today_scheduled": {
            "distance_km": 5,  # This would come from current plan
            "pace_range": "6:15-6:30",
            "type": "easy",
        },
    }
