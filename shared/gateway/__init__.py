"""Shared gateway framework for Clawdbot integration."""

from .registry import EndpointMeta, register_endpoint, get_all_endpoints, clear_registry
from .decorator import gateway_endpoint
from .skill import generate_skill_markdown
from .ratelimit import init_ratelimit_db, check_rate_limit, parse_rate_limit
from .audit import init_audit_db, log_request, get_recent_logs

__all__ = [
    "EndpointMeta",
    "register_endpoint",
    "get_all_endpoints",
    "clear_registry",
    "gateway_endpoint",
    "generate_skill_markdown",
    "init_ratelimit_db",
    "check_rate_limit",
    "parse_rate_limit",
    "init_audit_db",
    "log_request",
    "get_recent_logs",
]
