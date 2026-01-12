import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.routers import ui, plans, sessions, sets

BASE_PATH = os.getenv("BASE_PATH", "").rstrip("/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.database import init_db
    await init_db()
    yield


app = FastAPI(title="Train", version="0.1.0", lifespan=lifespan)

# Mount static files only if directories exist (for testing)
if os.path.isdir("shared/css"):
    app.mount("/static/shared/css", StaticFiles(directory="shared/css"), name="shared-css")
if os.path.isdir("shared/js"):
    app.mount("/static/shared/js", StaticFiles(directory="shared/js"), name="shared-js")
if os.path.isdir("src/static"):
    app.mount("/static", StaticFiles(directory="src/static"), name="static")


@app.get("/health")
async def health():
    return {"status": "healthy"}


app.include_router(ui.router)
app.include_router(plans.router)
app.include_router(sessions.router)
app.include_router(sets.router)
