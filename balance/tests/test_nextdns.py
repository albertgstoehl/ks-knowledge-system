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
    with patch("httpx.AsyncClient.patch") as mock_patch:
        mock_patch.return_value = AsyncMock(status_code=204)

        result = await nextdns_service.unblock_youtube()

        assert result is True
        mock_patch.assert_called_once()
        # Verify it sets active=False (unblock)
        call_kwargs = mock_patch.call_args[1]
        assert call_kwargs["json"] == {"active": False}


@pytest.mark.asyncio
async def test_block_youtube_success(nextdns_service):
    with patch("httpx.AsyncClient.patch") as mock_patch:
        mock_patch.return_value = AsyncMock(status_code=204)

        result = await nextdns_service.block_youtube()

        assert result is True
        # Verify it sets active=True (block)
        call_kwargs = mock_patch.call_args[1]
        assert call_kwargs["json"] == {"active": True}


@pytest.mark.asyncio
async def test_unblock_youtube_api_failure(nextdns_service):
    with patch("httpx.AsyncClient.patch") as mock_patch:
        mock_patch.return_value = AsyncMock(status_code=500)

        with pytest.raises(NextDNSError):
            await nextdns_service.unblock_youtube()
