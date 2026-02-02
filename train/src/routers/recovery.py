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


def calculate_readiness(data: dict) -> dict:
    """
    Calculate readiness verdict with transparent per-metric checks.
    
    Targets based on Garmin's established thresholds for trained athletes:
    - Sleep: 70+ (Garmin's 'fair' threshold)
    - HRV: 45+ ms (typical for active adults)
    - RHR: 50- bpm (trained runner baseline)
    """
    metrics = []
    checks_passed = 0
    total_checks = 0
    
    # Sleep Score: 0-100 Garmin score
    if data.get("sleep_score"):
        sleep = data["sleep_score"]
        if sleep >= 80:
            status = "GREEN"
            checks_passed += 1
        elif sleep >= 70:
            status = "GREEN"
            checks_passed += 1
        else:
            status = "YELLOW" if sleep >= 60 else "RED"
        total_checks += 1
        metrics.append({
            "name": "sleep",
            "value": sleep,
            "unit": "",
            "target": "70+",
            "status": status
        })
    
    # HRV: Higher is better recovery
    if data.get("hrv_avg"):
        hrv = data["hrv_avg"]
        if hrv >= 50:
            status = "GREEN"
            checks_passed += 1
        elif hrv >= 45:
            status = "GREEN"
            checks_passed += 1
        else:
            status = "YELLOW" if hrv >= 40 else "RED"
        total_checks += 1
        metrics.append({
            "name": "hrv",
            "value": hrv,
            "unit": "ms",
            "target": "45+",
            "status": status
        })
    
    # Resting HR: Lower is better
    if data.get("resting_hr"):
        rhr = data["resting_hr"]
        if rhr <= 50:
            status = "GREEN"
            checks_passed += 1
        elif rhr <= 55:
            status = "GREEN"
            checks_passed += 1
        else:
            status = "YELLOW" if rhr <= 60 else "RED"
        total_checks += 1
        metrics.append({
            "name": "resting_hr",
            "value": rhr,
            "unit": "bpm",
            "target": "50-",
            "status": status
        })
    
    # Overall verdict
    if total_checks == 0:
        verdict = "UNKNOWN"
        guidance = "No data available"
    elif checks_passed == total_checks:
        verdict = "GREEN"
        guidance = "Full training capacity"
    elif checks_passed >= total_checks * 0.5:
        verdict = "YELLOW"
        guidance = "Moderate training - keep it conversational"
    else:
        verdict = "RED"
        guidance = "Rest day recommended"
    
    return {
        "verdict": verdict,
        "guidance": guidance,
        "checks": f"{checks_passed}/{total_checks}",
        "metrics": metrics
    }


@router.post("/sync")
async def sync_recovery(
    payload: RecoverySync,
    session: AsyncSession = Depends(get_db)
):
    """Sync daily recovery data from Garmin."""
    from src.models import Run
    
    # Calculate weekly mileage (last 7 days of runs)
    week_ago = date.today() - timedelta(days=7)
    mileage_result = await session.execute(
        select(func.sum(Run.distance_km))
        .where(Run.date >= week_ago)
    )
    weekly_mileage = mileage_result.scalar() or 0.0
    
    # Calculate readiness with full breakdown
    readiness_data = calculate_readiness(payload.model_dump())
    
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
        existing.readiness_score = 100 if readiness_data["verdict"] == "GREEN" else (50 if readiness_data["verdict"] == "YELLOW" else 0)
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
            readiness_score=100 if readiness_data["verdict"] == "GREEN" else (50 if readiness_data["verdict"] == "YELLOW" else 0),
            weekly_mileage=weekly_mileage,
        )
        session.add(summary)
    
    await session.commit()
    
    return {
        "date": payload.date,
        "weekly_mileage": weekly_mileage,
        "readiness": readiness_data
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
