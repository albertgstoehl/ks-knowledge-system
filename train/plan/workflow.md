# Plan Iteration Workflow

1. Review current plan markdown in this folder.
2. Summarize last 4 sessions (volume, PRs, skipped lifts).
3. Capture notes: pain, lagging muscles, motivation.
4. Propose changes and rationale.
5. Save as new markdown file referencing the previous plan.

## Frontmatter Format

Plans must include YAML frontmatter with template definitions:

```yaml
---
templates:
  Push:
    - name: Barbell bench press
      muscles: [chest, triceps, shoulders]
    - name: Incline dumbbell press
      muscles: [chest, shoulders]
    - name: Cable flyes
      muscles: [chest]
  Pull:
    - name: Barbell rows
      muscles: [back, biceps]
    - name: Lat pulldowns
      muscles: [back, biceps]
---
# Plan Title
...rest of markdown...
```

**Requirements:**
- Template names become workout session labels
- `name`: Exercise name (must match exactly when logging sets)
- `muscles`: List of muscle groups for volume tracking
- No sets/reps/RIR in frontmatter (keep in markdown tables)
