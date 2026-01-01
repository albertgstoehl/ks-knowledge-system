# Transcript Analysis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Analyze Claude Code transcripts from Balance pomodoro sessions to evaluate effectiveness and detect misalignment with stated intentions.

**Architecture:** End-of-day cron script extracts user prompts from `~/.claude/projects/` JSONL files, correlates with Balance sessions, runs analysis via `claude --print`, stores results in Balance DB.

**Tech Stack:** Python 3.11, FastAPI, SQLite, Claude CLI.

**Prerequisite:** Priority drift detection should be implemented first (provides priority context).

---

## Task 1: Extend Intention Field — Remove "3 Words" Constraint

**Files:**
- Modify: `scripts/claude-hooks/balance-check.py:95`
- Modify: `balance/src/templates/_content_index.html`

**Step 1: Update hook prompt**

In `scripts/claude-hooks/balance-check.py`, change the intention input:

```python
# Before (around line 95)
intention = input("Intention (3 words): ").strip()

# After
intention = input("Intention: ").strip()
```

**Step 2: Update timer UI placeholder**

In `balance/src/templates/_content_index.html`, find the intention input and update placeholder:

```html
<!-- Before -->
<input ... placeholder="3 words...">

<!-- After -->
<input ... placeholder="What are you working on?">
```

**Step 3: Test manually**

Run: `python3 ~/.claude/hooks/balance-check.py`
Expected: Prompts "Intention:" without word limit

**Step 4: Commit**

```bash
git add scripts/claude-hooks/balance-check.py balance/src/templates/_content_index.html
git commit -m "feat(balance): extend intention field to allow longer descriptions"
```

---

## Task 2: Database Schema — session_analyses Table

**Files:**
- Modify: `balance/src/database.py`
- Modify: `balance/tests/test_database.py`

**Step 1: Write failing test**

```python
# Add to balance/tests/test_database.py
@pytest.mark.asyncio
async def test_session_analyses_table_exists():
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='session_analyses'"
        )
        result = await cursor.fetchone()
        assert result is not None
        assert result[0] == "session_analyses"
```

**Step 2: Run test to verify it fails**

Run: `cd balance && python -m pytest tests/test_database.py::test_session_analyses_table_exists -v`
Expected: FAIL — table doesn't exist

**Step 3: Add session_analyses table to init_db**

In `balance/src/database.py`, add after other table creations:

```python
await db.execute("""
    CREATE TABLE IF NOT EXISTS session_analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL REFERENCES sessions(id),
        analyzed_at TEXT NOT NULL,

        -- What happened
        projects_used TEXT,
        prompt_count INTEGER,

        -- Analysis results
        intention_alignment TEXT,
        alignment_detail TEXT,
        scope_behavior TEXT,
        scope_detail TEXT,
        project_switches INTEGER,
        tool_appropriate_count INTEGER,
        tool_questionable_count INTEGER,
        tool_questionable_examples TEXT,
        red_flags TEXT,
        one_line_summary TEXT,
        severity TEXT,

        -- Raw reference
        raw_response TEXT
    )
""")
```

**Step 4: Run test to verify it passes**

Run: `cd balance && python -m pytest tests/test_database.py::test_session_analyses_table_exists -v`
Expected: PASS

**Step 5: Commit**

```bash
git add balance/src/database.py balance/tests/test_database.py
git commit -m "feat(balance): add session_analyses table schema"
```

---

## Task 3: Pydantic Models for Analysis

**Files:**
- Modify: `balance/src/models.py`

**Step 1: Add Analysis models**

