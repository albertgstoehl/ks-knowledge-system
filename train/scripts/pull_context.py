#!/usr/bin/env python3
"""
Pull training context for plan iteration workflow.

Usage:
    python pull_context.py              # Formatted for LLM
    python pull_context.py --json       # Raw JSON
    python pull_context.py --url URL    # Custom API URL
"""

import argparse
import json
import sys

import httpx


def format_for_llm(data: dict) -> str:
    """Format context data for LLM consumption."""
    lines = []

    plan = data.get("plan")
    if plan:
        lines.append(f"## Current Plan: {plan['title']}")
        lines.append(f"Started: {plan['created_at'][:10]}")
        lines.append("")
    else:
        lines.append("## No active plan")
        lines.append("")
        return "\n".join(lines)

    summary = data.get("summary", {})
    lines.append("## Summary")
    lines.append(f"- Weeks on plan: {summary.get('weeks_on_plan', 0)}")
    lines.append(f"- Total sessions: {summary.get('total_sessions', 0)}")
    lines.append("")

    volume = summary.get("volume_by_muscle", {})
    if volume:
        lines.append("## Volume by Muscle (sets)")
        for muscle, sets in sorted(volume.items(), key=lambda item: -item[1]):
            lines.append(f"- {muscle}: {sets}")
        lines.append("")

    sessions = data.get("sessions", [])[:5]
    if sessions:
        lines.append("## Recent Sessions")
        for entry in sessions:
            date = entry["started_at"][:10]
            key = entry["template_key"]
            notes = entry.get("notes") or ""
            notes_preview = notes[:50] + "..." if len(notes) > 50 else notes
            lines.append(f"- {date} ({key}): {notes_preview}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pull training context")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()

    try:
        with httpx.Client() as client:
            resp = client.get(f"{args.url}/api/context", timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        print(f"Error fetching context: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(format_for_llm(data))


if __name__ == "__main__":
    main()
