import httpx
from typing import Dict, Optional
import logging
import asyncio

logger = logging.getLogger(__name__)

class JinaClient:
    def __init__(self, api_key: Optional[str] = None, timeout: float = 30.0):
        self.base_url = "https://r.jina.ai"
        self.api_key = api_key
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

    async def extract_metadata(self, url: str) -> Dict[str, str]:
        """Extract title, description, and content from URL using Jina AI

        Implements retry logic with exponential backoff for transient failures.
        """
        # Validate input
        try:
            self._validate_url(url)
        except ValueError as e:
            logger.error(f"Invalid URL: {e}")
            return {
                "title": "Error",
                "description": "",
                "content": "",
                "error_type": "validation_error"
            }

        # Retry loop with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        f"{self.base_url}/{url}",
                        headers=headers,
                        follow_redirects=True
                    )
                    response.raise_for_status()

                    # Jina returns markdown content
                    content = response.text

                    # Extract title and description from Jina response
                    title = ""
                    description = ""
                    lines = content.split("\n")

                    # Look for "Title:" prefix in the response
                    for i, line in enumerate(lines):
                        if line.startswith("Title: "):
                            title = line[7:].strip()
                        elif line.startswith("# ") and not title:
                            title = line[2:].strip()

                    # Extract description from the markdown content section
                    in_markdown_section = False
                    for line in lines:
                        if "Markdown Content:" in line:
                            in_markdown_section = True
                            continue
                        if in_markdown_section and line.strip() and not line.startswith("["):
                            description = line.strip()
                            break

                    return {
                        "title": title or "Untitled",
                        "description": description or "",
                        "content": content
                    }

            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as e:
                # Transient errors - retry with exponential backoff
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Transient error for {url} (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Max retries reached for {url}: {e}")

            except httpx.HTTPStatusError as e:
                # HTTP errors (4xx, 5xx) - don't retry client errors
                logger.error(f"HTTP error for {url}: {e.response.status_code}")
                return {
                    "title": "Error fetching content",
                    "description": "",
                    "content": "",
                    "error_type": "http_error"
                }

            except httpx.HTTPError as e:
                # Other HTTP errors
                logger.error(f"Jina API error for {url}: {e}")
                return {
                    "title": "Error fetching content",
                    "description": "",
                    "content": "",
                    "error_type": "api_error"
                }

            except Exception as e:
                logger.error(f"Unexpected error extracting metadata for {url}: {e}")
                return {
                    "title": "Error",
                    "description": "",
                    "content": "",
                    "error_type": "unexpected_error"
                }

        # If we exhausted all retries
        logger.error(f"Failed to extract metadata for {url} after {self.max_retries} attempts")
        return {
            "title": "Error fetching content",
            "description": "",
            "content": "",
            "error_type": "network_error"
        }
