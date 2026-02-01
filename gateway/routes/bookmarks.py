"""Bookmark manager gateway routes."""

import inspect
import os
from typing import Any, Optional

import httpx
from pydantic import BaseModel, HttpUrl

from shared.gateway import gateway_endpoint

BOOKMARK_SERVICE_URL = os.getenv("BOOKMARK_SERVICE_URL", "http://localhost:8001")


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class BookmarkCreateRequest(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    is_thesis: bool = False
    pinned: bool = False


class BookmarkResponse(BaseModel):
    id: int
    url: str
    title: Optional[str]
    summary: Optional[str]
    created_at: str


@gateway_endpoint(
    method="POST",
    path="/api/bookmarks",
    rate_limit="30/hour",
    description="Create a new bookmark",
    params={
        "url": {"type": "string", "required": True, "format": "url"},
        "title": {"type": "string", "required": False},
        "is_thesis": {"type": "boolean", "required": False, "default": False},
        "pinned": {"type": "boolean", "required": False, "default": False},
    },
)
async def create_bookmark(req: BookmarkCreateRequest) -> BookmarkResponse:
    """Create a new bookmark via gateway."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BOOKMARK_SERVICE_URL}/api/bookmarks",
            json={
                "url": str(req.url),
                "title": req.title,
                "is_thesis": req.is_thesis,
                "pinned": req.pinned,
            },
        )
        await _maybe_await(resp.raise_for_status())
        data = await _maybe_await(resp.json())

        return BookmarkResponse(
            id=data["id"],
            url=data["url"],
            title=data.get("title"),
            summary=data.get("summary"),
            created_at=data["created_at"],
        )


@gateway_endpoint(
    method="GET",
    path="/api/bookmarks",
    rate_limit="60/hour",
    description="List recent bookmarks",
    params={
        "limit": {"type": "integer", "required": False, "default": 20, "max": 100},
    },
)
async def list_bookmarks(limit: int = 20) -> list[BookmarkResponse]:
    """List recent bookmarks."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BOOKMARK_SERVICE_URL}/api/bookmarks",
            params={"limit": min(limit, 100)},
        )
        await _maybe_await(resp.raise_for_status())
        data = await _maybe_await(resp.json())

        return [
            BookmarkResponse(
                id=item["id"],
                url=item["url"],
                title=item.get("title"),
                summary=item.get("summary"),
                created_at=item["created_at"],
            )
            for item in data
        ]
