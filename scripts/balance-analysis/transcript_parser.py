#!/usr/bin/env python3
"""Parse Claude Code JSONL transcripts and extract user prompts."""

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator


CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


def find_project_dirs() -> list[Path]:
    """Find all project directories in Claude storage."""
    if not CLAUDE_PROJECTS_DIR.exists():
        return []
    return [d for d in CLAUDE_PROJECTS_DIR.iterdir() if d.is_dir()]


def decode_project_path(encoded: str) -> str:
    """Decode project path from directory name.

    e.g., '-home-ags-knowledge-system' -> 'knowledge-system'
    """
    # Remove leading dash and split
    parts = encoded.lstrip("-").split("-")
    # Return just the last part (project name)
    return parts[-1] if parts else encoded


def parse_jsonl_file(filepath: Path) -> Iterator[dict]:
    """Parse a JSONL file and yield message objects."""
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
    except Exception:
        return


def extract_messages_in_timewindow(
    start_ts: datetime,
    end_ts: datetime
) -> list[dict]:
    """Extract all user messages across all projects within a time window."""
    messages = []

    for project_dir in find_project_dirs():
        project_name = decode_project_path(project_dir.name)

        for jsonl_file in project_dir.glob("*.jsonl"):
            for msg in parse_jsonl_file(jsonl_file):
                # Check timestamp
                ts_str = msg.get("timestamp")
                if not ts_str:
                    continue

                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    # Make naive for comparison if needed
                    ts = ts.replace(tzinfo=None)
                except ValueError:
                    continue

                # Filter by time window
                if start_ts <= ts <= end_ts:
                    msg_type = msg.get("type")

                    if msg_type == "user":
                        # User message - extract text from content
                        raw_content = msg.get("message", {}).get("content", "")

                        # Handle both string and list content formats
                        if isinstance(raw_content, str):
                            content = raw_content
                        elif isinstance(raw_content, list):
                            # Extract text from content blocks
                            text_parts = []
                            for item in raw_content:
                                if isinstance(item, dict):
                                    if item.get("type") == "text":
                                        text_parts.append(item.get("text", ""))
                                    # Skip tool_result blocks
                            content = " ".join(text_parts)
                        else:
                            content = str(raw_content)

                        # Skip system/hook messages
                        if content.startswith("Caveat:") or not content.strip():
                            continue

                        messages.append({
                            "timestamp": ts_str,
                            "project": project_name,
                            "type": "user",
                            "prompt": content[:500],  # Truncate long prompts
                        })

                    elif msg_type == "assistant":
                        # Extract tools used from assistant message
                        content = msg.get("message", {}).get("content", [])
                        tools = []
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "tool_use":
                                    tools.append(block.get("name"))
                        if tools:
                            messages.append({
                                "timestamp": ts_str,
                                "project": project_name,
                                "type": "tools",
                                "tools_used": tools,
                            })

    # Sort by timestamp
    messages.sort(key=lambda x: x["timestamp"])
    return messages


def build_timeline(messages: list[dict]) -> list[dict]:
    """Build a timeline combining user prompts with their tool usage."""
    timeline = []
    current_prompt = None

    for msg in messages:
        if msg["type"] == "user":
            # Save previous prompt if exists
            if current_prompt:
                timeline.append(current_prompt)

            current_prompt = {
                "timestamp": msg["timestamp"],
                "project": msg["project"],
                "prompt": msg["prompt"],
                "tools_used": []
            }
        elif msg["type"] == "tools" and current_prompt:
            # Add tools to current prompt
            current_prompt["tools_used"].extend(msg["tools_used"])

    # Don't forget the last one
    if current_prompt:
        timeline.append(current_prompt)

    return timeline


def summarize_timeline(timeline: list[dict]) -> dict:
    """Create summary statistics from timeline."""
    projects = set()
    tools = {}

    for entry in timeline:
        projects.add(entry["project"])
        for tool in entry.get("tools_used", []):
            tools[tool] = tools.get(tool, 0) + 1

    return {
        "total_prompts": len(timeline),
        "projects_touched": list(projects),
        "tools_invoked": tools
    }


if __name__ == "__main__":
    # Test with last hour
    from datetime import timedelta

    end = datetime.now()
    start = end - timedelta(hours=1)

    print(f"Extracting messages from {start} to {end}")
    messages = extract_messages_in_timewindow(start, end)
    timeline = build_timeline(messages)
    summary = summarize_timeline(timeline)

    print(f"\nFound {len(timeline)} prompts")
    print(f"Projects: {summary['projects_touched']}")
    print(f"Tools: {summary['tools_invoked']}")

    if timeline:
        print("\nFirst 3 prompts:")
        for entry in timeline[:3]:
            print(f"  [{entry['project']}] {entry['prompt'][:80]}...")
