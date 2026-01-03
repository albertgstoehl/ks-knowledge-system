import pytest
from unittest.mock import AsyncMock, patch
from src.services.background_jobs import BackgroundJobService
from src.models import Bookmark
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_background_job_with_llm(tmp_path):
    """Test full background job flow with LLM summarization"""
    from src import database

    # Setup test database
    test_db = tmp_path / "test.db"
    await database.init_db(f"sqlite+aiosqlite:///{test_db}")

    # Create service with mock LLM
    service = BackgroundJobService(oauth_token="test-token")

    # Mock Jina client
    with patch.object(service.jina_client, 'extract_metadata', new_callable=AsyncMock) as mock_jina:
        mock_jina.return_value = {
            "title": "Test Article",
            "description": "Short meta description",
            "content": "This is a long article about testing. It has multiple paragraphs with detailed information about how to write good tests."
        }

        # Mock LLM service
        with patch.object(service, '_get_llm_service') as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.summarize_content = AsyncMock(return_value="This article explains testing best practices. It covers writing good tests with detailed examples.")
            mock_get_llm.return_value = mock_llm

            # Create bookmark
            async with database.async_session_maker() as session:
                bookmark = Bookmark(url="https://example.com/test", title="Temp")
                session.add(bookmark)
                await session.commit()
                bookmark_id = bookmark.id

            # Process bookmark
            async with database.async_session_maker() as session:
                await service.process_new_bookmark(bookmark_id, session)

            # Verify LLM summary was used
            async with database.async_session_maker() as session:
                result = await session.get(Bookmark, bookmark_id)
                assert result.title == "Test Article"
                assert result.description == "This article explains testing best practices. It covers writing good tests with detailed examples."
                assert result.description != "Short meta description"  # LLM summary used, not Jina
