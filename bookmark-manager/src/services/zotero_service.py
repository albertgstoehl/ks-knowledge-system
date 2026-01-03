"""Zotero Web API integration for paper sync."""

import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

ZOTERO_API_BASE = "https://api.zotero.org"
API_VERSION = "3"


class ZoteroService:
    def __init__(self, api_key: str = None, user_id: str = None):
        import os
        self.api_key = api_key or os.getenv("ZOTERO_API_KEY")
        self.user_id = user_id or os.getenv("ZOTERO_USER_ID")

        if not self.api_key or not self.user_id:
            logger.warning("Zotero API credentials not configured")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Zotero-API-Key": self.api_key,
            "Zotero-API-Version": API_VERSION,
            "Content-Type": "application/json",
        }

    async def _fetch_metadata_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Fetch metadata from CrossRef by DOI."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.crossref.org/works/{doi}",
                    timeout=30.0
                )
                if not response.is_success:
                    return None

                data = response.json()
                work = data.get("message", {})

                creators = []
                for author in work.get("author", []):
                    creators.append({
                        "creatorType": "author",
                        "firstName": author.get("given", ""),
                        "lastName": author.get("family", ""),
                    })

                date_parts = work.get("published", {}).get("date-parts", [[]])
                date = "-".join(str(p) for p in date_parts[0]) if date_parts[0] else None

                return {
                    "itemType": "journalArticle",
                    "title": work.get("title", ["Untitled"])[0],
                    "creators": creators,
                    "date": date,
                    "DOI": doi,
                    "url": work.get("URL"),
                    "abstractNote": work.get("abstract", "").replace("<jats:p>", "").replace("</jats:p>", ""),
                    "publicationTitle": work.get("container-title", [""])[0],
                }
        except Exception as e:
            logger.error(f"Failed to fetch DOI metadata: {e}")
            return None

    async def _create_zotero_item(self, item_data: Dict[str, Any], tags: list) -> Optional[str]:
        """Create item in Zotero library."""
        if not self.api_key or not self.user_id:
            logger.error("Zotero credentials not configured")
            return None

        item_data["tags"] = [{"tag": t} for t in tags]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{ZOTERO_API_BASE}/users/{self.user_id}/items",
                    headers=self._get_headers(),
                    json=[item_data],
                    timeout=30.0
                )

                if not response.is_success:
                    logger.error(f"Zotero API error: {response.status_code} - {response.text}")
                    return None

                result = response.json()
                successful = result.get("successful", {})
                if successful:
                    return list(successful.values())[0].get("key")

                failed = result.get("failed", {})
                if failed:
                    logger.error(f"Zotero creation failed: {failed}")

                return None
        except Exception as e:
            logger.error(f"Failed to create Zotero item: {e}")
            return None

    async def sync_paper(
        self,
        url: str,
        title: str,
        doi: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sync paper to Zotero.

        Returns:
            Dict with zotero_key and needs_manual flag
        """
        tags = ["bookmark-manager"]
        item_data = None
        needs_manual = False

        # Try to get metadata from DOI
        if doi:
            item_data = await self._fetch_metadata_by_doi(doi)

        # Fallback to basic item
        if not item_data:
            needs_manual = True
            tags.append("needs-doi")
            item_data = {
                "itemType": "webpage",
                "title": title,
                "url": url,
            }

        zotero_key = await self._create_zotero_item(item_data, tags)

        return {
            "zotero_key": zotero_key,
            "needs_manual": needs_manual,
        }
