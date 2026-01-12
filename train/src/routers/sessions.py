from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models import Session

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionStart(BaseModel):
    template_key: str


class SessionEnd(BaseModel):
    session_id: int
    notes: str | None = None


@router.post("/start")
async def start_session(payload: SessionStart, session: AsyncSession = Depends(get_db)):
    new_session = Session(template_key=payload.template_key)
    session.add(new_session)
    await session.commit()
    await session.refresh(new_session)
    return {
        "id": new_session.id,
        "template_key": new_session.template_key,
        "started_at": str(new_session.started_at),
    }


@router.post("/end")
async def end_session(payload: SessionEnd, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Session).where(Session.id == payload.session_id))
    active = result.scalars().first()
    if not active:
        raise HTTPException(status_code=404, detail="Session not found")
    active.ended_at = datetime.utcnow()
    active.notes = payload.notes
    await session.commit()
    await session.refresh(active)
    return {
        "id": active.id,
        "ended_at": str(active.ended_at),
        "notes": active.notes,
    }
