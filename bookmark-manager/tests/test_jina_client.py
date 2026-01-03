import pytest
from unittest.mock import AsyncMock, patch
from src.services.jina_client import JinaClient
import httpx

@pytest.mark.asyncio
async def test_jina_extract_metadata():
    """Test Jina AI metadata extraction"""
    client = JinaClient()
    result = await client.extract_metadata("https://example.com")

    assert "title" in result
    assert "description" in result
    assert "content" in result

@pytest.mark.asyncio
async def test_jina_retry_logic():
    """Test that retry logic works for transient failures"""
    client = JinaClient(timeout=5.0)

    # Mock the httpx.AsyncClient to simulate transient failures
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # First two attempts fail with network error, third succeeds
        mock_response = AsyncMock()
        mock_response.text = "Title: Test Page\n\nMarkdown Content:\nTest description"
        mock_response.raise_for_status = AsyncMock()

        mock_client.get = AsyncMock(side_effect=[
            httpx.NetworkError("Connection failed"),
            httpx.NetworkError("Connection failed"),
            mock_response
        ])

        result = await client.extract_metadata("https://example.com")

        # Should succeed after retries
        assert result["title"] == "Test Page"
        assert "error_type" not in result
        assert mock_client.get.call_count == 3

@pytest.mark.asyncio
async def test_jina_empty_url():
    """Test handling of empty URL"""
    client = JinaClient()

    result = await client.extract_metadata("")
    assert result["error_type"] == "validation_error"
    assert result["title"] == "Error"

@pytest.mark.asyncio
async def test_jina_invalid_url():
    """Test handling of invalid URL format"""
    client = JinaClient()

    # Test URL without protocol
    result = await client.extract_metadata("example.com")
    assert result["error_type"] == "validation_error"
    assert result["title"] == "Error"

    # Test None URL
    result = await client.extract_metadata(None)
    assert result["error_type"] == "validation_error"
    assert result["title"] == "Error"

    # Test whitespace-only URL
    result = await client.extract_metadata("   ")
    assert result["error_type"] == "validation_error"
    assert result["title"] == "Error"

@pytest.mark.asyncio
async def test_jina_configurable_timeout():
    """Test that timeout is configurable"""
    client = JinaClient(timeout=15.0)
    assert client.timeout == 15.0

    client_with_default = JinaClient()
    assert client_with_default.timeout == 30.0
