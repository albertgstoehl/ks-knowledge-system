from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.schemas import SearchRequest, BookmarkResponse
from src.services.search_service import SearchService
from typing import List

router = APIRouter(prefix="/search", tags=["search"])
search_service = SearchService()

@router.post("/keyword", response_model=List[BookmarkResponse])
async def keyword_search(
    search_data: SearchRequest,
    session: AsyncSession = Depends(get_db)
):
    """Keyword search on title, description, and URL"""
    results = await search_service.keyword_search(
        query=search_data.query,
        session=session,
        state_filter=search_data.state,
        limit=search_data.limit
    )

    return [BookmarkResponse.model_validate(b) for b in results]
