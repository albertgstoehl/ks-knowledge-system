# Navigation Graph Redesign

## Problem

The current radial graph layout is unintuitive. All connected nodes appear scattered around the center without semantic meaning - no visual distinction between parent, next note, or branches.

## Solution

Redesign the graph to use a **horizontal timeline with vertical branches**:

```
     PARENT ←── CURRENT ──→ NEXT (oldest child)
                   │
                   ├── branch 1 (2nd child)
                   │
                   └── branch 2 (3rd child)
                         ↓
                   (newer = lower)
```

## Mental Model

- **LEFT (prev)**: The note this one backlinks to (parent in metadata)
- **RIGHT (next)**: First note that backlinks here (oldest child by created_at)
- **BELOW (branches)**: Additional notes that backlink here (younger siblings)

This follows reading direction (left-to-right for sequence) with branches expanding downward.

## Layout Specifications

### Positioning
- Canvas: 300×200px (unchanged)
- Node radius: 15px
- Horizontal spacing: ~80px between prev/current/next
- Vertical branch spacing: ~40px

### Coordinates
```
prev:     (50, 60)
current:  (150, 60)
next:     (250, 60)
branch1:  (150, 100)
branch2:  (150, 140)
+N more:  (150, 170) - text indicator
```

### Display Limits
- Max visible branches: 2
- If more exist: show "+N more" indicator (clickable)

## Styling (per style.md)

- Current node: filled #000
- Connected nodes: fill #fff, stroke #000, stroke-width 2px
- Lines: stroke #000, stroke-width 1px
- Hover state: fill #f5f5f5 on connected nodes
- Font: monospace, 10px for labels

No gradients. No shadows.

## Edge Cases

| Scenario | Display |
|----------|---------|
| Entry point (no parent) | No left node, line starts at current |
| Leaf node (no children) | No right node, no branches |
| 1 child | Show on right as "next" only |
| 2 children | Oldest → right, 2nd → first branch |
| 3+ children | Oldest → right, 2nd/3rd → branches, "+N more" |

## Interactions

- **Click node**: Navigate to that note
- **Hover node**: Tooltip with "id: title", fill changes to #f5f5f5
- **Click "+N more"**: Expand to show all branches (or dropdown)

## Backend Changes

Restructure API response for note view:

```python
# Current
{"back": [...], "forward": [...]}

# New
{
    "parent": {"id": "1220a", "title": "..."} | null,
    "children": [
        {"id": "1219c", "title": "...", "created_at": "..."},
        {"id": "1219d", "title": "...", "created_at": "..."}
    ]  # sorted by created_at ascending
}
```

Ensure `created_at` timestamp is captured and returned for sorting.

## Frontend Changes (note.html)

Replace the radial layout JS (~lines 50-140) with:

```javascript
const parent = /* from backend */;
const children = /* sorted by created_at asc */;

const positions = {
    prev: {x: 50, y: 60},
    current: {x: 150, y: 60},
    next: {x: 250, y: 60},
    branchStart: {x: 150, y: 100},
    branchSpacing: 40
};

// Draw parent on left (if exists)
// Draw current in center (filled)
// Draw children[0] on right as next (if exists)
// Draw children[1..2] below as branches
// Draw "+N more" text if children.length > 3
```

## Files to Modify

1. `src/templates/note.html` - Replace graph JS (~50 lines)
2. `src/routers/api.py` - Restructure response (~10 lines)
3. Ensure `created_at` in note model/scanner

## Not Changed

- Database schema
- Note content rendering
- Click navigation behavior
- Overall page layout
