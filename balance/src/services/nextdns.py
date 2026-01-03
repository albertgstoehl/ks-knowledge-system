# balance/src/services/nextdns.py
import httpx
import os
from typing import Optional


class NextDNSError(Exception):
    """Raised when NextDNS API call fails."""
    pass


class NextDNSService:
    BASE_URL = "https://api.nextdns.io"
    YOUTUBE_DOMAIN = "youtube.com"

    def __init__(self, api_key: str = None, profile_id: str = None):
        self.api_key = api_key or os.getenv("NEXTDNS_API_KEY")
        self.profile_id = profile_id or os.getenv("NEXTDNS_PROFILE_ID")

        if not self.api_key or not self.profile_id:
            raise ValueError("NEXTDNS_API_KEY and NEXTDNS_PROFILE_ID required")

    async def unblock_youtube(self) -> bool:
        """Remove youtube.com from denylist."""
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method="DELETE",
                url=f"{self.BASE_URL}/profiles/{self.profile_id}/denylist/{self.YOUTUBE_DOMAIN}",
                headers={"X-Api-Key": self.api_key},
                timeout=10.0
            )

            if response.status_code not in (200, 204, 404):
                raise NextDNSError(f"Failed to unblock: {response.status_code}")

            return True

    async def block_youtube(self) -> bool:
        """Add youtube.com to denylist."""
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method="PUT",
                url=f"{self.BASE_URL}/profiles/{self.profile_id}/denylist/{self.YOUTUBE_DOMAIN}",
                headers={"X-Api-Key": self.api_key},
                json={"id": self.YOUTUBE_DOMAIN, "active": True},
                timeout=10.0
            )

            if response.status_code not in (200, 204):
                raise NextDNSError(f"Failed to block: {response.status_code}")

            return True


# Singleton instance (initialized on first use)
_service: Optional[NextDNSService] = None


def get_nextdns_service() -> NextDNSService:
    global _service
    if _service is None:
        _service = NextDNSService()
    return _service
