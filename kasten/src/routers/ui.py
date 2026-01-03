# kasten/src/routers/ui.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database import get_db
from src.models import Note, Link, Source
import os
import re
import random

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory=["src/templates", "shared/templates"])

def render_links(content: str) -> str:
    """Convert [[id]] to clickable links."""
    def replace_link(match):
        note_id = match.group(1)
        return f'<a href="/note/{note_id}">{note_id}</a>'
    return re.sub(r'\[\[([^\]]+)\]\]', replace_link, content)

@router.get("/")
async def landing(request: Request, session: AsyncSession = Depends(get_db)):
    # Get entry points - notes with no parent (root notes)
    result = await session.execute(
        select(Note).where(Note.parent_id == None).order_by(Note.id.desc())
    )
    entry_points = [{"id": n.id, "title": n.title} for n in result.scalars().all()]

    return templates.TemplateResponse("landing.html", {
        "request": request,
        "entry_points": entry_points
    })

@router.get("/random")
async def random_redirect(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Note))
    notes = result.scalars().all()
    if not notes:
        return RedirectResponse(url="/")
    note = random.choice(notes)
    return RedirectResponse(url=f"/note/{note.id}")

@router.get("/note/{note_id}")
async def note_view(request: Request, note_id: str, session: AsyncSession = Depends(get_db)):
    from urllib.parse import urlparse

    # Get note
    result = await session.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        return RedirectResponse(url="/")

    # Read content
    notes_path = os.getenv("NOTES_PATH", "/app/notes")
    filepath = os.path.join(notes_path, note.file_path)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        content = "(Note file not found)"

    # Render links
    content_html = render_links(content)

    # Get source if linked
    source = None
    if note.source_id:
        source_result = await session.execute(
            select(Source).where(Source.id == note.source_id)
        )
        source_obj = source_result.scalar_one_or_none()
        if source_obj:
            # Extract domain from URL
            domain = urlparse(source_obj.url).netloc.replace("www.", "")
            source = {
                "id": source_obj.id,
                "url": source_obj.url,
                "title": source_obj.title,
                "description": source_obj.description,
                "domain": domain,
                "archived_at": source_obj.archived_at
            }

    # Get parent (from parent_id field)
    parent = None
    if note.parent_id:
        parent_result = await session.execute(
            select(Note).where(Note.id == note.parent_id)
        )
        parent_note = parent_result.scalar_one_or_none()
        if parent_note:
            parent = {"id": parent_note.id, "title": parent_note.title}

    # Get children (notes that have this note as parent, sorted by created_at)
    children_result = await session.execute(
        select(Note).where(Note.parent_id == note_id).order_by(Note.created_at.asc())
    )
    children = [{"id": n.id, "title": n.title} for n in children_result.scalars().all()]

    # Get siblings (other notes with same parent - to show branch context)
    siblings = []
    if note.parent_id:
        siblings_result = await session.execute(
            select(Note).where(
                Note.parent_id == note.parent_id,
                Note.id != note_id
            ).order_by(Note.created_at.asc())
        )
        siblings = [{"id": n.id, "title": n.title} for n in siblings_result.scalars().all()]

    canvas_url = os.getenv("CANVAS_URL", "https://canvas.gstoehl.dev")
    return templates.TemplateResponse("note.html", {
        "request": request,
        "note": {"id": note.id, "title": note.title},
        "content": content_html,
        "source": source,
        "parent": parent,
        "children": children,
        "siblings": siblings,
        "canvas_url": canvas_url
    })
