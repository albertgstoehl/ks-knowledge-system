# Transcript Analysis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete and verify the transcript analysis system that evaluates Claude Code session effectiveness.

**Architecture:** End-of-day cron script parses Claude transcripts from `~/.claude/projects/`, correlates with Balance sessions, analyzes via Claude CLI (Haiku), and stores results for Stats page display.

**Tech Stack:** Python 3.11, Claude CLI (`claude --print`), FastAPI, SQLite, vanilla JS

**Status:** ~95% implemented. This plan covers verification, edge case handling, and cron setup.

---

## Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| Database schema | Done | `balance/src/database.py:98-122` |
| Pydantic models | Done | `balance/src/models.py:146-181` |
| GET /sessions/unanalyzed | Done | `balance/src/routers/sessions.py:641-658` |
| POST /sessions/{id}/analysis | Done | `balance/src/routers/sessions.py:661-686` |
| GET /stats/effectiveness | Done | `balance/src/routers/sessions.py:689-757` |
| Transcript parser | Done | `scripts/balance-analysis/transcript_parser.py` |
| Analysis prompt | Done | `scripts/balance-analysis/prompts/session_analysis.md` |
| Analysis script | Done | `scripts/balance-analysis/analyze_sessions.py` |
| Stats UI | Done | `balance/src/templates/_content_stats.html:8-15` |
| Intention field (hook) | Done | `scripts/claude-hooks/balance-check.py:95` |
| Intention placeholder (UI) | Done | `balance/src/templates/_content_index.html:32` |
| Cron setup | **Pending** | Server crontab |
| Edge case handling | **Pending** | `analyze_sessions.py` |

---

## Task 1: Verify Existing Components

**Purpose:** Confirm all pieces work before proceeding.

**Step 1: Verify database schema includes session_analyses table**

Run:
```bash
sqlite3 ~/knowledge-system/balance/data/balance.db ".schema session_analyses"
```

Expected: Table with columns including `id, session_id, analyzed_at, intention_alignment, one_line_summary, severity`

**Step 2: Verify transcript parser finds Claude directories**

Run:
```bash
ls -la ~/.claude/projects/
```

Expected: Directories like `-home-ags-knowledge-system/` with `.jsonl` files

**Step 3: Test transcript parser standalone**

Run:
```bash
cd ~/knowledge-system && python3 -c "
from scripts.balance_analysis.transcript_parser import find_project_dirs, decode_project_path
dirs = find_project_dirs()
print(f'Found {len(dirs)} project dirs:')
for d in dirs[:5]:
    print(f'  {d.name} -> {decode_project_path(d.name)}')
"
```

Expected: List of project directories with decoded names

---

## Task 2: Test Balance API Endpoints

**Purpose:** Verify API endpoints work correctly.

**Step 1: Test /api/sessions/unanalyzed endpoint**

Run:
```bash
curl -s https://balance.gstoehl.dev/api/sessions/unanalyzed | python3 -m json.tool
```

Expected: JSON array of sessions with `claude_used=true` and no analysis (may be empty)

**Step 2: Test /api/stats/effectiveness endpoint**

Run:
```bash
curl -s https://balance.gstoehl.dev/api/stats/effectiveness | python3 -m json.tool
```

Expected: JSON with `total_analyzed`, `alignment_breakdown`, etc.

**Step 3: Verify Stats UI loads effectiveness section**

Open: https://balance.gstoehl.dev/stats

Expected: If analyses exist, shows "Session effectiveness (today)" card. If none, section is hidden.

---

## Task 3: Add Edge Case Handling

**Purpose:** Handle edge cases from design doc (retry logic, no-data handling).

**Files:**
- Modify: `scripts/balance-analysis/analyze_sessions.py:115-155`

**Step 1: Update analyze_session function with retry and no-data handling**

```python
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
        # Store as no_data instead of silently skipping
        api_post(f"/api/sessions/{session_id}/analysis", {
            "intention_alignment": "unknown",
            "alignment_detail": "No Claude messages found in session time window",
            "scope_behavior": "unknown",
            "scope_detail": None,
            "project_switches": 0,
            "tool_appropriate_count": 0,
            "tool_questionable_count": 0,
            "tool_questionable_examples": [],
            "red_flags": [],
            "one_line_summary": "No data - possible clock skew or transcripts deleted",
            "severity": "none",
            "projects_used": [],
            "prompt_count": 0,
            "raw_response": None
        })
        return True

    timeline = build_timeline(messages)
    summary = summarize_timeline(timeline)

    print(f"  Found {len(timeline)} prompts across {summary['projects_touched']}")

    # Build and run analysis with retry
    prompt = build_analysis_prompt(session, timeline, summary)

    max_retries = 2
    for attempt in range(max_retries):
        try:
            analysis = analyze_with_claude(prompt)
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  Retry {attempt + 1}: {e}")
                continue
            print(f"  Analysis failed after {max_retries} attempts: {e}", file=sys.stderr)
            return False

    # Add metadata
    analysis["projects_used"] = summary["projects_touched"]
    analysis["prompt_count"] = summary["total_prompts"]
    analysis["raw_response"] = None  # Don't store raw for now

    # Store results
    result = api_post(f"/api/sessions/{session_id}/analysis", analysis)
    if result:
        print(f"  Stored analysis: {analysis['intention_alignment']}, severity={analysis['severity']}")
        return True
    else:
        print(f"  Failed to store analysis", file=sys.stderr)
        return False
```

