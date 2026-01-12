from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from src.utils.paths import find_shared_dir

router = APIRouter(tags=["ui"])

templates_dir = Path(__file__).parent.parent / "templates"
shared_templates_dir = find_shared_dir(Path(__file__)) / "templates"
templates = Jinja2Templates(directory=[str(templates_dir), str(shared_templates_dir)])


@router.get("/", response_class=HTMLResponse)
@router.get("/today", response_class=HTMLResponse)
async def today(request: Request):
    return templates.TemplateResponse("today.html", {"request": request, "active_tab": "Today"})


@router.get("/log", response_class=HTMLResponse)
async def log(request: Request):
    return templates.TemplateResponse("log.html", {"request": request, "active_tab": "Log Workout"})


@router.get("/plan", response_class=HTMLResponse)
async def plan(request: Request):
    return templates.TemplateResponse("plan.html", {"request": request, "active_tab": "Plan"})
