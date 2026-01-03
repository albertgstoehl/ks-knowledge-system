# tests/test_zotero_service.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.zotero_service import ZoteroService

@pytest.fixture
def zotero_service():
    return ZoteroService(api_key="test_key", user_id="12345")


class TestZoteroService:
    @pytest.mark.asyncio
    async def test_create_item_with_doi(self, zotero_service):
        with patch.object(zotero_service, '_fetch_metadata_by_doi') as mock_fetch:
            mock_fetch.return_value = {
                "title": "Test Paper",
                "creators": [{"firstName": "John", "lastName": "Doe", "creatorType": "author"}],
                "date": "2024",
            }
            with patch.object(zotero_service, '_create_zotero_item') as mock_create:
                mock_create.return_value = "ABC123"

                result = await zotero_service.sync_paper(
                    url="https://doi.org/10.1000/test",
                    title="Test Paper",
                    doi="10.1000/test"
                )

                assert result["zotero_key"] == "ABC123"
                assert result["needs_manual"] is False

    @pytest.mark.asyncio
    async def test_create_item_without_doi(self, zotero_service):
        with patch.object(zotero_service, '_create_zotero_item') as mock_create:
            mock_create.return_value = "XYZ789"

            result = await zotero_service.sync_paper(
                url="https://example.com/paper",
                title="Unknown Paper",
                doi=None
            )

            assert result["zotero_key"] == "XYZ789"
            assert result["needs_manual"] is True
