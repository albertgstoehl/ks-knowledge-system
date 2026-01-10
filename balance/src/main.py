from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import os

from .database import init_db
from .routers import sessions, logging, settings, priorities, nextup, events
from .scheduler import start_scheduler, stop_scheduler, check_expired_sessions, ensure_youtube_blocked

# Support path-based routing (e.g., /dev prefix for dev environment)
BASE_PATH = os.getenv("BASE_PATH", "").rstrip("/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and scheduler on startup."""
    await init_db()
    # Check for any expired sessions on startup (catches sessions from pod restarts)
    await check_expired_sessions()
    # Ensure YouTube is blocked by default (unless active YouTube session)
    await ensure_youtube_blocked()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Balance", lifespan=lifespan)

# Register routers
app.include_router(sessions.router)
app.include_router(logging.router)
app.include_router(settings.router)
app.include_router(priorities.router)
app.include_router(nextup.router)
app.include_router(events.router)

# Static files and templates
static_path = os.path.join(os.path.dirname(__file__), "static")
templates_path = os.path.join(os.path.dirname(__file__), "templates")

# Shared paths: try Docker mount first (/app/shared), then local (../../shared)
_base = os.path.dirname(__file__)
_docker_shared = os.path.join(_base, "..", "shared")
_local_shared = os.path.join(_base, "..", "..", "shared")
_shared_base = _docker_shared if os.path.exists(_docker_shared) else _local_shared
shared_css_path = os.path.join(_shared_base, "css")
shared_templates_path = os.path.join(_shared_base, "templates")

# Mount shared (css + js) first, then service-specific static
app.mount("/static/shared", StaticFiles(directory=_shared_base), name="shared")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Include shared templates in search path
templates = Jinja2Templates(directory=[templates_path, shared_templates_path])


def _template_for(request: Request, full: str, partial: str, context: dict):
    """Return partial for htmx requests, full page otherwise."""
    # Always include BASE_PATH in template context
    template_context = {"request": request, "base_path": BASE_PATH, **context}
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(partial, template_context)
    return templates.TemplateResponse(full, template_context)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main timer page."""
    return _template_for(request, "index.html", "_content_index.html", {"active_nav": "timer"})


@app.get("/log", response_class=HTMLResponse)
async def log_page(request: Request):
    """Activity logging page."""
    return _template_for(request, "log.html", "_content_log.html", {"active_nav": "log"})


@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    """Stats and life compass page."""
    return _template_for(request, "stats.html", "_content_stats.html", {"active_nav": "stats"})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page."""
    return _template_for(request, "settings.html", "_content_settings.html", {"active_nav": "settings"})


@app.get("/evening", response_class=HTMLResponse)
async def evening_page(request: Request):
    """Evening check-in page."""
    return _template_for(request, "evening.html", "_content_evening.html", {"active_nav": ""})


# Dev-only mockup route (set DEV_MODE=true to enable)
if os.getenv("DEV_MODE", "").lower() == "true":
    @app.get("/mockup", response_class=HTMLResponse)
    async def mockup_page(request: Request):
        """UI mockup for design iteration (dev only)."""
        return templates.TemplateResponse("mockup.html", {"request": request})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
