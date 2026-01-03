import httpx
from typing import Optional, Dict
import logging
import asyncio

logger = logging.getLogger(__name__)

class ArchiveService:
    def __init__(self, timeout: float = 60.0):
        self.save_url = "https://web.archive.org/save"
        self.timeout = timeout
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay for exponential backoff

    def _validate_url(self, url: str) -> None:
        """Validate URL input before making API calls"""
        if not url or not isinstance(url, str):
            raise ValueError("URL must be a non-empty string")

        url_stripped = url.strip()
        if not url_stripped:
            raise ValueError("URL must be a non-empty string")

        # Basic URL format validation
        if not (url_stripped.startswith("http://") or url_stripped.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")

    async def submit_to_archive(self, url: str) -> Optional[Dict[str, str]]:
        """Submit URL to Web Archive and return snapshot URL or error info

        Returns:
            Dict with either:
            - {"snapshot_url": str} on success
            - {"error_type": str, "message": str} on failure
        """
        # Validate input
        try:
            self._validate_url(url)
        except ValueError as e:
            logger.error(f"Invalid URL: {e}")
            return {
                "error_type": "validation_error",
                "message": str(e)
            }

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; BookmarkManager/1.0; +https://github.com/bookmark-manager)"
        }

        last_exception = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    response = await client.get(f"{self.save_url}/{url}", headers=headers)

                    if response.status_code == 200:
                        # Archive.org redirects to the snapshot URL
                        snapshot_url = str(response.url)
                        logger.info(f"Successfully archived {url}: {snapshot_url}")
                        return {"snapshot_url": snapshot_url}
                    elif response.status_code == 429:
                        # Rate limited - exponential backoff
                        if attempt < self.max_retries - 1:
                            delay = self.base_delay * (2 ** attempt) * 5  # Longer delays for rate limits
                            logger.warning(f"Archive rate limited (attempt {attempt + 1}/{self.max_retries}), waiting {delay}s before retry")
                            await asyncio.sleep(delay)
                        else:
                            logger.error(f"Archive rate limited after {self.max_retries} attempts")
                            return {
                                "error_type": "rate_limit_error",
                                "message": "Archive service rate limit exceeded"
                            }
                    else:
                        logger.warning(f"Archive attempt {attempt + 1} failed with status {response.status_code}")
                        if attempt >= self.max_retries - 1:
                            return {
                                "error_type": "http_error",
                                "message": f"HTTP {response.status_code}"
                            }

            except httpx.TimeoutException as e:
                # Timeout - retry with exponential backoff
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Archive timeout for {url} (attempt {attempt + 1}/{self.max_retries}). Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Archive timeout after {self.max_retries} attempts")
                    return {
                        "error_type": "timeout_error",
                        "message": "Request timed out"
                    }

            except httpx.NetworkError as e:
                # Network error - retry with exponential backoff
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Archive network error for {url} (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Archive network error after {self.max_retries} attempts: {e}")
                    return {
                        "error_type": "network_error",
                        "message": str(e)
                    }

            except httpx.HTTPStatusError as e:
                # HTTP status error - don't retry client errors (4xx)
                logger.error(f"Archive HTTP status error for {url}: {e.response.status_code}")
                return {
                    "error_type": "http_status_error",
                    "message": f"HTTP {e.response.status_code}"
                }

            except Exception as e:
                logger.error(f"Unexpected archive error for {url}: {e}")
                return {
                    "error_type": "unexpected_error",
                    "message": str(e)
                }

        logger.error(f"Failed to archive {url} after {self.max_retries} attempts")
        return {
            "error_type": "max_retries_exceeded",
            "message": f"Failed after {self.max_retries} attempts"
        }
