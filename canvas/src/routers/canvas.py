from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database import get_db
from src.models import CanvasState
from src.schemas import CanvasContent, CanvasResponse, QuoteRequest

router = APIRouter(prefix="/api", tags=["canvas"])

async def get_or_create_canvas(session: AsyncSession) -> CanvasState:
    result = await session.execute(select(CanvasState).where(CanvasState.id == 1))
    canvas = result.scalar_one_or_none()
    if not canvas:
        canvas = CanvasState(id=1, content="")
        session.add(canvas)
        await session.commit()
        await session.refresh(canvas)
    return canvas

@router.get("/canvas", response_model=CanvasResponse)
async def get_canvas(session: AsyncSession = Depends(get_db)):
    canvas = await get_or_create_canvas(session)
    return CanvasResponse(content=canvas.content, updated_at=canvas.updated_at)

@router.put("/canvas", response_model=CanvasResponse)
async def update_canvas(data: CanvasContent, session: AsyncSession = Depends(get_db)):
    canvas = await get_or_create_canvas(session)
    canvas.content = data.content
    await session.commit()
    await session.refresh(canvas)
    return CanvasResponse(content=canvas.content, updated_at=canvas.updated_at)

@router.delete("/canvas")
async def clear_canvas(session: AsyncSession = Depends(get_db)):
    """Clear the draft content. Called by scheduled job at midnight."""
    canvas = await get_or_create_canvas(session)
    canvas.content = ""
    await session.commit()
    return {"status": "cleared"}


@router.post("/quotes", status_code=201)
async def receive_quote(data: QuoteRequest, session: AsyncSession = Depends(get_db)):
    canvas = await get_or_create_canvas(session)

    quote_block = f'\n\n> "{data.quote}"\n> — {data.source_title} ({data.source_url})\n'
    canvas.content = canvas.content + quote_block

    await session.commit()
    return {"status": "ok"}
