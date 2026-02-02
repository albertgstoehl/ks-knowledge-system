"""Gateway middleware for rate limiting and audit logging."""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from shared.gateway.audit import log_request
from shared.gateway.ratelimit import check_rate_limit, parse_rate_limit


class GatewayMiddleware(BaseHTTPMiddleware):
    """Middleware that applies rate limiting and audit logging to gateway endpoints."""

    async def dispatch(self, request: Request, call_next):
        route_meta = None
        for route in request.app.router.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL and hasattr(route, "endpoint"):
                endpoint = route.endpoint
                if hasattr(endpoint, "_gateway_meta"):
                    route_meta = endpoint._gateway_meta
                    break

        if route_meta:
            meta = route_meta
            client_ip = request.client.host if request.client else "unknown"
            limit, window = parse_rate_limit(meta["rate_limit"])

            if not await check_rate_limit(meta["path"], client_ip, limit, window):
                await log_request(
                    meta["path"],
                    meta["method"],
                    client_ip,
                    {},
                    429,
                    "Rate limit exceeded",
                )
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                )

            try:
                response = await call_next(request)
                await log_request(
                    meta["path"],
                    meta["method"],
                    client_ip,
                    {},
                    response.status_code,
                )
                return response
            except Exception as exc:
                await log_request(
                    meta["path"],
                    meta["method"],
                    client_ip,
                    {},
                    500,
                    str(exc),
                )
                raise

        return await call_next(request)
