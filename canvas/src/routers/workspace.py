from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from src.database import get_db
from src.models import WorkspaceNote, WorkspaceConnection
from src.schemas import (
    WorkspaceNoteCreate, WorkspaceNoteResponse,
    ConnectionCreate, ConnectionUpdate, ConnectionResponse,
    WorkspaceResponse
)

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

def calculate_position(existing_count: int) -> tuple[float, float]:
    """Simple grid layout for auto-positioning"""
    cols = 3
    row = existing_count // cols
    col = existing_count % cols
    return (col * 350.0, row * 250.0)

@router.get("", response_model=WorkspaceResponse)
async def get_workspace(session: AsyncSession = Depends(get_db)):
    notes_result = await session.execute(select(WorkspaceNote))
    notes = notes_result.scalars().all()

    conns_result = await session.execute(select(WorkspaceConnection))
    connections = conns_result.scalars().all()

    return WorkspaceResponse(
        notes=[WorkspaceNoteResponse(
            id=n.id, km_note_id=n.km_note_id, x=n.x, y=n.y
        ) for n in notes],
        connections=[ConnectionResponse(
            id=c.id, from_note_id=c.from_note_id, to_note_id=c.to_note_id, label=c.label
        ) for c in connections]
    )

@router.post("/notes", status_code=201, response_model=WorkspaceNoteResponse)
async def add_note(data: WorkspaceNoteCreate, session: AsyncSession = Depends(get_db)):
    # Check if note already in workspace
    existing_check = await session.execute(
        select(WorkspaceNote).where(WorkspaceNote.km_note_id == data.km_note_id)
    )
    if existing_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Note already in workspace")

    # Count existing notes for positioning
    result = await session.execute(select(WorkspaceNote))
    existing = len(result.scalars().all())
    x, y = calculate_position(existing)

    note = WorkspaceNote(
        km_note_id=data.km_note_id,
        x=x,
        y=y
    )
    session.add(note)
    await session.commit()
    await session.refresh(note)

    return WorkspaceNoteResponse(
        id=note.id, km_note_id=note.km_note_id, x=note.x, y=note.y
    )

@router.delete("/notes/{note_id}")
async def delete_note(note_id: int, session: AsyncSession = Depends(get_db)):
    # Delete connections involving this note
    await session.execute(
        delete(WorkspaceConnection).where(
            (WorkspaceConnection.from_note_id == note_id) |
            (WorkspaceConnection.to_note_id == note_id)
        )
    )

    result = await session.execute(select(WorkspaceNote).where(WorkspaceNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    await session.delete(note)
    await session.commit()
    return {"status": "deleted"}

@router.post("/connections", status_code=201, response_model=ConnectionResponse)
async def add_connection(data: ConnectionCreate, session: AsyncSession = Depends(get_db)):
    conn = WorkspaceConnection(
        from_note_id=data.from_note_id,
        to_note_id=data.to_note_id,
        label=data.label
    )
    session.add(conn)
    await session.commit()
    await session.refresh(conn)

    return ConnectionResponse(
        id=conn.id, from_note_id=conn.from_note_id,
        to_note_id=conn.to_note_id, label=conn.label
    )

@router.put("/connections/{conn_id}", response_model=ConnectionResponse)
async def update_connection(conn_id: int, data: ConnectionUpdate, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(WorkspaceConnection).where(WorkspaceConnection.id == conn_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    conn.label = data.label
    await session.commit()
    await session.refresh(conn)

    return ConnectionResponse(
        id=conn.id, from_note_id=conn.from_note_id,
        to_note_id=conn.to_note_id, label=conn.label
    )

@router.delete("/connections/{conn_id}")
async def delete_connection(conn_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(WorkspaceConnection).where(WorkspaceConnection.id == conn_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    await session.delete(conn)
    await session.commit()
    return {"status": "deleted"}
