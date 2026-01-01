# Personal Drift Detection Design

Extends the existing priority drift alert to also detect when Personal sessions exceed Expected sessions.

## Problem

Current drift detection only shows when priorities are imbalanced (Thesis vs Work). But if you're doing mostly Personal sessions, that's a bigger issue - all priorities are being neglected.

## Solution

The drift alert becomes a unified "balance check" showing one issue - the most important one.

### Hierarchy

1. **Check personal ratio first** - If Personal > Expected this week, show personal drift
2. **Then check priority drift** - Only if Expected >= Personal, check if priorities are imbalanced

### Alert Messages

**Personal drift (when Personal > Expected):**
> **Expected** got only **35%** of sessions. **Personal** got **65%**.

**Priority drift (when Expected >= Personal but priorities imbalanced):**
> **Thesis** is priority #1 but got **20%** of sessions. **Work** (#2) got **80%**.

Same visual style, same component - just different content.

## API Changes

`GET /api/stats/drift` response extended:

```json
{
  "drift_type": "personal" | "priority" | null,
  "personal_drift": { "expected_pct": 35, "personal_pct": 65 },
  "priority_drift": { "priority": "Thesis", "rank": 1, "pct": 20, ... },
  "breakdown": [...]
}
```

Frontend checks `drift_type`:
- `"personal"` - show personal drift message
- `"priority"` - show priority drift message
- `null` - hide alert

## Logic

```python
expected_sessions = count where type='expected'
personal_sessions = count where type='personal'
total = expected + personal

if total == 0:
    drift_type = None
elif personal_sessions > expected_sessions:
    drift_type = "personal"
elif priority_imbalance_exists:
    drift_type = "priority"
else:
    drift_type = None
```

## Implementation

1. Update `/api/stats/drift` endpoint in `sessions.py`
2. Update `loadDrift()` in `_content_stats.html` to handle both drift types
3. No CSS changes needed - same `.drift-alert` component
