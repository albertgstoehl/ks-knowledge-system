from datetime import datetime
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models import Plan, Session

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionStart(BaseModel):
    template_key: str
    plan_id: int | None = None


class SessionEnd(BaseModel):
    session_id: int
    notes: str | None = None


@router.get("")
async def list_sessions(
    since: Optional[date] = None,
    plan_id: Optional[int] = None,
    session: AsyncSession = Depends(get_db),
):
    query = select(Session).order_by(Session.started_at.desc())

    if since:
        query = query.where(Session.started_at >= datetime.combine(since, datetime.min.time()))
    if plan_id:
        query = query.where(Session.plan_id == plan_id)

    result = await session.execute(query)
    sessions = result.scalars().all()

    return [
        {
            "id": entry.id,
            "started_at": str(entry.started_at),
            "ended_at": str(entry.ended_at) if entry.ended_at else None,
            "template_key": entry.template_key,
            "notes": entry.notes,
            "plan_id": entry.plan_id,
        }
        for entry in sessions
    ]


@router.post("/start")
async def start_session(payload: SessionStart, session: AsyncSession = Depends(get_db)):
    if payload.plan_id:
        result = await session.execute(select(Plan).where(Plan.id == payload.plan_id))
        if not result.scalars().first():
            raise HTTPException(status_code=404, detail="Plan not found")

    new_session = Session(template_key=payload.template_key, plan_id=payload.plan_id)
    session.add(new_session)
    await session.commit()
    await session.refresh(new_session)
    return {
        "id": new_session.id,
        "template_key": new_session.template_key,
        "started_at": str(new_session.started_at),
        "plan_id": new_session.plan_id,
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
