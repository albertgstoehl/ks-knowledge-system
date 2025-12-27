from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import os

from .database import init_db
from .routers import sessions, logging, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


app = FastAPI(title="Balance", lifespan=lifespan)

# Register routers
app.include_router(sessions.router)
app.include_router(logging.router)
app.include_router(settings.router)

# Static files and templates
static_path = os.path.join(os.path.dirname(__file__), "static")
templates_path = os.path.join(os.path.dirname(__file__), "templates")

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main timer page."""
    return templates.TemplateResponse("index.html", {"request": request, "active_nav": "timer"})


@app.get("/log", response_class=HTMLResponse)
async def log_page(request: Request):
    """Activity logging page."""
    return templates.TemplateResponse("log.html", {"request": request, "active_nav": "log"})


@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    """Stats and life compass page."""
    return templates.TemplateResponse("stats.html", {"request": request, "active_nav": "stats"})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page."""
    return templates.TemplateResponse("settings.html", {"request": request, "active_nav": "settings"})


@app.get("/evening", response_class=HTMLResponse)
async def evening_page(request: Request):
    """Evening check-in page."""
    return templates.TemplateResponse("evening.html", {"request": request, "active_nav": ""})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
