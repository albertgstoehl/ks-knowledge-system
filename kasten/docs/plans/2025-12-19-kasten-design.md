# Kasten: Zettelkasten Note Browser

## Overview

Kasten is a minimal note browser for navigating a Zettelkasten. No search - you explore by following links. Structure emerges from connections.

```
CANVAS ──creates notes──► KASTEN ──push to workspace──► CANVAS
         (draft mode)     (browse)                      (workspace mode)
```

Kasten is read-only navigation. Creating and connecting notes happens in Canvas.

## Philosophy

**Simple rules, emergent structure:**
1. Notes are files
2. Notes link to other notes `[[id]]`
3. That's it

No search. No categories. No tags. You get lost in your notes to find what you're looking for - true Luhmann style.

## Note IDs

Simple date + letter format:

```
1219a   ← Dec 19, first note
1219b   ← Dec 19, second note
1220a   ← Dec 20, first note
1220b   ← Dec 20, second note
```

- **Date prefix** = when created (MMDD)
- **Letter suffix** = which note that day (a, b, c...)
- **Structure** = purely in links, not IDs

Files: `1219a.md`, `1219b.md`, etc.

## Note Format

Plain markdown with inline links:

```markdown
The insight about supply chains [[1219b]] connects to
what I was thinking earlier about transparency in systems.

This builds on [[1218a]] but takes it further.
```

Links are `[[id]]`, rendered as clickable in UI.

## User Flow

### Landing Page

Two options to enter the graph:

```
┌────────────────────────────────────────────────────────┐
│                        KASTEN                          │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Entry Points                      [Feeling Lucky]     │
│                                                        │
│  ○ 1219a - Supply chain insight                        │
│  ○ 1215b - Transparency systems                        │
│  ○ 1210a - Knowledge emergence                         │
│                                                        │
└────────────────────────────────────────────────────────┘
```

- **Entry Points** = Notes with only outgoing links (starting points of chains)
- **Feeling Lucky** = Random note, forces discovery

### Note View

```
┌────────────────────────────────────────────────────────┐
│ ←                       [Push to Workspace]          → │
├────────────────────────────────────────────────────────┤
│                                                        │
│ The insight about supply chains [[1219b]] connects to  │
│ what I was thinking earlier about transparency in      │
│ systems.                                               │
│                                                        │
│ This builds on [[1218a]] but takes it further.         │
│                                                        │
├────────────────────────────────────────────────────────┤
│                                                        │
│              ○                                         │
│               \                                        │
│                ● ← 1219a                               │
│               /|\                                      │
│              ○ ○ ○                                     │
│                                                        │
└────────────────────────────────────────────────────────┘
```

**Navigation:**
- **←** One step back (where you came from)
- **→** One step forward (continue chain)
- **Node visualization** = Clickable circles showing connections
  - ● = Current note (filled)
  - ○ = Connected notes (backlinks above, forward links below)

**Node hover:** Shows first line of note content as preview.

**Action:**
- **Push to Workspace** = Send note to Canvas workspace

### Navigation Logic

- **Back (←)** = Previous note in your browsing history (like browser back)
- **Forward (→)** = Next note if you went back (like browser forward)
- **Click node** = Navigate to that note, becomes new position in history

## Architecture

```
kasten/
├── src/
│   ├── main.py              # FastAPI app
│   ├── database.py          # SQLite for link index
│   ├── models.py            # Note metadata
│   ├── scanner.py           # Parse markdown files, extract links
│   ├── routers/
│   │   ├── ui.py            # HTML pages
│   │   └── api.py           # JSON API
│   └── templates/
│       ├── base.html        # Layout, styling
│       ├── landing.html     # Entry points + feeling lucky
│       └── note.html        # Note view with node visualization
├── static/
│   └── graph.js             # Node visualization (simple SVG)
├── tests/
│   ├── test_api.py
│   └── test_ui.py
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

## Data Model

```python
class Note(Base):
    """Note metadata (content is in markdown files)"""
    __tablename__ = "notes"

    id = Column(String(10), primary_key=True)  # e.g., "1219a"
    title = Column(String(255))                 # First line of content
    created_at = Column(DateTime)
    file_path = Column(String(255))

class Link(Base):
    """Links between notes"""
    __tablename__ = "links"

    id = Column(Integer, primary_key=True)
    from_note_id = Column(String(10), ForeignKey("notes.id"))
    to_note_id = Column(String(10), ForeignKey("notes.id"))
```

**Note:** Actual content lives in markdown files. Database just indexes links for fast traversal.

## API Endpoints

```
GET /api/notes                    # List all notes
GET /api/notes/entry-points       # Notes with only outgoing links
GET /api/notes/random             # Random note
GET /api/notes/{id}               # Get note content + links
GET /api/notes/{id}/links         # Get forward and back links
POST /api/reindex                 # Rescan markdown files
```

## UI Routes

```
GET /                             # Landing page
GET /note/{id}                    # Note view
```

## Integration with Canvas

**Push to Workspace:**

When user clicks "Push to Workspace", Kasten calls Canvas API:

```
POST https://canvas.gstoehl.dev/api/workspace/notes
{
    "km_note_id": "1219a",
    "content": "The insight about supply chains..."
}
```

Canvas receives the note snapshot for arranging in workspace.

## Git Integration

Notes directory is a git repo. Kasten doesn't commit (Canvas does that when creating notes). Kasten just reads files.

Optional: Watch for file changes and auto-reindex.

## Styling

Follow `/home/ags/knowledge-system/bookmark-manager/docs/style.md`:
- Brutalist/utilitarian
- Monospace font
- Black borders, white background

## Deployment

**Caddy:**
```
kasten.gstoehl.dev {
    reverse_proxy kasten:8000
}
```

**Docker:** Joins `app-network` with bookmark-manager, canvas.

**Notes volume:** Mount the notes directory (e.g., `/home/ags/notes`) into container.

## The Full Ecosystem

```
bookmark.gstoehl.dev  → Sources (read articles, push quotes to Canvas)
canvas.gstoehl.dev    → Thinking (draft notes, arrange in workspace)
kasten.gstoehl.dev    → Notes (browse, push to Canvas workspace)
```

**Data flow:**
1. Read source in bookmark-manager
2. Push quote to Canvas draft
3. Write around quote, extract atomic note → saves to notes directory
4. Browse notes in Kasten
5. Push notes to Canvas workspace
6. Arrange, connect, export argument

## Implementation Phases

### Phase 1: Core
1. Project setup (FastAPI, SQLite)
2. Scanner to parse markdown files and extract links
3. Note view with content rendering

### Phase 2: Navigation
4. Landing page with entry points
5. Feeling lucky (random note)
6. Node visualization (SVG)
7. Click to navigate

### Phase 3: Integration
8. Push to Workspace button
9. Canvas API integration

### Phase 4: Polish
10. Git auto-reindex on file change
11. Playwright tests
12. Docker + Caddy
