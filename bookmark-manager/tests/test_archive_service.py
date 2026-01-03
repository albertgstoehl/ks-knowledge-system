import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.archive_service import ArchiveService
import httpx
import time

@pytest.mark.asyncio
async def test_archive_submission_success():
    """Test successful URL submission to Web Archive with mocked response"""
    service = ArchiveService()

    # Mock the httpx.AsyncClient
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.url = "https://web.archive.org/web/20231201120000/https://example.com"

        mock_client.get = AsyncMock(return_value=mock_response)

        result = await service.submit_to_archive("https://example.com")

        assert result is not None
        assert "snapshot_url" in result
        assert "web.archive.org" in result["snapshot_url"]
        assert "error_type" not in result

@pytest.mark.asyncio
async def test_archive_empty_url():
    """Test handling of empty URL"""
    service = ArchiveService()

    result = await service.submit_to_archive("")
    assert result is not None
    assert result["error_type"] == "validation_error"
    assert "message" in result

@pytest.mark.asyncio
async def test_archive_none_url():
    """Test handling of None URL"""
    service = ArchiveService()

    result = await service.submit_to_archive(None)
    assert result is not None
    assert result["error_type"] == "validation_error"
    assert "message" in result

@pytest.mark.asyncio
async def test_archive_invalid_url_format():
    """Test handling of invalid URL format (no protocol)"""
    service = ArchiveService()

    # Test URL without protocol
    result = await service.submit_to_archive("example.com")
    assert result is not None
    assert result["error_type"] == "validation_error"
    assert "http://" in result["message"] or "https://" in result["message"]

    # Test whitespace-only URL
    result = await service.submit_to_archive("   ")
    assert result is not None
    assert result["error_type"] == "validation_error"

@pytest.mark.asyncio
async def test_archive_retry_logic_with_network_errors():
    """Test that retry logic works for transient network failures"""
    service = ArchiveService(timeout=5.0)

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # First two attempts fail with network error, third succeeds
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.url = "https://web.archive.org/web/20231201120000/https://example.com"

        mock_client.get = AsyncMock(side_effect=[
            httpx.NetworkError("Connection failed"),
            httpx.NetworkError("Connection failed"),
            mock_response
        ])

        result = await service.submit_to_archive("https://example.com")

        # Should succeed after retries
        assert "snapshot_url" in result
        assert "error_type" not in result
        assert mock_client.get.call_count == 3

@pytest.mark.asyncio
async def test_archive_retry_logic_with_timeouts():
    """Test that retry logic works for timeout errors"""
    service = ArchiveService(timeout=5.0)

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # First two attempts timeout, third succeeds
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.url = "https://web.archive.org/web/20231201120000/https://example.com"

        mock_client.get = AsyncMock(side_effect=[
            httpx.TimeoutException("Request timeout"),
            httpx.TimeoutException("Request timeout"),
            mock_response
        ])

        result = await service.submit_to_archive("https://example.com")

        # Should succeed after retries
        assert "snapshot_url" in result
        assert "error_type" not in result
        assert mock_client.get.call_count == 3

@pytest.mark.asyncio
async def test_archive_rate_limiting_429():
    """Test rate limiting (429) behavior with retries"""
    service = ArchiveService(timeout=5.0)

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # First two attempts get rate limited, third succeeds
        mock_429_response = AsyncMock()
        mock_429_response.status_code = 429

        mock_success_response = AsyncMock()
        mock_success_response.status_code = 200
        mock_success_response.url = "https://web.archive.org/web/20231201120000/https://example.com"

        mock_client.get = AsyncMock(side_effect=[
            mock_429_response,
            mock_429_response,
            mock_success_response
        ])

        # Patch asyncio.sleep to avoid actual waiting
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.submit_to_archive("https://example.com")

        # Should succeed after retries
        assert "snapshot_url" in result
        assert "error_type" not in result
        assert mock_client.get.call_count == 3

@pytest.mark.asyncio
async def test_archive_rate_limiting_exhausted():
    """Test rate limiting when all retries are exhausted"""
    service = ArchiveService(timeout=5.0)

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # All attempts get rate limited
        mock_429_response = AsyncMock()
        mock_429_response.status_code = 429

        mock_client.get = AsyncMock(return_value=mock_429_response)

        # Patch asyncio.sleep to avoid actual waiting
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.submit_to_archive("https://example.com")

        # Should return rate limit error
        assert result["error_type"] == "rate_limit_error"
        assert "rate limit" in result["message"].lower()
        assert mock_client.get.call_count == 3

@pytest.mark.asyncio
async def test_archive_timeout_handling():
    """Test timeout error handling when all retries fail"""
    service = ArchiveService(timeout=5.0)

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # All attempts timeout
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))

        # Patch asyncio.sleep to avoid actual waiting
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.submit_to_archive("https://example.com")

        # Should return timeout error
        assert result["error_type"] == "timeout_error"
        assert "timed out" in result["message"].lower() or "timeout" in result["message"].lower()
        assert mock_client.get.call_count == 3

@pytest.mark.asyncio
async def test_archive_network_error_handling():
    """Test network error handling when all retries fail"""
    service = ArchiveService(timeout=5.0)

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # All attempts fail with network error
        mock_client.get = AsyncMock(side_effect=httpx.NetworkError("Connection refused"))

        # Patch asyncio.sleep to avoid actual waiting
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.submit_to_archive("https://example.com")

        # Should return network error
        assert result["error_type"] == "network_error"
        assert "message" in result
        assert mock_client.get.call_count == 3

@pytest.mark.asyncio
async def test_archive_http_status_error():
    """Test HTTP status error handling"""
    service = ArchiveService(timeout=5.0)

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock HTTP status error
        mock_response = MagicMock()
        mock_response.status_code = 503
        error = httpx.HTTPStatusError("Service unavailable", request=MagicMock(), response=mock_response)

        mock_client.get = AsyncMock(side_effect=error)

        result = await service.submit_to_archive("https://example.com")

        # Should return HTTP status error
        assert result["error_type"] == "http_status_error"
        assert "503" in result["message"]

@pytest.mark.asyncio
async def test_archive_configurable_timeout():
    """Test that timeout is configurable via constructor"""
    service = ArchiveService(timeout=15.0)
    assert service.timeout == 15.0

    service_with_default = ArchiveService()
    assert service_with_default.timeout == 60.0

@pytest.mark.asyncio
async def test_archive_exponential_backoff():
    """Test that exponential backoff is applied on retries"""
    service = ArchiveService(timeout=5.0)

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # All attempts fail with network error
        mock_client.get = AsyncMock(side_effect=httpx.NetworkError("Connection failed"))

        # Patch asyncio.sleep to track delays
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await service.submit_to_archive("https://example.com")

            # Verify exponential backoff pattern
            assert mock_sleep.call_count == 2  # Called for first two retries (not on last)
            # First retry: 1.0 * (2^0) = 1.0
            # Second retry: 1.0 * (2^1) = 2.0
            delays = [call.args[0] for call in mock_sleep.call_args_list]
            assert delays[0] == 1.0
            assert delays[1] == 2.0
