from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import RecoverySummary

router = APIRouter(prefix="/api/recovery", tags=["recovery"])


class RecoverySync(BaseModel):
    date: str  # YYYY-MM-DD
    resting_hr: Optional[int] = None
    hrv_avg: Optional[int] = None
    sleep_score: Optional[int] = None
    sleep_duration_hours: Optional[float] = None
    deep_sleep_percent: Optional[float] = None
    avg_stress: Optional[int] = None


class RecoveryResponse(BaseModel):
    date: str
    resting_hr: Optional[int]
    hrv_avg: Optional[int]
    sleep_score: Optional[int]
    readiness_score: int
    weekly_mileage: float


def calculate_readiness_score(data: dict) -> int:
    """Calculate 0-100 readiness score from metrics."""
    score = 50  # baseline
    
    if data.get("sleep_score"):
        score += (data["sleep_score"] - 70) * 0.3
    
    # HRV: higher is better (simplified)
    if data.get("hrv_avg"):
        score += (data["hrv_avg"] - 45) * 0.5
    
    # RHR: lower is better (simplified)
    if data.get("resting_hr"):
        score -= (data["resting_hr"] - 50) * 0.3
    
    return max(0, min(100, int(score)))


@router.post("/sync")
async def sync_recovery(
    payload: RecoverySync,
    session: AsyncSession = Depends(get_db)
):
    """Sync daily recovery data from Garmin."""
    # Calculate weekly mileage (last 7 days of runs)
    from src.models import Session as TrainSession, SetEntry
    
    # TODO: Calculate from runs table once we have it
    weekly_mileage = 0.0
    
    readiness = calculate_readiness_score(payload.model_dump())
    
    # Check if exists
    result = await session.execute(
        select(RecoverySummary).where(RecoverySummary.date == payload.date)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Update
        existing.resting_hr = payload.resting_hr
        existing.hrv_avg = payload.hrv_avg
        existing.sleep_score = payload.sleep_score
        existing.sleep_duration_hours = payload.sleep_duration_hours
        existing.deep_sleep_percent = payload.deep_sleep_percent
        existing.avg_stress = payload.avg_stress
        existing.readiness_score = readiness
        existing.weekly_mileage = weekly_mileage
    else:
        # Create new
        summary = RecoverySummary(
            date=date.fromisoformat(payload.date),
            resting_hr=payload.resting_hr,
            hrv_avg=payload.hrv_avg,
            sleep_score=payload.sleep_score,
            sleep_duration_hours=payload.sleep_duration_hours,
            deep_sleep_percent=payload.deep_sleep_percent,
            avg_stress=payload.avg_stress,
            readiness_score=readiness,
            weekly_mileage=weekly_mileage,
        )
        session.add(summary)
    
    await session.commit()
    
    return {
        "date": payload.date,
        "readiness_score": readiness,
        "weekly_mileage": weekly_mileage,
    }


@router.get("/daily", response_model=RecoveryResponse)
async def get_daily_recovery(
    date_str: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
):
    """Get recovery data for a specific date (default: today)."""
    target_date = date.fromisoformat(date_str) if date_str else date.today()
    
    result = await session.execute(
        select(RecoverySummary).where(RecoverySummary.date == target_date)
    )
    summary = result.scalar_one_or_none()
    
    if not summary:
        raise HTTPException(status_code=404, detail="No data for this date")
    
    return RecoveryResponse(
        date=summary.date.isoformat(),
        resting_hr=summary.resting_hr,
        hrv_avg=summary.hrv_avg,
        sleep_score=summary.sleep_score,
        readiness_score=summary.readiness_score,
        weekly_mileage=summary.weekly_mileage,
    )


@router.get("/weekly")
async def get_weekly_recovery(
    session: AsyncSession = Depends(get_db)
):
    """Get 7-day aggregate recovery stats."""
    week_ago = date.today() - timedelta(days=7)
    
    result = await session.execute(
        select(
            func.avg(RecoverySummary.readiness_score).label("avg_readiness"),
            func.avg(RecoverySummary.sleep_score).label("avg_sleep"),
            func.avg(RecoverySummary.hrv_avg).label("avg_hrv"),
            func.avg(RecoverySummary.resting_hr).label("avg_rhr"),
        )
        .where(RecoverySummary.date >= week_ago)
    )
    row = result.one()
    
    return {
        "period": "last_7_days",
        "avg_readiness": round(row.avg_readiness or 0),
        "avg_sleep": round(row.avg_sleep or 0),
        "avg_hrv": round(row.avg_hrv or 0),
        "avg_resting_hr": round(row.avg_rhr or 0),
    }
