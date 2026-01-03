from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from src.services.background_jobs import BackgroundJobService
from src.routers import bookmarks, search, backup, ui, feeds, canvas, events
from src.scheduler import start_scheduler, stop_scheduler
import os

app = FastAPI(
    title="Bookmark Manager API",
    description="Minimal bookmark management with semantic search",
    version="0.1.0"
)

# Mount shared CSS and JS
app.mount("/static/shared/css", StaticFiles(directory="shared/css"), name="shared-css")
app.mount("/static/shared/js", StaticFiles(directory="shared/js"), name="shared-js")

# Initialize services
jina_api_key = os.getenv("JINA_API_KEY")
oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
background_job_service = BackgroundJobService(
    jina_api_key=jina_api_key,
    oauth_token=oauth_token
)

@app.on_event("startup")
async def startup():
    from src.database import init_db
    await init_db()
    start_scheduler()


@app.on_event("shutdown")
async def shutdown():
    stop_scheduler()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return RedirectResponse(url="/ui/")

# Register routers
app.include_router(bookmarks.router)
app.include_router(search.router)
app.include_router(backup.router)
app.include_router(ui.router)
app.include_router(feeds.router)
app.include_router(canvas.router)
app.include_router(events.router)
