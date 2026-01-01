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

{{
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
}}

No suggestions. Just observations.