**Step 2: Run analysis script to verify**

Run:
```bash
cd ~/knowledge-system && python3 scripts/balance-analysis/analyze_sessions.py
```

Expected: No errors, handles edge cases gracefully

**Step 3: Commit**

```bash
git add scripts/balance-analysis/analyze_sessions.py
git commit -m "$(cat <<'EOF'
fix(analysis): add retry logic and no-data handling

- Retry Claude CLI calls up to 2 times on failure
- Store analysis with 'unknown' status when no messages found
- Prevents silent failures for edge cases

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Set Up Cron Job

**Purpose:** Automate daily analysis at 22:00.

**Step 1: Create log directory**

Run:
```bash
mkdir -p ~/knowledge-system/logs
```

**Step 2: Add crontab entry**

Run:
```bash
crontab -e
```

Add line:
```
0 22 * * * cd ~/knowledge-system && /usr/bin/python3 scripts/balance-analysis/analyze_sessions.py >> logs/balance-analysis.log 2>&1
```

**Step 3: Verify crontab saved**

Run:
```bash
crontab -l | grep balance-analysis
```

Expected: The crontab line appears

---

## Task 5: Create Test Session for End-to-End Testing

**Purpose:** Generate a real session with Claude usage to test the full pipeline.

**Step 1: Start a test session via UI**

1. Go to https://balance.gstoehl.dev
2. Start an Expected session with intention: "Test transcript analysis system"
3. Use Claude Code during the session (this conversation counts!)

**Step 2: Complete the session**

1. Let timer complete or abandon after a few minutes
2. Fill out questionnaire

**Step 3: Verify session marked claude_used**

Run:
```bash
sqlite3 ~/knowledge-system/balance/data/balance.db \
  "SELECT id, intention, claude_used FROM sessions ORDER BY id DESC LIMIT 5;"
```

Expected: Recent session shows `claude_used = 1`

---

## Task 6: Run Analysis Script Manually

**Purpose:** Test the full analysis pipeline.

**Step 1: Run analysis script**

Run:
```bash
cd ~/knowledge-system && python3 scripts/balance-analysis/analyze_sessions.py
```

Expected output:
```
=== Balance Session Analysis — 2026-01-01T... ===
Found N unanalyzed sessions
Analyzing session X: Test transcript analysis system
  Found M prompts across ['knowledge-system']
  Stored analysis: aligned, severity=none
=== Complete: 1/1 sessions analyzed ===
```

**Step 2: Verify analysis stored**

Run:
```bash
sqlite3 ~/knowledge-system/balance/data/balance.db \
  "SELECT session_id, intention_alignment, one_line_summary FROM session_analyses ORDER BY id DESC LIMIT 3;"
```

Expected: Recent analysis with alignment verdict and summary

**Step 3: Verify Stats UI shows new analysis**

Refresh: https://balance.gstoehl.dev/stats

Expected: "Session effectiveness (today)" card shows with analysis data

---

## Task 7: Final Verification and Documentation

**Purpose:** Confirm everything works and update docs.

**Step 1: Check Stats page with real data**

Open: https://balance.gstoehl.dev/stats

Verify:
- Effectiveness section visible if analyses exist
- Shows correct alignment breakdown
- Red flags display correctly
- Quotes from recent sessions appear

**Step 2: Run analysis again to confirm idempotency**

Run:
```bash
cd ~/knowledge-system && python3 scripts/balance-analysis/analyze_sessions.py
```

Expected: "No sessions to analyze" (already analyzed sessions not re-processed)

**Step 3: Update CLAUDE.md if needed**

Verify `CLAUDE.md` already references the design doc under Balance section.

---

## Summary

| Task | Description | Status |
|------|-------------|--------|
| 1 | Verify existing components | Pending |
| 2 | Test Balance API endpoints | Pending |
| 3 | Add edge case handling | Pending |
| 4 | Set up cron job | Pending |
| 5 | Create test session | Pending |
| 6 | Run analysis script | Pending |
| 7 | Final verification | Pending |

**Implementation is ~95% complete.** Main work is verification, edge case handling, and cron setup.
