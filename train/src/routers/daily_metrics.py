from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import DailyMetrics

router = APIRouter(prefix="/api/daily-metrics", tags=["daily-metrics"])


class DailyMetricsSync(BaseModel):
    date: str
    resting_hr: Optional[int] = None
    hrv_avg: Optional[int] = None
    sleep_score: Optional[int] = None
    sleep_duration_hours: Optional[float] = None
    vo2max: Optional[float] = None
    marathon_shape: Optional[float] = None
    tsb: Optional[float] = None
    atl: Optional[float] = None
    ctl: Optional[float] = None
    soreness: Optional[int] = None
    energy: Optional[int] = None


@router.post("/sync")
async def sync_daily_metrics(
    payload: DailyMetricsSync,
    session: AsyncSession = Depends(get_db)
):
    """Upsert daily metrics from Runalyze sync."""
    target_date = date.fromisoformat(payload.date)
    
    result = await session.execute(
        select(DailyMetrics).where(DailyMetrics.date == target_date)
    )
    existing = result.scalar_one_or_none()
    
    data = payload.model_dump(exclude={"date"})
    
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
    else:
        metrics = DailyMetrics(date=target_date, **data)
        session.add(metrics)
    
    await session.commit()
    
    return {"status": "synced", "date": payload.date}


@router.get("/today")
async def get_today_metrics(session: AsyncSession = Depends(get_db)):
    """Get today's metrics for display."""
    result = await session.execute(
        select(DailyMetrics).where(DailyMetrics.date == date.today())
    )
    metrics = result.scalar_one_or_none()
    
    if not metrics:
        raise HTTPException(status_code=404, detail="No data for today")
    
    # Calculate weeks to race (hardcoded for now)
    race_date = date(2026, 4, 15)
    weeks_to_race = (race_date - date.today()).days // 7
    
    return {
        "date": metrics.date.isoformat(),
        "marathon": {
            "weeks_to_race": weeks_to_race,
            "shape_pct": metrics.marathon_shape,
            "shape_status": _get_shape_status(metrics.marathon_shape),
        },
        "readiness": {
            "tsb": metrics.tsb,
            "tsb_status": _get_tsb_status(metrics.tsb),
            "vo2max": metrics.vo2max,
        },
        "health": {
            "resting_hr": metrics.resting_hr,
            "hrv_avg": metrics.hrv_avg,
            "sleep_score": metrics.sleep_score,
        },
    }


def _get_shape_status(shape: Optional[float]) -> str:
    if shape is None:
        return "unknown"
    if shape >= 90:
        return "race_ready"
    if shape >= 70:
        return "building"
    return "insufficient"


def _get_tsb_status(tsb: Optional[float]) -> str:
    if tsb is None:
        return "unknown"
    if tsb < -25:
        return "overreached"
    if tsb < -10:
        return "training_zone"
    if tsb < 10:
        return "recovered"
    return "detraining"
