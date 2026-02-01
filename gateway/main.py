"""Knowledge Gateway API for Clawdbot integration."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from shared.gateway import get_all_endpoints, init_ratelimit_db, init_audit_db
from shared.gateway.skill import generate_skill_markdown
from gateway.middleware import GatewayMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize databases on startup."""
    await init_ratelimit_db()
    await init_audit_db()
    yield


app = FastAPI(
    title="Knowledge Gateway",
    description="Gateway API for knowledge-system services",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(GatewayMiddleware)


def register_gateway_routes(app: FastAPI) -> None:
    """Register all decorated endpoints from the registry."""
    for ep in get_all_endpoints():
        if ep.method == "GET":
            app.get(ep.path)(ep.handler)
        elif ep.method == "POST":
            app.post(ep.path)(ep.handler)
        elif ep.method == "PUT":
            app.put(ep.path)(ep.handler)
        elif ep.method == "DELETE":
            app.delete(ep.path)(ep.handler)
        elif ep.method == "PATCH":
            app.patch(ep.path)(ep.handler)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/skill", response_class=PlainTextResponse)
async def get_skill():
    """Return auto-generated OpenClaw skill."""
    return generate_skill_markdown(
        name="knowledge-gateway",
        description="API for bookmark manager, canvas, kasten, balance",
        base_url_env="KNOWLEDGE_GATEWAY_URL",
    )


# Import routes to trigger decorator registration
from gateway.routes import bookmarks, canvas, balance, kasten  # noqa: F401

# Register all gateway routes after imports
register_gateway_routes(app)
