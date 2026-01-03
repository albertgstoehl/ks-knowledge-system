import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models import Bookmark
from src.schemas import CanvasQuoteCreate, CanvasQuoteResponse

router = APIRouter(prefix="/canvas", tags=["canvas"])

CANVAS_API_URL = os.getenv("CANVAS_API_URL", "http://canvas:8000/api/quotes")


@router.post("/quotes", response_model=CanvasQuoteResponse)
async def push_quote_to_canvas(
    data: CanvasQuoteCreate,
    session: AsyncSession = Depends(get_db)
):
    """Push a quote to Canvas draft mode"""

    # Get bookmark for source metadata
    bookmark = await session.get(Bookmark, data.bookmark_id)
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    # Push to Canvas
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                CANVAS_API_URL,
                json={
                    "text": data.quote,
                    "source_url": bookmark.url,
                    "source_title": bookmark.title or "Untitled"
                },
                timeout=10.0
            )
            response.raise_for_status()
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Canvas service unavailable: {str(e)}"
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Canvas error: {e.response.text}"
            )

    return CanvasQuoteResponse(success=True, message="Quote sent to Canvas")
