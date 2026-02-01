"""Endpoint registry for skill generation and dynamic route registration."""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class EndpointMeta:
    """Metadata for a gateway endpoint."""

    method: str
    path: str
    rate_limit: str
    description: str
    params: dict[str, Any] = field(default_factory=dict)
    response_example: Optional[dict] = None
    handler: Optional[Callable] = None


_endpoints: list[EndpointMeta] = []


def register_endpoint(meta: EndpointMeta) -> None:
    """Register an endpoint for skill generation."""
    _endpoints.append(meta)


def get_all_endpoints() -> list[EndpointMeta]:
    """Get all registered endpoints (returns copy)."""
    return _endpoints.copy()


def clear_registry() -> None:
    """Clear registry (for testing)."""
    _endpoints.clear()
