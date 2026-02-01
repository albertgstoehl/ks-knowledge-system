"""Tests for rate limiting."""

import pytest


def test_parse_rate_limit_hour():
    """Parse '20/hour' correctly."""
    from shared.gateway.ratelimit import parse_rate_limit

    count, seconds = parse_rate_limit("20/hour")
    assert count == 20
    assert seconds == 3600


def test_parse_rate_limit_minute():
    """Parse '100/minute' correctly."""
    from shared.gateway.ratelimit import parse_rate_limit

    count, seconds = parse_rate_limit("100/minute")
    assert count == 100
    assert seconds == 60


def test_parse_rate_limit_day():
    """Parse '5/day' correctly."""
    from shared.gateway.ratelimit import parse_rate_limit

    count, seconds = parse_rate_limit("5/day")
    assert count == 5
    assert seconds == 86400


@pytest.mark.asyncio
async def test_check_rate_limit_allows_within_limit(tmp_path):
    """Requests within limit should be allowed."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "test_ratelimit.db")

    from shared.gateway.ratelimit import init_ratelimit_db, check_rate_limit

    await init_ratelimit_db()

    assert (
        await check_rate_limit("/test", "client1", limit=3, window_seconds=3600) is True
    )
    assert (
        await check_rate_limit("/test", "client1", limit=3, window_seconds=3600) is True
    )
    assert (
        await check_rate_limit("/test", "client1", limit=3, window_seconds=3600) is True
    )


@pytest.mark.asyncio
async def test_check_rate_limit_blocks_over_limit(tmp_path):
    """Requests over limit should be blocked."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "test_ratelimit2.db")

    from shared.gateway.ratelimit import init_ratelimit_db, check_rate_limit

    await init_ratelimit_db()

    for _ in range(3):
        await check_rate_limit("/test", "client1", limit=3, window_seconds=3600)

    assert (
        await check_rate_limit("/test", "client1", limit=3, window_seconds=3600)
        is False
    )


@pytest.mark.asyncio
async def test_check_rate_limit_separate_clients(tmp_path):
    """Different clients should have separate limits."""
    import os

    os.environ["GATEWAY_DB_PATH"] = str(tmp_path / "test_ratelimit3.db")

    from shared.gateway.ratelimit import init_ratelimit_db, check_rate_limit

    await init_ratelimit_db()

    for _ in range(3):
        await check_rate_limit("/test", "client1", limit=3, window_seconds=3600)

    assert (
        await check_rate_limit("/test", "client2", limit=3, window_seconds=3600) is True
    )