```python
# Add to balance/src/models.py

class SessionAnalysis(BaseModel):
    id: int
    session_id: int
    analyzed_at: str
    projects_used: list[str]
    prompt_count: int
    intention_alignment: str  # aligned|pivoted|drifted
    alignment_detail: str
    scope_behavior: str  # focused|expanded|rabbit_hole
    scope_detail: Optional[str] = None
    project_switches: int
    tool_appropriate_count: int
    tool_questionable_count: int
    tool_questionable_examples: list[str]
    red_flags: list[str]
    one_line_summary: str
    severity: str  # none|minor|notable|significant

class SessionAnalysisCreate(BaseModel):
    intention_alignment: str
    alignment_detail: str
    scope_behavior: str
    scope_detail: Optional[str] = None
    project_switches: int
    tool_appropriate_count: int
    tool_questionable_count: int
    tool_questionable_examples: list[str]
    red_flags: list[str]
    one_line_summary: str
    severity: str
    projects_used: list[str]
    prompt_count: int
    raw_response: Optional[str] = None
```

**Step 2: Verify imports work**

Run: `cd balance && python -c "from src.models import SessionAnalysis, SessionAnalysisCreate; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add balance/src/models.py
git commit -m "feat(balance): add SessionAnalysis pydantic models"
```

---

## Task 4: API Endpoint — Get Unanalyzed Sessions

**Files:**
- Modify: `balance/src/routers/sessions.py`
- Modify: `balance/tests/test_sessions.py`

**Step 1: Write failing test**

```python
# Add to balance/tests/test_sessions.py
@pytest.mark.asyncio
async def test_get_unanalyzed_sessions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/sessions/unanalyzed")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
```

**Step 2: Run test to verify it fails**

Run: `cd balance && python -m pytest tests/test_sessions.py::test_get_unanalyzed_sessions -v`
Expected: FAIL — 404 Not Found

**Step 3: Add endpoint**

```python
# Add to balance/src/routers/sessions.py
@router.get("/sessions/unanalyzed")
async def get_unanalyzed_sessions():
    """Get sessions with claude_used=true that haven't been analyzed."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT s.id, s.type, s.intention, s.priority_id,
                   s.started_at, s.ended_at,
                   p.name as priority_name, p.rank as priority_rank
            FROM sessions s
            LEFT JOIN priorities p ON s.priority_id = p.id
            LEFT JOIN session_analyses sa ON s.id = sa.session_id
            WHERE s.claude_used = 1
              AND s.ended_at IS NOT NULL
              AND sa.id IS NULL
            ORDER BY s.started_at DESC
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
```

**Step 4: Run test to verify it passes**

Run: `cd balance && python -m pytest tests/test_sessions.py::test_get_unanalyzed_sessions -v`
Expected: PASS

**Step 5: Commit**

```bash
git add balance/src/routers/sessions.py balance/tests/test_sessions.py
git commit -m "feat(balance): add GET /api/sessions/unanalyzed endpoint"
```

---

## Task 5: API Endpoint — Store Analysis Results

**Files:**
- Modify: `balance/src/routers/sessions.py`
- Modify: `balance/tests/test_sessions.py`

**Step 1: Write failing test**

```python
# Add to balance/tests/test_sessions.py
@pytest.mark.asyncio
async def test_store_session_analysis():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a session first
        await client.post("/api/sessions/start", json={
            "type": "expected",
            "intention": "Test intention"
        })
        # Mark it as using claude and end it
        await client.post("/api/session/mark-claude-used", json={})
        await client.post("/api/sessions/end", json={"did_the_thing": True})

        # Get the session ID
        sessions = await client.get("/api/sessions/unanalyzed")
        session_id = sessions.json()[0]["id"]

        # Store analysis
        response = await client.post(f"/api/sessions/{session_id}/analysis", json={
            "intention_alignment": "aligned",
            "alignment_detail": "Work matched intention",
            "scope_behavior": "focused",
            "scope_detail": None,
            "project_switches": 0,
            "tool_appropriate_count": 5,
            "tool_questionable_count": 1,
            "tool_questionable_examples": ["prompt 3: simple file read"],
            "red_flags": [],
            "one_line_summary": "Focused session on intended task",
            "severity": "none",
            "projects_used": ["knowledge-system"],
            "prompt_count": 6
        })
        assert response.status_code == 200
        assert response.json()["id"] is not None
```

