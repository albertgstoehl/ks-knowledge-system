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
    # Check for active session (no ended_at)
    active_session = None
    if database.async_session_maker:
        async with database.async_session_maker() as db:
            result = await db.execute(
                select(Session)
                .where(Session.ended_at.is_(None))
                .order_by(desc(Session.started_at))
                .limit(1)
            )
            active_session = result.scalars().first()
    return _render(request, "today.html", {"active_tab": "Today", "active_session": active_session})


@router.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    return _render(request, "history.html", {"active_tab": "History"})


@router.get("/plan", response_class=HTMLResponse)
async def plan(request: Request):
    return _render(request, "plan.html", {"active_tab": "Plan"})
