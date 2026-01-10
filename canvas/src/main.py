from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from src.routers import canvas, ui, workspace, events
import os

# Support path-based routing (e.g., /dev prefix for dev environment)
BASE_PATH = os.getenv("BASE_PATH", "").rstrip("/")

app = FastAPI(title="Canvas", version="0.1.0", root_path=BASE_PATH)

# Allow CORS for Kasten integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount shared CSS and JS
app.mount("/static/shared/css", StaticFiles(directory="shared/css"), name="shared-css")
app.mount("/static/shared/js", StaticFiles(directory="shared/js"), name="shared-js")
# Mount service-specific static
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup():
    from src.database import init_db
    await init_db()

@app.get("/health")
async def health():
    return {"status": "healthy"}

app.include_router(canvas.router)
app.include_router(workspace.router)
app.include_router(ui.router)
app.include_router(events.router)