**Step 2: Run test to verify it fails**

Run: `cd balance && python -m pytest tests/test_sessions.py::test_store_session_analysis -v`
Expected: FAIL — 404 or 405

**Step 3: Add endpoint**

```python
# Add to balance/src/routers/sessions.py
from ..models import SessionAnalysisCreate
import json

@router.post("/sessions/{session_id}/analysis")
async def store_session_analysis(session_id: int, data: SessionAnalysisCreate):
    """Store analysis results for a session."""
    async with get_db() as db:
        now = datetime.now().isoformat()
        cursor = await db.execute(
            """INSERT INTO session_analyses (
                session_id, analyzed_at, projects_used, prompt_count,
                intention_alignment, alignment_detail, scope_behavior,
                scope_detail, project_switches, tool_appropriate_count,
                tool_questionable_count, tool_questionable_examples,
                red_flags, one_line_summary, severity, raw_response
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id, now,
                json.dumps(data.projects_used), data.prompt_count,
                data.intention_alignment, data.alignment_detail,
                data.scope_behavior, data.scope_detail, data.project_switches,
                data.tool_appropriate_count, data.tool_questionable_count,
                json.dumps(data.tool_questionable_examples),
                json.dumps(data.red_flags), data.one_line_summary,
                data.severity, data.raw_response
            )
        )
        await db.commit()
        return {"id": cursor.lastrowid, "session_id": session_id}
```

**Step 4: Run test to verify it passes**

Run: `cd balance && python -m pytest tests/test_sessions.py::test_store_session_analysis -v`
Expected: PASS

**Step 5: Commit**

```bash
git add balance/src/routers/sessions.py balance/tests/test_sessions.py
git commit -m "feat(balance): add POST /api/sessions/{id}/analysis endpoint"
```

---

## Task 6: API Endpoint — Effectiveness Stats

**Files:**
- Modify: `balance/src/routers/sessions.py`
- Modify: `balance/tests/test_sessions.py`

**Step 1: Write failing test**

```python
# Add to balance/tests/test_sessions.py
@pytest.mark.asyncio
async def test_get_effectiveness_stats():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/stats/effectiveness")
        assert response.status_code == 200
        data = response.json()
        assert "total_analyzed" in data
        assert "alignment_breakdown" in data
```

**Step 2: Run test to verify it fails**

Run: `cd balance && python -m pytest tests/test_sessions.py::test_get_effectiveness_stats -v`
Expected: FAIL — 404

**Step 3: Add endpoint**

```python
# Add to balance/src/routers/sessions.py
@router.get("/stats/effectiveness")
async def get_effectiveness_stats():
    """Get aggregated effectiveness stats."""
    async with get_db() as db:
        # Get today's analyses
        today_start = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        cursor = await db.execute("""
            SELECT intention_alignment, scope_behavior, red_flags,
                   tool_questionable_count, one_line_summary, session_id
            FROM session_analyses
            WHERE analyzed_at >= ?
            ORDER BY analyzed_at DESC
        """, (today_start,))
        rows = await cursor.fetchall()

        if not rows:
            return {
                "total_analyzed": 0,
                "alignment_breakdown": {},
                "scope_breakdown": {},
                "avg_questionable_prompts": 0,
                "common_red_flags": [],
                "recent_summaries": []
            }

        # Count alignments
        alignment_counts = {}
        scope_counts = {}
        total_questionable = 0
        all_flags = []
        summaries = []

        for row in rows:
            alignment = row[0]
            scope = row[1]
            flags = json.loads(row[2]) if row[2] else []
            questionable = row[3] or 0
            summary = row[4]
            session_id = row[5]

            alignment_counts[alignment] = alignment_counts.get(alignment, 0) + 1
            scope_counts[scope] = scope_counts.get(scope, 0) + 1
            total_questionable += questionable
            all_flags.extend(flags)
            if summary:
                summaries.append({"session_id": session_id, "summary": summary})

        # Count flag occurrences
        flag_counts = {}
        for flag in all_flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1

        common_flags = sorted(
            [{"flag": k, "count": v} for k, v in flag_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:5]

        return {
            "total_analyzed": len(rows),
            "alignment_breakdown": alignment_counts,
            "scope_breakdown": scope_counts,
            "avg_questionable_prompts": round(total_questionable / len(rows), 1),
            "common_red_flags": common_flags,
            "recent_summaries": summaries[:3]
        }
```

