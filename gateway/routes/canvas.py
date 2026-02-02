"""Canvas gateway routes."""

import inspect
import os
from typing import Any, Optional

import httpx
from pydantic import BaseModel

from shared.gateway import gateway_endpoint

CANVAS_SERVICE_URL = os.getenv("CANVAS_SERVICE_URL", "http://localhost:8002")


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class QuotePushRequest(BaseModel):
    content: str
    source_url: Optional[str] = None
    source_title: Optional[str] = None


class DraftResponse(BaseModel):
    content: str
    updated_at: str


@gateway_endpoint(
    method="POST",
    path="/api/canvas/quotes",
    rate_limit="30/hour",
    description="Push a quote to canvas draft",
    params={
        "content": {"type": "string", "required": True},
        "source_url": {"type": "string", "required": False},
        "source_title": {"type": "string", "required": False},
    },
)
async def push_quote(req: QuotePushRequest) -> dict:
    """Push a quote to canvas for later note-taking."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CANVAS_SERVICE_URL}/api/quotes",
            json={
                "content": req.content,
                "source_url": req.source_url,
                "source_title": req.source_title,
            },
        )
        await _maybe_await(resp.raise_for_status())
        return await _maybe_await(resp.json())


@gateway_endpoint(
    method="GET",
    path="/api/canvas/draft",
    rate_limit="60/hour",
    description="Get current canvas draft content",
    params={},
)
async def get_draft() -> DraftResponse:
    """Get current canvas draft."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CANVAS_SERVICE_URL}/api/draft")
        await _maybe_await(resp.raise_for_status())
        data = await _maybe_await(resp.json())
        return DraftResponse(
            content=data.get("content", ""),
            updated_at=data.get("updated_at", ""),
        )
