"""OpenClaw skill generation from registered endpoints."""

import json

from .registry import get_all_endpoints


def generate_skill_markdown(
    name: str,
    description: str,
    base_url_env: str = "GATEWAY_URL",
) -> str:
    """
    Generate OpenClaw skill markdown from registered endpoints.

    Args:
        name: Skill name (e.g., "knowledge-gateway")
        description: Skill description
        base_url_env: Environment variable for base URL

    Returns:
        Markdown string for SKILL.md
    """
    endpoints = get_all_endpoints()

    lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
        f'metadata: {{"openclaw": {{"requires": {{"env": ["{base_url_env}"]}}}}}}',
        "---",
        "",
        f"# {name.replace('-', ' ').title()}",
        "",
        f"Base URL: ${{{base_url_env}}}",
        "",
    ]

    for ep in endpoints:
        lines.append(f"## {ep.method} {ep.path}")
        lines.append(ep.description)
        lines.append(f"Rate limit: {ep.rate_limit}")
        lines.append("")

        if ep.params:
            lines.append("**Params:**")
            for param_name, spec in ep.params.items():
                required = "required" if spec.get("required") else "optional"
                ptype = spec.get("type", "any")
                desc_parts = [f"{param_name}: {ptype}, {required}"]

                if "enum" in spec:
                    desc_parts.append(f"one of {spec['enum']}")
                if "min" in spec:
                    desc_parts.append(f"min {spec['min']}")
                if "max" in spec:
                    desc_parts.append(f"max {spec['max']}")
                if "pattern" in spec:
                    desc_parts.append(f"pattern {spec['pattern']}")

                lines.append(f"- {', '.join(desc_parts)}")
            lines.append("")

        if ep.response_example:
            lines.append("**Example response:**")
            lines.append("```json")
            lines.append(json.dumps(ep.response_example, indent=2))
            lines.append("```")
            lines.append("")

    return "\n".join(lines)
