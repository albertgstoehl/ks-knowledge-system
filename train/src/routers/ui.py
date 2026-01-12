import os
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from src.utils.paths import find_shared_dir

BASE_PATH = os.getenv("BASE_PATH", "").rstrip("/")

router = APIRouter(tags=["ui"])

templates_dir = Path(__file__).parent.parent / "templates"
shared_templates_dir = find_shared_dir(Path(__file__)) / "templates"
templates = Jinja2Templates(directory=[str(templates_dir), str(shared_templates_dir)])


@router.get("/")
async def root():
    return RedirectResponse(url=f"{BASE_PATH}/today")


@router.get("/today", response_class=HTMLResponse)
async def today(request: Request):
    context = {"request": request, "active_tab": "Today", "base_path": BASE_PATH}
    return templates.TemplateResponse("today.html", context)


@router.get("/log", response_class=HTMLResponse)
async def log(request: Request):
    context = {"request": request, "active_tab": "Log Workout", "base_path": BASE_PATH}
    return templates.TemplateResponse("log.html", context)


@router.get("/plan", response_class=HTMLResponse)
async def plan(request: Request):
    context = {"request": request, "active_tab": "Plan", "base_path": BASE_PATH}
    return templates.TemplateResponse("plan.html", context)
