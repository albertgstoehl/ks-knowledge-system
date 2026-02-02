import os
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from src import database
from src.models import Session, DailyMetrics
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
    from src.models import Run
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
            
            # Get daily metrics from Runalyze
            metrics_result = await db.execute(
                select(DailyMetrics).where(DailyMetrics.date == today)
            )
            metrics = metrics_result.scalar_one_or_none()
            
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
            
            # Calculate status for metrics
            def _get_shape_status(shape):
                if shape is None:
                    return "no_data"
                if shape >= 90:
                    return "race_ready"
                if shape >= 70:
                    return "building"
                return "insufficient"

            def _get_tsb_status(tsb):
                if tsb is None:
                    return "no_data"
                if tsb < -25:
                    return "overreached"
                if tsb < -10:
                    return "training_zone"
                if tsb < 10:
                    return "recovered"
                return "detraining"
            
            today_data = {
                "marathon": {
                    "weeks_to_race": weeks_to_race,
                    "has_data": metrics is not None,
                    "shape_pct": metrics.marathon_shape if metrics else None,
                    "shape_status": _get_shape_status(metrics.marathon_shape if metrics else None),
                    "tsb": metrics.tsb if metrics else None,
                    "tsb_status": _get_tsb_status(metrics.tsb if metrics else None),
                    "vo2max": metrics.vo2max if metrics else None,
                    "weekly_mileage": round(weekly_mileage, 1),
                    "runs_this_week": len(runs_this_week),
                    "target_runs_per_week": 3,
                },
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


@router.get("/runs/log", response_class=HTMLResponse)
async def log_run(request: Request):
    """Manual run logging page (for when you forgot your watch)."""
    from datetime import date
    return _render(request, "log_run.html", {"active_tab": "Today", "today_date": date.today().isoformat()})
