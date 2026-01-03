# balance/tests/test_nextdns.py
import pytest
from unittest.mock import AsyncMock, patch
from src.services.nextdns import NextDNSService, NextDNSError


@pytest.fixture
def nextdns_service():
    return NextDNSService(
        api_key="test-api-key",
        profile_id="test-profile"
    )


@pytest.mark.asyncio
async def test_unblock_youtube_success(nextdns_service):
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_request.return_value = AsyncMock(status_code=204)

        result = await nextdns_service.unblock_youtube()

        assert result is True
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_block_youtube_success(nextdns_service):
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_request.return_value = AsyncMock(status_code=204)

        result = await nextdns_service.block_youtube()

        assert result is True


@pytest.mark.asyncio
async def test_unblock_youtube_api_failure(nextdns_service):
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_request.return_value = AsyncMock(status_code=500)

        with pytest.raises(NextDNSError):
            await nextdns_service.unblock_youtube()
