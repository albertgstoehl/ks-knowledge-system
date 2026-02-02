"""Kasten gateway routes (read-only)."""

import inspect
import os
from typing import Any

import httpx
from pydantic import BaseModel

from shared.gateway import gateway_endpoint

KASTEN_SERVICE_URL = os.getenv("KASTEN_SERVICE_URL", "http://localhost:8003")


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    links: list[str]


@gateway_endpoint(
    method="GET",
    path="/api/kasten/notes/{note_id}",
    rate_limit="60/hour",
    description="Get a specific note by ID",
    params={
        "note_id": {"type": "string", "required": True, "pattern": "^[0-9]{4}[a-z]+$"},
    },
)
async def get_note(note_id: str) -> NoteResponse:
    """Get a specific Kasten note."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{KASTEN_SERVICE_URL}/api/notes/{note_id}")
        await _maybe_await(resp.raise_for_status())
        data = await _maybe_await(resp.json())
        return NoteResponse(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            links=data.get("links", []),
        )


@gateway_endpoint(
    method="GET",
    path="/api/kasten/entry-points",
    rate_limit="30/hour",
    description="Get entry point notes (notes with outgoing links but no backlinks)",
    params={},
)
async def get_entry_points() -> list[dict]:
    """Get Kasten entry points for exploration."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{KASTEN_SERVICE_URL}/api/entry-points")
        await _maybe_await(resp.raise_for_status())
        return await _maybe_await(resp.json())
