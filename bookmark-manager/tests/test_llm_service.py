import pytest
import os
from src.services.llm_service import LLMService
from unittest.mock import AsyncMock, patch, MagicMock
from claude_agent_sdk import AssistantMessage, TextBlock

@pytest.mark.asyncio
async def test_summarize_content():
    """Test LLM content summarization"""
    service = LLMService(oauth_token="test-token")

    content = "This is a long article about machine learning..."
    url = "https://example.com/article"

    # Mock the query function from claude_agent_sdk
    with patch('src.services.llm_service.query') as mock_query:
        # Create mock message with text block
        text_block = TextBlock(text="A concise summary about ML.")
        mock_message = AssistantMessage(
            content=[text_block],
            model="haiku"
        )

        # Make query return async iterator with our mock message
        async def mock_async_iter():
            yield mock_message

        mock_query.return_value = mock_async_iter()

        summary = await service.summarize_content(content, url)

        assert summary == "A concise summary about ML."
        assert len(summary) > 0

@pytest.mark.asyncio
async def test_summarize_empty_content():
    """Test handling of empty content"""
    service = LLMService(oauth_token="test-token")

    summary = await service.summarize_content("", "https://example.com")
    assert summary == ""

    summary = await service.summarize_content("   ", "https://example.com")
    assert summary == ""

def test_missing_oauth_token():
    """Test that missing token raises error"""
    # Clear env var temporarily
    old_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if "CLAUDE_CODE_OAUTH_TOKEN" in os.environ:
        del os.environ["CLAUDE_CODE_OAUTH_TOKEN"]

    try:
        with pytest.raises(ValueError, match="CLAUDE_CODE_OAUTH_TOKEN is required"):
            LLMService()
    finally:
        # Restore env var
        if old_token:
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = old_token

@pytest.mark.asyncio
async def test_summarize_api_error():
    """Test handling of API errors"""
    service = LLMService(oauth_token="test-token")

    content = "Test content"
    url = "https://example.com"

    with patch('src.services.llm_service.query') as mock_query:
        # Make query raise an exception
        async def mock_error_iter():
            raise Exception("API Error")
            yield  # Make it a generator

        mock_query.return_value = mock_error_iter()

        summary = await service.summarize_content(content, url)

        # Should return empty string on error
        assert summary == ""