**Step 4: Run test to verify it passes**

Run: `cd balance && python -m pytest tests/test_sessions.py::test_get_effectiveness_stats -v`
Expected: PASS

**Step 5: Commit**

```bash
git add balance/src/routers/sessions.py balance/tests/test_sessions.py
git commit -m "feat(balance): add GET /api/stats/effectiveness endpoint"
```

---

## Task 7: Transcript Parser Script

**Files:**
- Create: `scripts/balance-analysis/transcript_parser.py`

**Step 1: Create the parser module**

```python
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
                        # User message
                        content = msg.get("message", {}).get("content", "")
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
```

**Step 2: Create directory and test**

```bash
mkdir -p scripts/balance-analysis
```

Run: `python3 scripts/balance-analysis/transcript_parser.py`
Expected: Shows recent prompts from your Claude usage

**Step 3: Commit**

```bash
git add scripts/balance-analysis/transcript_parser.py
git commit -m "feat(analysis): add transcript parser for Claude JSONL files"
```

---

## Task 8: Analysis Prompt Template

**Files:**
- Create: `scripts/balance-analysis/prompts/session_analysis.md`

**Step 1: Create prompt template**

```markdown
# Session Effectiveness Analysis

You are analyzing a pomodoro work session for alignment and effectiveness.
Return ONLY valid JSON matching the schema below. No commentary, no markdown.

## Session Context

- **Stated intention:** "{intention}"
- **Type:** {type}
- **Priority:** "{priority}" (#{priority_rank})
- **Duration:** {duration} minutes

## Timeline of Claude Usage

{timeline_json}

## Analysis Dimensions

### 1. Intention Alignment
Did the work match what was declared?
- `aligned` — Prompts match intention throughout
- `pivoted` — Conscious shift to different goal (acceptable)
- `drifted` — Gradual slide away from intention (problematic)

### 2. Scope Behavior
- `focused` — Stayed on task
- `expanded` — "While I'm here..." additions
- `rabbit_hole` — Exploratory tangent > 30% of prompts

### 3. Tool Appropriateness
Flag prompts that were likely faster without Claude:
- Single file reads/edits user has done before
- Simple git commands
- Lookups that could be a quick grep

### 4. Project Coherence
- Single project = focused
- Multiple projects = context switching (note if intentional vs drift)

## Red Flags to Detect

| Pattern | Indicator |
|---------|-----------|
| just_one_more_thing | Prompt starts with "also", "while we're here", "quickly" |
| scope_creep | Early prompts narrow, late prompts broad |
| yak_shaving | Refactoring/cleanup before actual task |
| avoidance | Working on lower priority when intention was higher |
| rubber_ducking | Asking Claude to confirm things user likely knows |

## Output Schema

Return exactly this JSON structure:

{
  "intention_alignment": "aligned|pivoted|drifted",
  "alignment_detail": "one sentence explanation",
  "scope_behavior": "focused|expanded|rabbit_hole",
  "scope_detail": "what expanded, if applicable, else null",
  "project_switches": 0,
  "project_switch_note": "intentional or drift, if switches > 0, else null",
  "tool_appropriate_count": 0,
  "tool_questionable_count": 0,
  "tool_questionable_examples": ["prompt N: reason"],
  "red_flags": ["flag_name"],
  "one_line_summary": "what actually happened in one sentence",
  "severity": "none|minor|notable|significant"
}

No suggestions. Just observations.
```

