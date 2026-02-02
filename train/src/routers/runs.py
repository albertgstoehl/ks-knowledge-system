from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Run

router = APIRouter(prefix="/api/runs", tags=["runs"])


class RunCreate(BaseModel):
    date: str
    distance_km: float
    duration_minutes: int
    avg_hr: Optional[int] = None
    elevation_gain_m: Optional[int] = None
    effort: Optional[int] = None  # 1-10
    soreness_next_day: Optional[int] = None  # 0-10
    notes: Optional[str] = None


class RunResponse(BaseModel):
    id: int
    date: str
    distance_km: float
    duration_minutes: int
    pace_per_km: str
    effort: Optional[int]
    notes: Optional[str]


def format_pace(distance_km: float, duration_minutes: int) -> str:
    """Format pace as MM:SS per km."""
    if distance_km <= 0:
        return "0:00"
    pace_minutes = duration_minutes / distance_km
    mins = int(pace_minutes)
    secs = int((pace_minutes - mins) * 60)
    return f"{mins}:{secs:02d}"


@router.post("", response_model=RunResponse)
async def create_run(
    payload: RunCreate,
    session: AsyncSession = Depends(get_db)
):
    """Log a manual run (for when you forgot your watch)."""
    run = Run(
        date=date.fromisoformat(payload.date),
        distance_km=payload.distance_km,
        duration_minutes=payload.duration_minutes,
        avg_hr=payload.avg_hr,
        elevation_gain_m=payload.elevation_gain_m,
        effort=payload.effort,
        soreness_next_day=payload.soreness_next_day,
        notes=payload.notes,
        source="manual",
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    
    return RunResponse(
        id=run.id,
        date=run.date.isoformat(),
        distance_km=run.distance_km,
        duration_minutes=run.duration_minutes,
        pace_per_km=format_pace(run.distance_km, run.duration_minutes),
        effort=run.effort,
        notes=run.notes,
    )


@router.get("", response_model=List[RunResponse])
async def list_runs(
    since: Optional[str] = None,
    limit: int = 30,
    session: AsyncSession = Depends(get_db)
):
    """List runs, newest first."""
    query = select(Run).order_by(desc(Run.date))
    
    if since:
        query = query.where(Run.date >= date.fromisoformat(since))
    
    query = query.limit(limit)
    
    result = await session.execute(query)
    runs = result.scalars().all()
    
    return [
        RunResponse(
            id=run.id,
            date=run.date.isoformat(),
            distance_km=run.distance_km,
            duration_minutes=run.duration_minutes,
            pace_per_km=format_pace(run.distance_km, run.duration_minutes),
            effort=run.effort,
            notes=run.notes,
        )
        for run in runs
    ]


@router.get("/today")
async def get_today_run(
    session: AsyncSession = Depends(get_db)
):
    """Get today's run if logged."""
    result = await session.execute(
        select(Run).where(Run.date == date.today())
    )
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="No run logged today")
    
    return RunResponse(
        id=run.id,
        date=run.date.isoformat(),
        distance_km=run.distance_km,
        duration_minutes=run.duration_minutes,
        pace_per_km=format_pace(run.distance_km, run.duration_minutes),
        effort=run.effort,
        notes=run.notes,
    )


@router.put("/{run_id}/notes")
async def update_run_notes(
    run_id: int,
    effort: Optional[int] = None,
    soreness: Optional[int] = None,
    notes: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
):
    """Add subjective notes to an imported run."""
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if effort is not None:
        run.effort = effort
    if soreness is not None:
        run.soreness_next_day = soreness
    if notes is not None:
        run.notes = notes
    
    await session.commit()
    return {"status": "updated"}
