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


@router.get("/context")
async def get_health_context(session: AsyncSession = Depends(get_db)):
    """
    Get rich health context for AI-assisted discussions.
    
    This endpoint provides trend data and baseline comparisons
    for use during weekly reviews and training discussions.
    """
    today = date.today()
    
    # 30-day baseline calculation
    days_30_ago = today - timedelta(days=30)
    days_7_ago = today - timedelta(days=7)
    yesterday = today - timedelta(days=1)
    
    # 30-day averages (baseline)
    baseline_result = await session.execute(
        select(
            func.avg(RecoverySummary.sleep_score).label("sleep_avg"),
            func.avg(RecoverySummary.hrv_avg).label("hrv_avg"),
            func.avg(RecoverySummary.resting_hr).label("rhr_avg"),
        )
        .where(RecoverySummary.date >= days_30_ago)
        .where(RecoverySummary.date < today)
    )
    baseline = baseline_result.one()
    
    # Today's values
    today_result = await session.execute(
        select(RecoverySummary).where(RecoverySummary.date == today)
    )
    today_recovery = today_result.scalar_one_or_none()
    
    # Yesterday's values (for day-over-day)
    yesterday_result = await session.execute(
        select(RecoverySummary).where(RecoverySummary.date == yesterday)
    )
    yesterday_recovery = yesterday_result.scalar_one_or_none()
    
    # 7-day training load trend
    runs_week_1 = await session.execute(
        select(func.sum(Run.distance_km))
        .where(Run.date >= days_7_ago)
    )
    runs_week_2 = await session.execute(
        select(func.sum(Run.distance_km))
        .where(Run.date >= days_30_ago + timedelta(days=7))
        .where(Run.date < days_7_ago)
    )
    
    weekly_mileage_current = runs_week_1.scalar() or 0
    weekly_mileage_previous = runs_week_2.scalar() or 0
    
    # Recent runs for pattern analysis
    recent_runs_result = await session.execute(
        select(Run)
        .where(Run.date >= days_7_ago)
        .order_by(Run.date.desc())
    )
    recent_runs = recent_runs_result.scalars().all()
    
    return {
        "user_baseline": {
            "period": "last_30_days",
            "sleep_avg": round(baseline.sleep_avg, 1) if baseline.sleep_avg else None,
            "hrv_avg": round(baseline.hrv_avg, 1) if baseline.hrv_avg else None,
            "rhr_avg": round(baseline.rhr_avg, 1) if baseline.rhr_avg else None,
        },
        "today_vs_baseline": {
            "sleep": _calc_pct_change(today_recovery.sleep_score, baseline.sleep_avg) if today_recovery else None,
            "hrv": _calc_pct_change(today_recovery.hrv_avg, baseline.hrv_avg) if today_recovery else None,
            "rhr": _calc_pct_change(today_recovery.resting_hr, baseline.rhr_avg, invert=True) if today_recovery else None,
        } if today_recovery else None,
        "yesterday_vs_baseline": {
            "sleep": _calc_pct_change(yesterday_recovery.sleep_score, baseline.sleep_avg) if yesterday_recovery else None,
            "hrv": _calc_pct_change(yesterday_recovery.hrv_avg, baseline.hrv_avg) if yesterday_recovery else None,
            "rhr": _calc_pct_change(yesterday_recovery.resting_hr, baseline.rhr_avg, invert=True) if yesterday_recovery else None,
        } if yesterday_recovery else None,
        "training_load": {
            "weekly_mileage_current": round(weekly_mileage_current, 1),
            "weekly_mileage_previous": round(weekly_mileage_previous, 1),
            "trend": "increasing" if weekly_mileage_current > weekly_mileage_previous * 1.1 else ("decreasing" if weekly_mileage_current < weekly_mileage_previous * 0.9 else "stable"),
            "runs_this_week": len(recent_runs),
            "recent_runs": [
                {
                    "date": r.date.isoformat(),
                    "distance_km": r.distance_km,
                    "pace": f"{int(r.duration_minutes / r.distance_km)}:{int((r.duration_minutes / r.distance_km % 1) * 60):02d}",
                    "effort": r.effort,
                }
                for r in recent_runs
            ]
        },
        "marathon": {
            "weeks_to_race": (date(2026, 4, 15) - today).days // 7,
            "race_date": "2026-04-15",
        }
    }


def _calc_pct_change(current, baseline, invert=False):
    """Calculate percentage change from baseline."""
    if current is None or baseline is None or baseline == 0:
        return None
    change = ((current - baseline) / baseline) * 100
    if invert:
        change = -change  # For metrics where lower is better (RHR)
    return f"{change:+.0f}%"
