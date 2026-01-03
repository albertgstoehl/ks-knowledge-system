import os
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.routers.canvas import get_or_create_canvas

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory=["src/templates", "shared/templates"])

@router.get("/")
async def root():
    return RedirectResponse(url="/draft")

@router.get("/draft")
async def draft_page(request: Request, session: AsyncSession = Depends(get_db)):
    canvas = await get_or_create_canvas(session)
    context = {
        "request": request,
        "active_tab": "draft",
        "content": canvas.content,
        "kasten_url": os.getenv("KASTEN_URL", "http://localhost:8003")
    }
    # Return partial for htmx requests
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("_content_draft.html", context)
    return templates.TemplateResponse("draft.html", context)

@router.get("/workspace")
async def workspace_page(request: Request, session: AsyncSession = Depends(get_db)):
    context = {
        "request": request,
        "active_tab": "workspace",
        "kasten_url": os.getenv("KASTEN_URL", "http://localhost:8003")
    }
    # Return partial for htmx requests
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("_content_workspace.html", context)
    return templates.TemplateResponse("workspace.html", context)
