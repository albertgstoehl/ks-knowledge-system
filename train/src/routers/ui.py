import os
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from src import database
from src.models import Session
from src.utils.paths import find_shared_dir

router = APIRouter(tags=["ui"])

BASE_PATH = os.getenv("BASE_PATH", "").rstrip("/")

templates_dir = Path(__file__).parent.parent / "templates"
shared_templates_dir = find_shared_dir(Path(__file__)) / "templates"
templates = Jinja2Templates(directory=[str(templates_dir), str(shared_templates_dir)])


def _render(request: Request, template: str, context: dict | None = None):
    """Render template with base_path included."""
    ctx = {"request": request, "base_path": BASE_PATH}
    if context:
        ctx.update(context)
    return templates.TemplateResponse(template, ctx)


@router.get("/", response_class=HTMLResponse)
@router.get("/today", response_class=HTMLResponse)
async def today(request: Request):
    from datetime import date, timedelta
    from src.models import RecoverySummary, Run
    from sqlalchemy import func
    
    # Check for active session (no ended_at)
    active_session = None
    today_data = None
    
    if database.async_session_maker:
        async with database.async_session_maker() as db:
            result = await db.execute(
                select(Session)
                .where(Session.ended_at.is_(None))
                .order_by(desc(Session.started_at))
                .limit(1)
            )
            active_session = result.scalars().first()
            
            # Get marathon training data
            today = date.today()
            week_ago = today - timedelta(days=7)
            yesterday = today - timedelta(days=1)
            
            # Get recovery data
            recovery_result = await db.execute(
                select(RecoverySummary).where(RecoverySummary.date == today)
            )
            recovery = recovery_result.scalar_one_or_none()
            
            # Get weekly mileage
            mileage_result = await db.execute(
                select(func.sum(Run.distance_km)).where(Run.date >= week_ago)
            )
            weekly_mileage = mileage_result.scalar() or 0
            
            # Get runs this week
            runs_result = await db.execute(
                select(Run).where(Run.date >= week_ago)
            )
            runs_this_week = runs_result.scalars().all()
            
            # Get yesterday's run
            yesterday_result = await db.execute(
                select(Run).where(Run.date == yesterday)
            )
            yesterday_run = yesterday_result.scalar_one_or_none()
            
            # Race date
            race_date = date(2026, 4, 15)
            weeks_to_race = (race_date - today).days // 7
            
            # Calculate readiness breakdown if we have recovery data
            readiness_data = None
            if recovery:
                from src.routers.recovery import calculate_readiness
                readiness_data = calculate_readiness({
                    "sleep_score": recovery.sleep_score,
                    "hrv_avg": recovery.hrv_avg,
                    "resting_hr": recovery.resting_hr
                })
            
            today_data = {
                "marathon": {
                    "weeks_to_race": weeks_to_race,
                    "readiness_score": recovery.readiness_score if recovery else None,
                    "weekly_mileage": round(weekly_mileage, 1),
                    "runs_this_week": len(runs_this_week),
                    "target_runs_per_week": 3,
                },
                "readiness": readiness_data,
                "yesterday_run": {
                    "distance_km": yesterday_run.distance_km if yesterday_run else None,
                    "pace": f"{int(yesterday_run.duration_minutes / yesterday_run.distance_km)}:{int((yesterday_run.duration_minutes / yesterday_run.distance_km % 1) * 60):02d}/km" if yesterday_run else None,
                    "has_notes": yesterday_run.notes is not None if yesterday_run else False,
                } if yesterday_run else None,
                "today_date": today.isoformat(),
                "today_scheduled": {
                    "distance_km": 5,
                    "pace_range": "6:15-6:30",
                    "type": "easy",
                },
            }
    
    return _render(request, "today.html", {
        "active_tab": "Today",
        "active_session": active_session,
        "marathon_mode": True,
        "today_data": today_data,
    })


@router.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    return _render(request, "history.html", {"active_tab": "History"})


@router.get("/plan", response_class=HTMLResponse)
async def plan(request: Request):
    return _render(request, "plan.html", {"active_tab": "Plan"})
