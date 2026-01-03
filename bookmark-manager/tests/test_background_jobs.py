import pytest
from src.services.background_jobs import BackgroundJobService
from src.models import Bookmark, Embedding, BookmarkState
from src import database
from sqlalchemy import select
import os
import json

@pytest.mark.asyncio
async def test_process_new_bookmark():
    """Test processing a new bookmark with all services"""
    # Setup test database
    test_db = "test_background_jobs.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    await database.init_db(f"sqlite+aiosqlite:///{test_db}")

    # Create test bookmark
    async with database.async_session_maker() as session:
        bookmark = Bookmark(
            url="https://example.com",
            state=BookmarkState.inbox
        )
        session.add(bookmark)
        await session.commit()
        await session.refresh(bookmark)
        bookmark_id = bookmark.id

    # Process bookmark
    job_service = BackgroundJobService()

    async with database.async_session_maker() as session:
        await job_service.process_new_bookmark(bookmark_id, session)

    # Verify bookmark was processed
    async with database.async_session_maker() as session:
        # Check bookmark metadata was updated
        result = await session.execute(
            select(Bookmark).where(Bookmark.id == bookmark_id)
        )
        processed_bookmark = result.scalar_one()

        assert processed_bookmark.title is not None
        assert processed_bookmark.title != ""
        # Archive URL might be None if archive.org is slow/fails
        # assert processed_bookmark.archive_url is not None

        # Check embedding was created
        result = await session.execute(
            select(Embedding).where(Embedding.bookmark_id == bookmark_id)
        )
        embedding = result.scalar_one()

        assert embedding is not None
        assert embedding.embedding_data is not None

        # Verify embedding data is valid JSON and has correct dimension
        embedding_vector = json.loads(embedding.embedding_data)
        assert isinstance(embedding_vector, list)
        assert len(embedding_vector) == 384  # all-MiniLM-L6-v2 dimension

    # Cleanup
    os.remove(test_db)


@pytest.mark.asyncio
async def test_process_nonexistent_bookmark():
    """Test processing a bookmark that doesn't exist"""
    # Setup test database
    test_db = "test_background_jobs_nonexistent.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    await database.init_db(f"sqlite+aiosqlite:///{test_db}")

    # Process non-existent bookmark
    job_service = BackgroundJobService()

    async with database.async_session_maker() as session:
        # Should not raise an error, just log and return
        await job_service.process_new_bookmark(9999, session)

    # Cleanup
    os.remove(test_db)


@pytest.mark.asyncio
async def test_lazy_loading_embedding_service():
    """Test that embedding service is lazy loaded"""
    job_service = BackgroundJobService()

    # Initially, embedding service should be None
    assert job_service.embedding_service is None

    # After getting it, should be initialized
    embedding_service = job_service._get_embedding_service()
    assert embedding_service is not None
    assert job_service.embedding_service is not None

    # Getting it again should return the same instance
    embedding_service2 = job_service._get_embedding_service()
    assert embedding_service is embedding_service2
