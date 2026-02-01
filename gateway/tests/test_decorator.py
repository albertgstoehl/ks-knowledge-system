"""Tests for gateway_endpoint decorator."""

from shared.gateway.registry import clear_registry, get_all_endpoints


def test_decorator_registers_endpoint():
    """Decorator should register endpoint metadata."""
    clear_registry()

    from shared.gateway.decorator import gateway_endpoint

    @gateway_endpoint(
        method="POST",
        path="/api/test",
        rate_limit="20/hour",
        description="Test endpoint",
        params={"name": {"type": "string", "required": True}},
    )
    async def test_handler(name: str):
        return {"name": name}

    endpoints = get_all_endpoints()
    assert len(endpoints) == 1
    assert endpoints[0].method == "POST"
    assert endpoints[0].path == "/api/test"
    assert endpoints[0].rate_limit == "20/hour"
    assert endpoints[0].handler is test_handler


def test_decorator_stores_meta_on_function():
    """Decorator should store _gateway_meta on the function for middleware."""
    clear_registry()

    from shared.gateway.decorator import gateway_endpoint

    @gateway_endpoint(
        method="GET",
        path="/api/meta-test",
        rate_limit="10/hour",
        description="Meta test",
    )
    async def handler():
        return {}

    assert hasattr(handler, "_gateway_meta")
    assert handler._gateway_meta["method"] == "GET"
    assert handler._gateway_meta["path"] == "/api/meta-test"
    assert handler._gateway_meta["rate_limit"] == "10/hour"


def test_decorator_preserves_function():
    """Decorator should return the original function unchanged."""
    clear_registry()

    from shared.gateway.decorator import gateway_endpoint

    @gateway_endpoint(
        method="GET",
        path="/api/preserve",
        rate_limit="10/hour",
        description="Preserve test",
    )
    async def my_handler():
        return {"preserved": True}

    assert my_handler.__name__ == "my_handler"