**Step 2: Create directory and commit**

```bash
mkdir -p scripts/balance-analysis/prompts
git add scripts/balance-analysis/prompts/session_analysis.md
git commit -m "feat(analysis): add session analysis prompt template"
```

---

## Task 9: Main Analysis Script

**Files:**
- Create: `scripts/balance-analysis/analyze_sessions.py`

**Step 1: Create the main script**

```python
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
            "--tools", "",
            "--model", "haiku",
            "--no-session-persistence"
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
```

**Step 2: Test the script**

Run: `python3 scripts/balance-analysis/analyze_sessions.py`
Expected: Shows "No sessions to analyze" or attempts to analyze any pending sessions

**Step 3: Commit**

```bash
git add scripts/balance-analysis/analyze_sessions.py
git commit -m "feat(analysis): add main session analysis script"
```

---

## Task 10: Stats UI — Effectiveness Section

**Files:**
- Modify: `balance/src/templates/_content_stats.html`

**Step 1: Add effectiveness section**

Add after the drift alert section:

```html
<div id="effectiveness-section" style="display: none;">
  <div class="stats-card">
    <div class="stats-card__header">Session effectiveness (today)</div>
    <div class="stats-card__body">
      <div id="effectiveness-summary"></div>
      <div id="effectiveness-flags" class="mt-md"></div>
      <div id="effectiveness-quotes" class="mt-md"></div>
    </div>
  </div>
</div>
```

**Step 2: Add JavaScript to load effectiveness**

Add to the Stats object in the inline script:

```javascript
async loadEffectiveness() {
  try {
    const data = await fetch('/api/stats/effectiveness').then(r => r.json());
    const section = document.getElementById('effectiveness-section');

    if (data.total_analyzed === 0) {
      section.style.display = 'none';
      return;
    }

    section.style.display = 'block';

    // Summary
    const summary = document.getElementById('effectiveness-summary');
    const aligned = data.alignment_breakdown.aligned || 0;
    const drifted = data.alignment_breakdown.drifted || 0;
    const pivoted = data.alignment_breakdown.pivoted || 0;

    summary.innerHTML = `
      <div class="text-lg">${data.total_analyzed} sessions analyzed</div>
      <div class="mt-sm">
        <span class="badge badge--success">${aligned} aligned</span>
        <span class="badge badge--warning">${pivoted} pivoted</span>
        <span class="badge badge--error">${drifted} drifted</span>
      </div>
    `;

    // Red flags
    const flags = document.getElementById('effectiveness-flags');
    if (data.common_red_flags.length > 0) {
      flags.innerHTML = `
        <div class="text-muted text-sm">Red flags:</div>
        <div class="mt-xs">
          ${data.common_red_flags.map(f =>
            `<span class="tag">${f.flag} (${f.count})</span>`
          ).join(' ')}
        </div>
      `;
    } else {
      flags.innerHTML = '';
    }

    // Quotes
    const quotes = document.getElementById('effectiveness-quotes');
    if (data.recent_summaries.length > 0) {
      quotes.innerHTML = data.recent_summaries.map(s => `
        <div class="quote mt-sm">
          <div class="quote__text">"${s.summary}"</div>
          <div class="quote__source">— Session #${s.session_id}</div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load effectiveness:', err);
  }
}
```

**Step 3: Call in init**

```javascript
init() {
  this.bindEvents();
  this.loadStats();
  this.loadNorthStar();
  this.loadDrift();
  this.loadEffectiveness();  // Add this
}
```

**Step 4: Add styles (inline or extend shared)**

```html
<style>
.badge { display: inline-block; padding: 0.25rem 0.5rem; font-size: var(--font-size-xs); }
.badge--success { background: var(--color-success-bg); }
.badge--warning { background: var(--color-warning-bg); }
.badge--error { background: var(--color-error-bg); }
.tag { display: inline-block; padding: 0.25rem 0.5rem; border: 1px solid var(--color-border); font-size: var(--font-size-xs); margin-right: 0.25rem; }
.quote { padding-left: 1rem; border-left: 2px solid var(--color-border); }
.quote__text { font-style: italic; }
.quote__source { font-size: var(--font-size-xs); color: var(--color-muted); margin-top: 0.25rem; }
</style>
```

**Step 5: Manual test**

Run: `cd balance && python -m uvicorn src.main:app --reload`
Visit: http://localhost:8005/stats
Expected: Effectiveness section appears if analyses exist

**Step 6: Commit**

```bash
git add balance/src/templates/_content_stats.html
git commit -m "feat(balance): add effectiveness section to stats UI"
```

---

## Task 11: Cron Setup

**Files:**
- Document in: `k8s/OPERATIONS.md`

**Step 1: Add cron entry on server**

SSH into server and add cron:

```bash
crontab -e
```

Add:
```
# Balance session analysis - runs at 22:00 daily
0 22 * * * cd /home/ags/knowledge-system && /usr/bin/python3 scripts/balance-analysis/analyze_sessions.py >> /var/log/balance-analysis.log 2>&1
```

**Step 2: Create log file with permissions**

```bash
sudo touch /var/log/balance-analysis.log
sudo chown ags:ags /var/log/balance-analysis.log
```

**Step 3: Document in OPERATIONS.md**

Add section to `k8s/OPERATIONS.md`:

```markdown
## Cron Jobs

