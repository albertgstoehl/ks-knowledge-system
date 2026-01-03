# Canvas: Draft & Workspace

## Overview

Canvas is a thinking tool with two modes:

1. **Draft Mode** - Free-form writing with quotes pushed from bookmark-manager
2. **Workspace Mode** - Arrange km notes into connected arguments

```
BOOKMARK-MANAGER ──quotes──► CANVAS DRAFT ──extract──► KM
KM               ──notes───► CANVAS WORKSPACE ──export──► Text
```

Canvas only receives content. It doesn't create quotes or notes - those come from source systems.

## Draft Mode

### Purpose

Write freely. Quotes arrive from bookmark-manager. When a thought crystallizes, extract it to km.

### Flow

1. In bookmark-manager: select text, click "Push to Canvas"
2. Quote instantly appends to bottom of canvas as markdown blockquote
3. Write around quotes, develop thoughts
4. Mark atomic thoughts with `---` delimiters
5. Save popup appears, extract to km
6. Extracted section disappears from canvas

### Quote Format (in canvas)

```markdown
Your writing here...

> "The selected quote text"
> — Source Title (https://source.url)

More writing continues...
```

Plain text (editable), visually distinct, linked to source.

### Note Extraction

```markdown
Rambling thoughts...

---
This is an atomic insight.
> "supporting quote"
The quote matters because X.
---

More rambling...
```

When `---` markers close, popup appears:
- Search km notes to connect to
- Save (connected) or New Chain (standalone)
- Section disappears after save

### Connection Logic

When connecting to an existing note:
- If selected note has **no forward connections** → new note **continues** it
- If selected note **already has forward connections** → new note **branches** from it

User picks the note. System determines relationship.

## Workspace Mode

### Purpose

Arrange existing km notes into a connected argument. Visualize relationships.

### Flow

1. In km: view note, click "Push to Workspace"
2. Note appears in workspace graph (auto-positioned)
3. Connect notes with labeled edges ("therefore", "however", etc.)
4. Zoom/pan infinite canvas to navigate
5. Export to linear text when ready

### Key Concepts

- **One workspace** - No multiple workspaces, just one shared space
- **Full content visible** - Notes show complete text, not just titles
- **Infinite canvas** - Zoom in/out, pan around
- **Auto-layout** - System positions nodes, no manual drag/drop
- **Snapshots** - Notes are copied in, not linked (captures point-in-time)
- **Freeform labels** - Name connections anything: "therefore", "contradicts", custom text
- **Notes added via km only** - No "Add Note" button in workspace

### UI

```
┌────────────────────────────────────────────────────────┐
│ WORKSPACE                           [Draft] [Workspace]│
├────────────────────────────────────────────────────────┤
│ [+ Connect]  [Export]                       [−] [+]    │
├────────────────────────────────────────────────────────┤
│                                                        │
│   ┌──────────────┐                                     │
│   │ Full note    │                                     │
│   │ content here │──"therefore"──►┌──────────────┐    │
│   │ ...          │                │ Another note │    │
│   └──────────────┘                │ content...   │    │
│                                   └──────────────┘    │
│                                                        │
│   (zoom/pan infinite canvas)                           │
└────────────────────────────────────────────────────────┘
```

### Export Format

```markdown
Blockchain enables transparent record-keeping across supply chains.

**Therefore:**

Traceability improves when all parties can verify the chain of custody.

**However:**

Adoption barriers remain significant due to technical complexity and cost.
```

## Architecture

```
canvas/
├── src/
│   ├── main.py              # FastAPI app
│   ├── database.py          # SQLite + async SQLAlchemy
│   ├── models.py            # CanvasState, WorkspaceNote, WorkspaceConnection
│   ├── routers/
│   │   ├── ui.py            # HTML pages (htmx)
│   │   ├── canvas.py        # Draft mode API
│   │   └── workspace.py     # Workspace mode API
│   └── templates/
│       ├── base.html        # Layout, styling, htmx/vis.js
│       ├── draft.html       # Textarea editor
│       └── workspace.html   # Graph canvas
├── static/
│   └── workspace.js         # vis.js initialization
├── tests/
│   ├── test_api.py          # API tests
│   └── test_ui.py           # Playwright tests
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

## Data Model

```python
class CanvasState(Base):
    """Single draft canvas"""
    __tablename__ = "canvas_state"

    id: int = 1  # Always 1
    content: str
    updated_at: datetime

class WorkspaceNote(Base):
    """Note pulled from km into workspace"""
    __tablename__ = "workspace_notes"

    id: int
    km_note_id: str       # Reference to km
    content: str          # Snapshot of note content
    x: float              # Position (auto-layout)
    y: float

class WorkspaceConnection(Base):
    """Labeled edge between notes"""
    __tablename__ = "workspace_connections"

    id: int
    from_note_id: int     # FK to WorkspaceNote
    to_note_id: int       # FK to WorkspaceNote
    label: str            # "therefore", "however", etc.
```

## API Endpoints

### Draft Mode

```
POST /api/quotes              # Receive quote from bookmark-manager
                              # Appends to canvas content instantly

GET  /api/canvas              # Get current canvas content
PUT  /api/canvas              # Update canvas (auto-save)
```

### Workspace Mode

```
GET  /api/workspace                      # Get all notes + connections
POST /api/workspace/notes                # Add note (called by km only)
DELETE /api/workspace/notes/{id}         # Remove note from workspace

POST /api/workspace/connections          # Create connection
PUT  /api/workspace/connections/{id}     # Update label
DELETE /api/workspace/connections/{id}   # Remove connection

POST /api/workspace/export               # Export to text
```

### UI Routes

```
GET /                         # Redirect to /draft
GET /draft                    # Draft mode page
GET /workspace                # Workspace graph view
```

## Tech Stack

- **Backend:** FastAPI + async SQLAlchemy + SQLite
- **Frontend:** Jinja2 templates + htmx
- **Workspace graph:** vis.js (auto-layout, zoom/pan)
- **Auto-save:** Debounced 300ms + localStorage

## Styling

Follow `/home/ags/knowledge-system/bookmark-manager/docs/style.md`

## Deployment

**Caddy:**
```
canvas.gstoehl.dev {
    reverse_proxy canvas:8000
}
```

**Docker:** Joins `app-network` with bookmark-manager and km.

## Dependencies

Canvas depends on:
- **bookmark-manager**: Text selection + "Push to Canvas" button (to be added)
- **km**: Web UI with "Push to Workspace" button + API endpoints (to be added)
