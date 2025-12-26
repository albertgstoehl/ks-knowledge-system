# Canvas: Daily Draft Wipe & Workspace Note Deletion

## Overview

Two features for Canvas:

1. **Daily Draft Wipe** - Automatically clear draft content at midnight (Europe/Zurich)
2. **Workspace Note Deletion** - Add UI to delete notes from workspace (API already exists)

## Feature 1: Daily Draft Wipe

### API Endpoint

Add `DELETE /api/canvas` to clear draft content:

```python
@router.delete("/canvas")
async def clear_canvas(session: AsyncSession = Depends(get_db)):
    """Clear the draft content. Called by scheduled job at midnight."""
    canvas = await get_or_create_canvas(session)
    canvas.content = ""
    await session.commit()
    return {"status": "cleared"}
```

### K8s CronJob

```yaml
# k8s/canvas-daily-wipe.yaml

apiVersion: batch/v1
kind: CronJob
metadata:
  name: canvas-daily-wipe
  namespace: default
spec:
  schedule: "0 0 * * *"
  timeZone: "Europe/Zurich"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: wipe
            image: curlimages/curl:latest
            command:
            - curl
            - -X
            - DELETE
            - http://canvas:8000/api/canvas
          restartPolicy: OnFailure
```

Runs at midnight Swiss time. Uses internal K8s service name.

## Feature 2: Workspace Note Deletion

### Current State

- API exists: `DELETE /api/workspace/notes/{id}` (cascades to remove connections)
- UI only allows deleting connections, not notes

### Changes to workspace.js

**updateSelectionUI():**
- Enable delete button when notes OR edges selected
- Update info text to reflect selection type

**deleteSelected() (renamed from deleteConnections):**
- If notes selected: `DELETE /api/workspace/notes/{id}` for each
- If edges selected: `DELETE /api/workspace/connections/{id}` for each
- Remove from vis.js DataSet after successful API call

## Files Changed

| File | Change |
|------|--------|
| `canvas/src/routers/canvas.py` | Add `DELETE /api/canvas` endpoint |
| `k8s/canvas-daily-wipe.yaml` | New CronJob manifest |
| `canvas/static/workspace.js` | Enable note deletion in UI |
