"""Gateway endpoint decorator for dynamic route registration."""

from typing import Any, Callable, Optional

from .registry import EndpointMeta, register_endpoint


def gateway_endpoint(
    method: str,
    path: str,
    rate_limit: str,
    description: str,
    params: Optional[dict[str, Any]] = None,
    response_example: Optional[dict] = None,
):
    """
    Decorator that registers endpoint for dynamic route registration.

    Routes are registered automatically on app startup from the registry.
    Middleware handles rate limiting and audit logging via _gateway_meta.

    Usage:
        @gateway_endpoint(
            method="POST",
            path="/api/bookmarks",
            rate_limit="30/hour",
            description="Create a new bookmark",
            params={"url": {"type": "string", "required": True}},
        )
        async def create_bookmark(req: BookmarkRequest) -> BookmarkResponse:
            ...
    """

    def decorator(func: Callable) -> Callable:
        func._gateway_meta = {
            "method": method,
            "path": path,
            "rate_limit": rate_limit,
        }

        meta = EndpointMeta(
            method=method,
            path=path,
            rate_limit=rate_limit,
            description=description,
            params=params or {},
            response_example=response_example,
            handler=func,
        )
        register_endpoint(meta)

        return func

    return decorator
