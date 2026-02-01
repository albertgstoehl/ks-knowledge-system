"""Tests for skill generation."""

from shared.gateway.registry import clear_registry


def test_generate_skill_markdown_header():
    """Skill should have YAML frontmatter."""
    clear_registry()

    from shared.gateway.skill import generate_skill_markdown

    skill = generate_skill_markdown(
        name="test-gateway",
        description="Test gateway",
        base_url_env="TEST_URL",
    )

    assert skill.startswith("---")
    assert "name: test-gateway" in skill
    assert "description: Test gateway" in skill
    assert "TEST_URL" in skill


def test_generate_skill_markdown_includes_endpoints():
    """Skill should include registered endpoints."""
    clear_registry()

    from shared.gateway.decorator import gateway_endpoint
    from shared.gateway.skill import generate_skill_markdown

    @gateway_endpoint(
        method="POST",
        path="/api/items",
        rate_limit="10/hour",
        description="Create an item",
        params={"name": {"type": "string", "required": True}},
    )
    async def create_item():
        pass

    skill = generate_skill_markdown(
        name="test-gateway",
        description="Test",
        base_url_env="TEST_URL",
    )

    assert "## POST /api/items" in skill
    assert "Create an item" in skill
    assert "10/hour" in skill
    assert "name: string, required" in skill


def test_generate_skill_markdown_param_details():
    """Skill should include param constraints."""
    clear_registry()

    from shared.gateway.decorator import gateway_endpoint
    from shared.gateway.skill import generate_skill_markdown

    @gateway_endpoint(
        method="GET",
        path="/api/search",
        rate_limit="60/hour",
        description="Search items",
        params={
            "query": {"type": "string", "required": True},
            "limit": {"type": "integer", "required": False, "max": 100},
            "type": {"type": "string", "required": False, "enum": ["a", "b"]},
        },
    )
    async def search():
        pass

    skill = generate_skill_markdown("test", "Test", "URL")

    assert "query: string, required" in skill
    assert "limit: integer, optional" in skill
    assert "max 100" in skill
    assert "one of ['a', 'b']" in skill
