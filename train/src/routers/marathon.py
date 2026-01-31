from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import RecoverySummary, Run

router = APIRouter(prefix="/api/marathon", tags=["marathon"])


class WeeklyReviewData(BaseModel):
    week_number: int
    target_miles: float
    actual_miles: float
    long_run_completed: bool
    avg_readiness: int
    hrv_trend: str  # "up", "down", "stable"
    sleep_avg: int


@router.get("/review")
async def get_weekly_review(session: AsyncSession = Depends(get_db)):
    """Get all data needed for weekly review."""
    today = date.today()
    week_ago = today - timedelta(days=7)
    two_weeks_ago = today - timedelta(days=14)
    
    # Weekly mileage
    mileage_result = await session.execute(
        select(func.sum(Run.distance_km))
        .where(Run.date >= week_ago)
    )
    actual_miles = mileage_result.scalar() or 0
    
    # Long run check (assume longest run in week is long run)
    long_run_result = await session.execute(
        select(Run)
        .where(Run.date >= week_ago)
        .order_by(Run.distance_km.desc())
        .limit(1)
    )
    long_run = long_run_result.scalar_one_or_none()
    long_run_completed = long_run is not None and long_run.distance_km >= 8
    
    # Recovery stats
    recovery_result = await session.execute(
        select(
            func.avg(RecoverySummary.readiness_score).label("avg_readiness"),
            func.avg(RecoverySummary.sleep_score).label("avg_sleep"),
            func.avg(RecoverySummary.hrv_avg).label("avg_hrv"),
        )
        .where(RecoverySummary.date >= week_ago)
    )
    recovery = recovery_result.one()
    
    # HRV trend (compare this week vs last week)
    prev_hrv_result = await session.execute(
        select(func.avg(RecoverySummary.hrv_avg))
        .where(RecoverySummary.date >= two_weeks_ago)
        .where(RecoverySummary.date < week_ago)
    )
    prev_hrv = prev_hrv_result.scalar() or recovery.avg_hrv or 0
    
    if recovery.avg_hrv and prev_hrv:
        if recovery.avg_hrv > prev_hrv * 1.05:
            hrv_trend = "up"
        elif recovery.avg_hrv < prev_hrv * 0.95:
            hrv_trend = "down"
        else:
            hrv_trend = "stable"
    else:
        hrv_trend = "unknown"
    
    return {
        "week_number": 3,  # Calculate from plan start date
        "target_miles": 20,  # From current plan
        "actual_miles": round(actual_miles, 1),
        "long_run_completed": long_run_completed,
        "long_run_distance": long_run.distance_km if long_run else 0,
        "avg_readiness": round(recovery.avg_readiness or 0),
        "avg_sleep": round(recovery.avg_sleep or 0),
        "hrv_trend": hrv_trend,
        "runs_completed": 0,  # Count from runs table
    }


class NextWeekPlan(BaseModel):
    target_miles: float
    long_run_distance: float
    easy_pace_range: str
    notes: Optional[str] = None


@router.post("/plan/next")
async def generate_next_week_plan(
    adjustments: NextWeekPlan,
    session: AsyncSession = Depends(get_db)
):
    """Generate next week's plan markdown."""
    # Generate markdown content
    week_num = 4  # Calculate from current
    
    markdown = f"""---
type: marathon-week
created: {date.today().isoformat()}
week_number: {week_num}
---

# Week {week_num} - Marathon Training

## Targets

| Metric | Target |
|--------|--------|
| Weekly mileage | {adjustments.target_miles} km |
| Long run | {adjustments.long_run_distance} km |
| Easy pace | {adjustments.easy_pace_range}/km |

## Schedule

| Day | Run | Distance | Notes |
|-----|-----|----------|-------|
| Tue | Easy | 5km | |
| Thu | Easy | 5km | |
| Sat | Long | {adjustments.long_run_distance}km | |

## Notes

{adjustments.notes or "None"}

## Watch List

- [ ] Knees
- [ ] Sleep quality
- [ ] Energy levels
"""
    
    # Save to file
    import os
    plan_dir = os.path.join(os.path.dirname(__file__), "../../plan")
    os.makedirs(plan_dir, exist_ok=True)
    
    filename = f"{date.today().isoformat()}-marathon-week-{week_num}.md"
    filepath = os.path.join(plan_dir, filename)
    
    with open(filepath, "w") as f:
        f.write(markdown)
    
    return {
        "filename": filename,
        "markdown": markdown,
    }
