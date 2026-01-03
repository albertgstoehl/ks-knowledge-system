import pytest
from unittest.mock import AsyncMock, patch
from src.services.background_jobs import BackgroundJobService
from src.models import Bookmark, BookmarkState
from src.database import get_db, engine, Base
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async for session in get_db():
        yield session

@pytest.mark.asyncio
async def test_process_bookmark_stores_content(db_session):
    """Content from Jina should be stored in bookmark.content"""
    # Create bookmark
    import uuid
    unique_url = f"https://example.com/content-test-{uuid.uuid4()}"
    bookmark = Bookmark(url=unique_url, state=BookmarkState.inbox)
    db_session.add(bookmark)
    await db_session.commit()
    await db_session.refresh(bookmark)

    # Mock Jina response with content
    mock_metadata = {
        "title": "Test Article",
        "description": "A test",
        "content": "# Test Article\n\nThis is the full markdown content."
    }

    service = BackgroundJobService()
    with patch.object(service.jina_client, 'extract_metadata', new_callable=AsyncMock) as mock_jina:
        mock_jina.return_value = mock_metadata
        with patch.object(service, '_get_embedding_service') as mock_embed:
            mock_embed.return_value.generate_embedding.return_value = [0.1] * 384
            with patch.object(service.archive_service, 'submit_to_archive', new_callable=AsyncMock) as mock_archive:
                mock_archive.return_value = {"snapshot_url": "https://archive.org/test"}

                await service.process_new_bookmark(bookmark.id, db_session)

    # Refresh and check content was stored
    await db_session.refresh(bookmark)
    assert bookmark.content == "# Test Article\n\nThis is the full markdown content."
