# Template-Aware Workouts

**Date:** 2026-01-18
**Status:** Design complete

## Problem

The training plan is markdown - human-readable but the app can't extract which templates exist or which exercises belong to each. "Start Workout" can't offer template choices.

## Solution

Add YAML frontmatter to plans defining templates and their exercises. Parse on API side, use in UI for guided workout logging.

## Plan Format

```yaml
---
templates:
  Push:
    - Barbell Bench Press
    - Incline Dumbbell Press
    - Cable Flyes
    - Lateral Raises
    - Tricep Pushdowns
  Pull:
    - Barbell Rows
    - Lat Pulldowns
    - Face Pulls
    - Dumbbell Rows
    - Bicep Curls
  Upper Mix + Legs:
    - Overhead Press
    - Chest-supported Rows
    - Pec Deck
    - Barbell Squats
    - Romanian Deadlifts
---
# Upper-Body Hypertrophy + Running Maintenance
...rest of markdown...
```

Exercise names only - no sets/reps/RIR in frontmatter (that stays in markdown tables for human reading).

## API Changes

`GET /api/plan/current` response adds:
- `templates`: dict of template_key → list of exercise names
- `markdown`: content AFTER frontmatter (stripped for display)

No new endpoints needed.

## Start Workout Flow

1. User taps "Start Workout" button
2. Modal opens listing templates from `plan.templates`
3. User taps template (e.g., "Push")
4. `POST /api/sessions/start` with `template_key: "Push"`
5. Redirects to active workout

If no plan or no templates defined, falls back to free text input (current behavior).

## Active Workout Flow

When session starts with a template:

1. Fetch template exercises from plan
2. For each exercise, get last set data from history
3. Display as collapsed cards with last weight preview:

```
▶ Barbell Bench Press   55kg x 6
▶ Incline Dumbbell Press 17.5kg x 8
▶ Cable Flyes           5kg x 12
▶ Lateral Raises        -
▶ Tricep Pushdowns      20kg x 12
```

4. Tap to expand → shows input fields pre-filled with last weight/reps
5. Log sets (existing behavior)

**Key decisions:**
- Only template exercises shown (not all history)
- No free text input to add exercises (YAGNI)
- No substitute button (YAGNI)
- Skipped exercises stay in list un-logged
- Use session notes for "machine was taken" situations

## Files to Modify

| File | Change |
|------|--------|
| `train/plan/workflow.md` | Document frontmatter format requirement |
| `train/plan/2026-01-14-plan.md` | Add YAML frontmatter with templates |
| `train/src/routers/plans.py` | Parse frontmatter, return templates, strip from markdown |
| `train/src/templates/partials/idle_workout.html` | Add template picker modal |
| `train/src/static/js/today.js` | Modal open/close, fetch templates |
| `train/src/templates/partials/active_workout.html` | Filter to template exercises only |

## Out of Scope

- Substitute exercises UI
- Adding non-template exercises during workout
- Sets/reps/RIR targets in frontmatter (keep in markdown)
