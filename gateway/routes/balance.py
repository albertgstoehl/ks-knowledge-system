"""Balance gateway routes."""

import inspect
import os
from typing import Any, Optional

import httpx
from pydantic import BaseModel

from shared.gateway import gateway_endpoint

BALANCE_SERVICE_URL = os.getenv("BALANCE_SERVICE_URL", "http://localhost:8005")


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class SessionStartRequest(BaseModel):
    session_type: str
    intention: Optional[str] = None
    priority_id: Optional[int] = None


class SessionResponse(BaseModel):
    id: int
    session_type: str
    started_at: str
    status: str


@gateway_endpoint(
    method="POST",
    path="/api/balance/sessions",
    rate_limit="20/hour",
    description="Start a focus session",
    params={
        "session_type": {
            "type": "string",
            "required": True,
            "enum": ["expected", "personal"],
        },
        "intention": {"type": "string", "required": False},
        "priority_id": {"type": "integer", "required": False},
    },
)
async def start_session(req: SessionStartRequest) -> SessionResponse:
    """Start a new focus session."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BALANCE_SERVICE_URL}/api/sessions",
            json={
                "session_type": req.session_type,
                "intention": req.intention,
                "priority_id": req.priority_id,
            },
        )
        await _maybe_await(resp.raise_for_status())
        data = await _maybe_await(resp.json())
        return SessionResponse(
            id=data["id"],
            session_type=data["session_type"],
            started_at=data["started_at"],
            status=data["status"],
        )


@gateway_endpoint(
    method="GET",
    path="/api/balance/status",
    rate_limit="120/hour",
    description="Get current balance status (on break, in session, etc)",
    params={},
)
async def get_status() -> dict:
    """Get current balance status."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BALANCE_SERVICE_URL}/api/status")
        await _maybe_await(resp.raise_for_status())
        return await _maybe_await(resp.json())
