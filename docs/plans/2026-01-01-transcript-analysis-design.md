# Transcript Analysis — Design

Analyze Claude Code usage during Balance pomodoro sessions to evaluate effectiveness and detect misalignment between stated intentions and actual work.

## Problem

"I have hooks and priority tracking, but I don't know if I'm using Claude effectively. Am I asking Claude for things I could do faster manually? Am I drifting from my stated intention mid-session? Is Claude enabling rabbit holes?"

Balance tracks sessions and priorities. Claude transcripts exist. But there's no connection between "what I said I'd do" and "what I actually asked Claude for."

## Solution

End-of-day analysis that:
1. Collects Claude transcripts from the day's `claude_used=true` sessions
2. Correlates them with Balance session intentions and priorities
3. Analyzes alignment, scope creep, and tool appropriateness via Claude
4. Stores results for display in Stats page

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Trigger timing | End-of-day cron (22:00) | Batch analysis, reflection mindset, not mid-work interruption |
| Data extracted | User prompts + metadata only | Full transcripts too large (500k+ tokens), prompts sufficient for pattern detection |
| Analysis model | Haiku via `claude --print` | Uses Max subscription, fast/cheap for pattern matching |
| Multi-project | Yes, scan all projects | Single pomodoro may span multiple projects |
| Storage | Balance DB `session_analyses` table | Integrated with existing stats, queryable |
| Surfacing | Stats page | Alongside priority drift detection |

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     End-of-Day Cron (22:00)                      │
│                                                                   │
│  scripts/balance-analysis/analyze_sessions.py                    │
│                                                                   │
│  1. GET /api/sessions/unanalyzed from Balance                    │
│  2. For each session:                                            │
│     a. Parse ~/.claude/projects/*/*.jsonl                        │
│     b. Filter messages by session timestamps                     │
│     c. Extract user prompts + tool metadata                      │
│     d. Build analysis prompt                                     │
│     e. Call: claude --print --model haiku                        │
│     f. POST /api/sessions/{id}/analysis                          │
└─────────────────────────────────────────────────────────────────┘
```

## Transcript Storage

Claude Code stores conversations in `~/.claude/projects/` with path-encoded directories:

```
~/.claude/projects/
├── -home-ags-knowledge-system/
│   ├── {session-uuid}.jsonl
│   └── {session-uuid}.jsonl
├── -home-ags-law-thesis-zhaw/
│   └── {session-uuid}.jsonl
└── ...
```

**JSONL format** (one JSON object per line):
```json
{
  "timestamp": "2026-01-01T15:00:00.000Z",
  "type": "user",
  "message": {"role": "user", "content": "..."},
  "cwd": "/home/ags/knowledge-system",
  "sessionId": "uuid"
}
```

Messages are written **instantly** — no batching at session end.

## Extraction Format

For each Balance session, extract:

```json
{
  "session": {
    "id": 42,
    "intention": "Fix the JWT validation bug in auth middleware",
    "type": "expected",
    "priority": "Work catchup",
    "priority_rank": 2,
    "started_at": "2026-01-01T15:00:00Z",
    "ended_at": "2026-01-01T15:25:00Z"
  },
  "timeline": [
    {
      "timestamp": "2026-01-01T15:00:30Z",
      "project": "knowledge-system",
      "prompt": "Can you help me debug the auth middleware?"
    },
    {
      "timestamp": "2026-01-01T15:03:00Z",
      "project": "knowledge-system",
      "prompt": "Actually, let's refactor the config system first",
      "tools_used": ["Read", "Glob", "Edit"]
    },
    {
      "timestamp": "2026-01-01T15:12:00Z",
      "project": "law-thesis-zhaw",
      "prompt": "Quick question about citation formats"
    }
  ],
  "summary": {
    "total_prompts": 12,
    "projects_touched": ["knowledge-system", "law-thesis-zhaw"],
    "tools_invoked": {"Read": 8, "Edit": 4, "Bash": 2}
  }
}
```

Typical size: 2-5k tokens per session. Easily fits in context.

## Analysis Prompt

```markdown
# Session Effectiveness Analysis

You are analyzing a pomodoro work session for alignment and effectiveness.
Return ONLY valid JSON matching the schema below. No commentary.

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
| "Just one more thing" | Prompt starts with "also", "while we're here", "quickly" |
| Scope creep | Early prompts narrow, late prompts broad |
| Yak shaving | Refactoring/cleanup before actual task |
| Avoidance | Working on lower priority when intention was higher |
| Rubber ducking | Asking Claude to confirm things you know |

## Output Schema

{
  "intention_alignment": "aligned|pivoted|drifted",
  "alignment_detail": "string — one sentence explanation",
  "scope_behavior": "focused|expanded|rabbit_hole",
  "scope_detail": "string — what expanded if applicable",
  "project_switches": number,
  "project_switch_note": "string — intentional or drift",
  "tool_appropriateness": {
    "appropriate_count": number,
    "questionable_count": number,
    "questionable_examples": ["string — prompt N: reason"]
  },
  "red_flags": ["string — flag names detected"],
  "one_line_summary": "string — what actually happened",
  "severity": "none|minor|notable|significant"
}

No suggestions. Just observations.
```

## Database Schema

### New Table: session_analyses

```sql
CREATE TABLE session_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    analyzed_at TEXT NOT NULL,

    -- What happened
    projects_used TEXT,              -- JSON array
    prompt_count INTEGER,

    -- Analysis results
    intention_alignment TEXT,        -- aligned|pivoted|drifted
    alignment_detail TEXT,
    scope_behavior TEXT,             -- focused|expanded|rabbit_hole
    scope_detail TEXT,
    project_switches INTEGER,
    tool_appropriate_count INTEGER,
    tool_questionable_count INTEGER,
    tool_questionable_examples TEXT, -- JSON array
    red_flags TEXT,                  -- JSON array
    one_line_summary TEXT,
    severity TEXT,                   -- none|minor|notable|significant

    -- Raw reference
    raw_response TEXT                -- Full Claude response for debugging
);
```

### Sessions Table Change

```sql
-- Already exists from claude-balance-lock design
ALTER TABLE sessions ADD COLUMN claude_used BOOLEAN DEFAULT FALSE;
```

## API Endpoints

### Balance API Additions

```
GET  /api/sessions/unanalyzed
     Returns sessions where claude_used=true AND no analysis exists
     Response: [{id, intention, type, priority_id, started_at, ended_at}, ...]

POST /api/sessions/{id}/analysis
     Stores analysis results
     Body: {intention_alignment, scope_behavior, ...}

GET  /api/stats/effectiveness
     Aggregated effectiveness stats for Stats page
     Response: {
       total_analyzed: 42,
       alignment_breakdown: {aligned: 30, pivoted: 8, drifted: 4},
       avg_questionable_prompts: 1.2,
       common_red_flags: [{flag: "scope_creep", count: 12}, ...]
     }
```

## CLI Invocation

```python
import subprocess
import json

def analyze_with_claude(prompt: str) -> dict:
    """Call Claude via CLI using Max subscription."""
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
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"Claude CLI failed: {result.stderr}")

    response = json.loads(result.stdout)
    if response.get("type") == "result" and response.get("subtype") == "success":
        return json.loads(response["result"])
    else:
        raise Exception(f"Analysis failed: {response}")
```

## File Structure

```
scripts/
├── claude-hooks/
│   └── balance-check.py           # Existing hook
└── balance-analysis/
    ├── analyze_sessions.py        # Main cron script
    ├── transcript_parser.py       # JSONL extraction utilities
    └── prompts/
        └── session_analysis.md    # Prompt template

balance/
├── src/
│   ├── routers/
│   │   └── sessions.py            # Add unanalyzed + analysis endpoints
│   └── database.py                # Add session_analyses table
└── tests/
    └── test_analysis.py           # New tests
```

## Cron Setup

```bash
# Run at 22:00 daily
0 22 * * * cd ~/knowledge-system && python3 scripts/balance-analysis/analyze_sessions.py >> /var/log/balance-analysis.log 2>&1
```

## UI Changes

### Stats Page — Effectiveness Section

Add below drift alert:

```
┌─────────────────────────────────────────┐
│ SESSION EFFECTIVENESS (today)           │
│                                         │
│ 4 sessions analyzed                     │
│                                         │
│ Alignment:  ████████░░ 3 aligned        │
│             ░░░░░░░░░░ 1 drifted        │
│                                         │
│ Red flags:  scope_creep (2)             │
│             yak_shaving (1)             │
│                                         │
│ ─────────────────────────────────────── │
│ "Started on auth bug, ended             │
│  refactoring config system"             │
│                      — Session #42      │
└─────────────────────────────────────────┘
```

Only shows if analyses exist for today. Clicking expands to show per-session details.

## Prerequisite Changes

### Extend Intention Field

Remove "3 words" constraint to provide richer context for analysis.

**balance-check.py hook:**
```python
# Before
intention = input("Intention (3 words): ").strip()

# After
intention = input("Intention: ").strip()
```

**Timer UI placeholder:**
```html
<!-- Before -->
<input placeholder="3 words...">

<!-- After -->
<input placeholder="What are you working on?">
```

## Edge Cases

| Case | Behavior |
|------|----------|
| No Claude usage in session | Skip — nothing to analyze |
| Transcripts deleted | Mark as `analysis_failed`, log reason |
| Session spans midnight | Use session timestamps, not calendar day |
| Very short session (<5 min) | Analyze anyway — even brief sessions can drift |
| No prompts found in timewindow | Mark as `no_data`, possible clock skew |
| Claude CLI fails | Retry once, then mark `analysis_failed` |

## Privacy Considerations

- Transcripts stay local (only parsed, not uploaded anywhere new)
- Analysis runs locally via Claude CLI
- Results stored in local Balance DB
- No external services involved

## Implementation Order

1. Extend intention field (hook + UI)
2. Database schema (session_analyses table)
3. Balance API endpoints (unanalyzed, analysis, effectiveness)
4. Transcript parser script
5. Analysis script with Claude CLI integration
6. Cron setup
7. Stats UI — effectiveness section
8. Manual testing with real sessions

## Non-Goals

- Real-time analysis (would interrupt flow)
- Notifications when drifting (just observations)
- Suggestions for improvement (user decides what to do)
- Historical re-analysis (only analyze going forward)
- Cross-day pattern detection (keep it simple for v1)
