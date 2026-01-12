import os
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from src.utils.paths import find_shared_dir

BASE_PATH = os.getenv("BASE_PATH", "").rstrip("/")

router = APIRouter(tags=["ui"])

templates_dir = Path(__file__).parent.parent / "templates"
shared_templates_dir = find_shared_dir(Path(__file__)) / "templates"
templates = Jinja2Templates(directory=[str(templates_dir), str(shared_templates_dir)])


def _render(request: Request, template: str, context: dict):
    """Render template with base_path included."""
    return templates.TemplateResponse(
        template, {"request": request, "base_path": BASE_PATH, **context}
    )


@router.get("/", response_class=HTMLResponse)
@router.get("/today", response_class=HTMLResponse)
async def today(request: Request):
    return _render(request, "today.html", {"active_tab": "Today"})


@router.get("/log", response_class=HTMLResponse)
async def log(request: Request):
    return _render(request, "log.html", {"active_tab": "Log Workout"})


@router.get("/plan", response_class=HTMLResponse)
async def plan(request: Request):
    return _render(request, "plan.html", {"active_tab": "Plan"})
