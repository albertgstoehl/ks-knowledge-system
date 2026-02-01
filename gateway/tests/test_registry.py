"""Tests for endpoint registry."""

from shared.gateway.registry import (
    EndpointMeta,
    register_endpoint,
    get_all_endpoints,
    clear_registry,
)


def test_register_endpoint_adds_to_registry():
    """Registering an endpoint should add it to the global registry."""
    clear_registry()

    meta = EndpointMeta(
        method="GET",
        path="/test",
        rate_limit="10/hour",
        description="Test endpoint",
        params={},
        handler=lambda: None,
    )
    register_endpoint(meta)

    endpoints = get_all_endpoints()
    assert len(endpoints) == 1
    assert endpoints[0].path == "/test"


def test_get_all_endpoints_returns_copy():
    """get_all_endpoints should return a copy, not the original list."""
    clear_registry()

    meta = EndpointMeta(
        method="GET",
        path="/test",
        rate_limit="10/hour",
        description="Test",
        params={},
        handler=lambda: None,
    )
    register_endpoint(meta)

    endpoints1 = get_all_endpoints()
    endpoints2 = get_all_endpoints()

    assert endpoints1 is not endpoints2


def test_clear_registry():
    """clear_registry should remove all endpoints."""
    meta = EndpointMeta(
        method="GET",
        path="/test",
        rate_limit="10/hour",
        description="Test",
        params={},
        handler=lambda: None,
    )
    register_endpoint(meta)
    clear_registry()

    assert len(get_all_endpoints()) == 0