### Balance Session Analysis

Runs daily at 22:00 to analyze Claude Code usage during Balance sessions.

**Location:** Server crontab
**Script:** `scripts/balance-analysis/analyze_sessions.py`
**Log:** `/var/log/balance-analysis.log`

**Manual run:**
```bash
cd ~/knowledge-system && python3 scripts/balance-analysis/analyze_sessions.py
```

**Check logs:**
```bash
tail -f /var/log/balance-analysis.log
```
```

**Step 4: Commit docs**

```bash
git add k8s/OPERATIONS.md
git commit -m "docs: add balance analysis cron job documentation"
```

---

## Task 12: End-to-End Test

**No files to modify — integration test**

**Step 1: Start a Balance session with Claude**

1. Start Balance session with intention: "Test the transcript analysis feature"
2. Use Claude Code for a few prompts
3. End the session

**Step 2: Verify session is marked for analysis**

```bash
curl https://balance.gstoehl.dev/api/sessions/unanalyzed
```

Expected: Session appears in list

**Step 3: Run analysis manually**

```bash
cd ~/knowledge-system && python3 scripts/balance-analysis/analyze_sessions.py
```

Expected: Session gets analyzed, results stored

**Step 4: Verify in Stats page**

Visit: https://balance.gstoehl.dev/stats
Expected: Effectiveness section shows the analysis

**Step 5: Commit any fixes discovered**

```bash
git add -A
git commit -m "fix(analysis): fixes from end-to-end testing"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Extend intention field |
| 2 | Database schema |
| 3 | Pydantic models |
| 4 | GET /sessions/unanalyzed |
| 5 | POST /sessions/{id}/analysis |
| 6 | GET /stats/effectiveness |
| 7 | Transcript parser script |
| 8 | Analysis prompt template |
| 9 | Main analysis script |
| 10 | Stats UI effectiveness section |
| 11 | Cron setup |
| 12 | End-to-end test |

**Dependencies:**
- Task 1-3 can run in parallel
- Tasks 4-6 depend on Tasks 2-3
- Tasks 7-9 can run in parallel with API work
- Task 10 depends on Task 6
- Task 11-12 are final integration steps
