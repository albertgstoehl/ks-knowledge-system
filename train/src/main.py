import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.routers import ui, plans, sessions, sets, context, exercises, recovery, runs, today, marathon, daily_metrics

BASE_PATH = os.getenv("BASE_PATH", "").rstrip("/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.database import init_db
    await init_db()
    yield


# Note: Don't use root_path - Traefik strips /dev prefix before reaching the app
app = FastAPI(title="Train", version="0.1.0", lifespan=lifespan)

# Static files - use absolute paths for StaticFiles (required for proper resolution)
_base = os.path.dirname(os.path.abspath(__file__))
static_path = os.path.join(_base, "static")

# Shared paths: try Docker mount first (/app/shared), then local (../../shared)
_docker_shared = os.path.abspath(os.path.join(_base, "..", "shared"))
_local_shared = os.path.abspath(os.path.join(_base, "..", "..", "shared"))
_shared_base = _docker_shared if os.path.exists(_docker_shared) else _local_shared

# Mount shared (css + js) first, then service-specific static
if os.path.exists(_shared_base):
    app.mount("/static/shared", StaticFiles(directory=_shared_base), name="shared")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/health")
async def health():
    return {"status": "healthy"}


app.include_router(ui.router)
app.include_router(plans.router)
app.include_router(sessions.router)
app.include_router(sets.router)
app.include_router(context.router)
app.include_router(exercises.router)
app.include_router(recovery.router)
app.include_router(runs.router)
app.include_router(today.router)
app.include_router(marathon.router)
app.include_router(daily_metrics.router)
