#!/usr/bin/env python3
"""
Analyze Claude Code transcripts for Balance sessions.

Run via cron at end of day:
    0 22 * * * cd ~/knowledge-system && python3 scripts/balance-analysis/analyze_sessions.py
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

from transcript_parser import extract_messages_in_timewindow, build_timeline, summarize_timeline


BALANCE_URL = "https://balance.gstoehl.dev"
PROMPT_TEMPLATE = Path(__file__).parent / "prompts" / "session_analysis.md"


def api_get(endpoint: str) -> dict:
    """GET request to Balance API."""
    try:
        with urlopen(f"{BALANCE_URL}{endpoint}", timeout=10) as response:
            return json.loads(response.read().decode())
    except URLError as e:
        print(f"Error fetching {endpoint}: {e}", file=sys.stderr)
        return None


def api_post(endpoint: str, data: dict) -> dict:
    """POST request to Balance API."""
    try:
        req = Request(
            f"{BALANCE_URL}{endpoint}",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except URLError as e:
        print(f"Error posting to {endpoint}: {e}", file=sys.stderr)
        return None


def load_prompt_template() -> str:
    """Load the analysis prompt template."""
    with open(PROMPT_TEMPLATE) as f:
        return f.read()


def build_analysis_prompt(session: dict, timeline: list[dict], summary: dict) -> str:
    """Build the analysis prompt for a session."""
    template = load_prompt_template()

    # Calculate duration
    start = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(session["ended_at"].replace("Z", "+00:00"))
    duration = int((end - start).total_seconds() / 60)

    # Format timeline as compact JSON
    timeline_json = json.dumps(timeline, indent=2)

    # Fill template
    prompt = template.format(
        intention=session.get("intention") or "No intention specified",
        type=session.get("type", "unknown"),
        priority=session.get("priority_name") or "No priority",
        priority_rank=session.get("priority_rank") or "?",
        duration=duration,
        timeline_json=timeline_json
    )

    return prompt


def analyze_with_claude(prompt: str) -> dict:
    """Run analysis via Claude CLI."""
    result = subprocess.run(
        [
            "claude", "--print",
            "--output-format", "json",
            "--allowedTools", "",
            "--model", "haiku",
        ],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode != 0:
        raise Exception(f"Claude CLI failed: {result.stderr}")

    response = json.loads(result.stdout)
    if response.get("type") == "result" and response.get("subtype") == "success":
        # Parse the inner JSON from Claude's response
        return json.loads(response["result"])
    else:
        raise Exception(f"Analysis failed: {response}")


def analyze_session(session: dict) -> bool:
    """Analyze a single session and store results."""
    session_id = session["id"]
    print(f"\nAnalyzing session {session_id}: {session.get('intention', 'No intention')}")

    # Parse timestamps
    start = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00")).replace(tzinfo=None)
    end = datetime.fromisoformat(session["ended_at"].replace("Z", "+00:00")).replace(tzinfo=None)

    # Extract messages
    messages = extract_messages_in_timewindow(start, end)
    if not messages:
        print(f"  No Claude messages found in time window")
        return False

    timeline = build_timeline(messages)
    summary = summarize_timeline(timeline)

    print(f"  Found {len(timeline)} prompts across {summary['projects_touched']}")

    # Build and run analysis
    prompt = build_analysis_prompt(session, timeline, summary)

    try:
        analysis = analyze_with_claude(prompt)
    except Exception as e:
        print(f"  Analysis failed: {e}", file=sys.stderr)
        return False

    # Add metadata
    analysis["projects_used"] = summary["projects_touched"]
    analysis["prompt_count"] = summary["total_prompts"]

    # Store results
    result = api_post(f"/api/sessions/{session_id}/analysis", analysis)
    if result:
        print(f"  Stored analysis: {analysis['intention_alignment']}, severity={analysis['severity']}")
        return True
    else:
        print(f"  Failed to store analysis", file=sys.stderr)
        return False


def main():
    print(f"=== Balance Session Analysis — {datetime.now().isoformat()} ===")

    # Get unanalyzed sessions
    sessions = api_get("/api/sessions/unanalyzed")
    if sessions is None:
        print("Failed to fetch unanalyzed sessions", file=sys.stderr)
        sys.exit(1)

    if not sessions:
        print("No sessions to analyze")
        return

    print(f"Found {len(sessions)} unanalyzed sessions")

    # Analyze each session
    success = 0
    for session in sessions:
        if analyze_session(session):
            success += 1

    print(f"\n=== Complete: {success}/{len(sessions)} sessions analyzed ===")


if __name__ == "__main__":
    main()
