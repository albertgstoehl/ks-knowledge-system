# kasten/src/routers/api.py
import os
import random
import re
from datetime import datetime
from glob import glob
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.database import get_db
from src.models import Note, Link, Source
from src.scanner import scan_notes_directory

router = APIRouter(prefix="/api", tags=["api"])

class NoteCreateRequest(BaseModel):
    title: str
    content: str
    parent: str | None = None
    source_id: int | None = None


class SourceCreateRequest(BaseModel):
    url: str
    title: str | None = None
    description: str | None = None
    content: str | None = None
    video_id: str | None = None


class SourceResponse(BaseModel):
    id: int
    url: str
    title: str | None
    description: str | None
    content: str | None
    video_id: str | None
    archived_at: datetime

    class Config:
        from_attributes = True


class SourceDetailResponse(BaseModel):
    id: int
    url: str
    title: str | None
    description: str | None
    content: str | None
    video_id: str | None
    archived_at: datetime
    note_ids: list[str]

    class Config:
        from_attributes = True

def get_notes_path():
    return os.getenv("NOTES_PATH", "/app/notes")

def generate_note_id(notes_path: str) -> str:
    """Generate next available YYMMDD+letter ID."""
    today = datetime.now().strftime("%y%m%d")
    existing = glob(os.path.join(notes_path, f"{today}*.md"))

    if not existing:
        return f"{today}a"

    # Find highest letter used today
    letters = []
    for path in existing:
        filename = os.path.basename(path)
        # Extract letter(s) after date
        match = re.match(rf'^{today}([a-z]+)\.md$', filename)
        if match:
            letters.append(match.group(1))

    if not letters:
        return f"{today}a"

    # Get next letter
    highest = max(letters)
    next_letter = chr(ord(highest[-1]) + 1)
    return f"{today}{next_letter}"

@router.post("/reindex")
async def reindex(session: AsyncSession = Depends(get_db)):
    """Rescan notes directory and rebuild index."""
    notes_path = get_notes_path()

    # Clear existing data
    await session.execute(Link.__table__.delete())
    await session.execute(Note.__table__.delete())

    # Scan and insert
    notes, links = scan_notes_directory(notes_path)

    for note_data in notes:
        note = Note(**note_data)
        session.add(note)

    await session.commit()

    # Add links (only for notes that exist)
    note_ids = {n["id"] for n in notes}
    for from_id, to_id in links:
        if from_id in note_ids and to_id in note_ids:
            link = Link(from_note_id=from_id, to_note_id=to_id)
            session.add(link)

    await session.commit()
    return {"status": "ok", "notes": len(notes), "links": len(links)}

@router.get("/notes")
async def list_notes(session: AsyncSession = Depends(get_db)):
    """List all notes."""
    result = await session.execute(select(Note).order_by(Note.id.desc()))
    notes = result.scalars().all()
    return [{"id": n.id, "title": n.title} for n in notes]

@router.get("/notes/entry-points")
async def get_entry_points(session: AsyncSession = Depends(get_db)):
    """Get notes with only outgoing links (no backlinks)."""
    # Notes that have outgoing links but no incoming links
    has_outgoing = select(Link.from_note_id).distinct()
    has_incoming = select(Link.to_note_id).distinct()

    result = await session.execute(
        select(Note).where(
            Note.id.in_(has_outgoing),
            Note.id.notin_(has_incoming)
        )
    )
    notes = result.scalars().all()
    return [{"id": n.id, "title": n.title} for n in notes]

@router.get("/notes/random")
async def get_random_note(session: AsyncSession = Depends(get_db)):
    """Get a random note."""
    result = await session.execute(select(Note))
    notes = result.scalars().all()
    if not notes:
        raise HTTPException(status_code=404, detail="No notes found")
    note = random.choice(notes)
    return {"id": note.id, "title": note.title}

@router.get("/notes/{note_id}")
async def get_note(note_id: str, session: AsyncSession = Depends(get_db)):
    """Get a specific note with content and source."""
    result = await session.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Read content from file
    notes_path = get_notes_path()
    filepath = os.path.join(notes_path, note.file_path)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    # Get source if linked
    source_data = None
    if note.source_id:
        source_result = await session.execute(
            select(Source).where(Source.id == note.source_id)
        )
        source = source_result.scalar_one_or_none()
        if source:
            source_data = {
                "id": source.id,
                "url": source.url,
                "title": source.title,
                "description": source.description,
                "content": source.content,
                "video_id": source.video_id,
                "archived_at": source.archived_at.isoformat() if source.archived_at else None
            }

    return {
        "id": note.id,
        "title": note.title,
        "content": content,
        "source": source_data
    }

@router.get("/notes/{note_id}/links")
async def get_note_links(note_id: str, session: AsyncSession = Depends(get_db)):
    """Get forward and back links for a note."""
    # Forward links (this note links to)
    forward_result = await session.execute(
        select(Note).join(Link, Note.id == Link.to_note_id).where(Link.from_note_id == note_id)
    )
    forward = forward_result.scalars().all()

    # Back links (notes that link to this)
    back_result = await session.execute(
        select(Note).join(Link, Note.id == Link.from_note_id).where(Link.to_note_id == note_id)
    )
    back = back_result.scalars().all()

    return {
        "forward": [{"id": n.id, "title": n.title} for n in forward],
        "back": [{"id": n.id, "title": n.title} for n in back]
    }

@router.post("/notes", status_code=201)
async def create_note(data: NoteCreateRequest, session: AsyncSession = Depends(get_db)):
    """Create a new note file."""
    notes_path = get_notes_path()
    note_id = generate_note_id(notes_path)
    filename = f"{note_id}.md"
    filepath = os.path.join(notes_path, filename)

    # Verify source exists if provided
    if data.source_id:
        source_result = await session.execute(
            select(Source).where(Source.id == data.source_id)
        )
        if not source_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Source not found")

    # Build file content
    lines = []
    if data.parent:
        lines.append("---")
        lines.append(f"parent: {data.parent}")
        lines.append("---")
    lines.append(data.title)
    lines.append("")
    lines.append(data.content)

    file_content = "\n".join(lines)

    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(file_content)

    # Add to database with source_id
    note = Note(
        id=note_id,
        title=data.title,
        file_path=filename,
        parent_id=data.parent,
        source_id=data.source_id
    )
    session.add(note)
    await session.commit()

    return {"id": note_id, "title": data.title}


@router.post("/sources", status_code=201, response_model=SourceResponse)
async def create_source(data: SourceCreateRequest, session: AsyncSession = Depends(get_db)):
    """Create a new source (archived bookmark)."""
    # Check for duplicate URL
    result = await session.execute(
        select(Source).where(Source.url == data.url)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Return existing source instead of error
        return existing

    source = Source(
        url=data.url,
        title=data.title,
        description=data.description,
        content=data.content,
        video_id=data.video_id
    )
    session.add(source)
    await session.commit()
    await session.refresh(source)

    return source


@router.get("/sources/{source_id}", response_model=SourceDetailResponse)
async def get_source(source_id: int, session: AsyncSession = Depends(get_db)):
    """Get a source with linked note IDs."""
    result = await session.execute(
        select(Source).where(Source.id == source_id)
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Get linked notes
    notes_result = await session.execute(
        select(Note.id).where(Note.source_id == source_id)
    )
    note_ids = [n[0] for n in notes_result.all()]

    return SourceDetailResponse(
        id=source.id,
        url=source.url,
        title=source.title,
        description=source.description,
        content=source.content,
        video_id=source.video_id,
        archived_at=source.archived_at,
        note_ids=note_ids
    )
