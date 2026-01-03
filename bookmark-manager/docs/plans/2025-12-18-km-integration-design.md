# Design: km Integration + Zotero Papers Workflow

## Goal

Create km notes from bookmarks and Zotero papers using a quote-then-respond workflow that enforces YOUR OWN ADDITION (not summary).

## Core Constraint

Cannot create a note without:
1. A specific quote from the content
2. Your own addition - what YOU contribute to this idea
3. A connection decision (stump / continue / branch)

## Three-Stage Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     SOURCES     │    │    PROCESSED    │    │   INTEGRATED    │
│                 │    │                 │    │                 │
│ Feeds           │ →  │ km notes with   │ →  │ Sticky note     │
│ Inbox           │    │ Luhmann         │    │ workspace       │
│ Papers          │    │ connections     │    │                 │
│                 │    │                 │    │                 │
│ "What to read"  │    │ "What I ADD"    │    │ "Arguments"     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Sources Tab

Single tab with collapsed sections:

```
┌─────────────────────────────┐
│ ▼ Feeds (12 new)            │
│   RSS items...              │
│                             │
│ ▶ Inbox (5)                 │
│   (collapsed)               │
│                             │
│ ▶ Papers (23 unprocessed)   │
│   (collapsed)               │
│                             │
│ ▶ Processed (142)           │
│   (collapsed)               │
└─────────────────────────────┘
```

### Papers Section
- Fetched via Zotero Web API (synced library)
- No triage needed - papers in Zotero are already screened
- "Unprocessed" = no km note linked to it
- "Processed" = has at least one km note

## Note Format (km)

```markdown
# [Your title - the idea you're adding]

> "[Exact quote from source]"

[Your addition - what YOU contribute, not summary]

---
Source: [Title](url)
Connected to: [[note-id]] (relationship)
```

## Note Creation Flow

```
┌─────────────────────────────────────┐
│ Source: Article Title               │
│ ────────────────────────────────    │
│                                     │
│ FULL CONTENT                        │
│ (highlight to select quote)         │
│                                     │
├─────────────────────────────────────┤
│ Quote: "[auto-filled from selection]│
│                                     │
│ Your addition:                      │
│ [What do YOU add to this idea?]     │
│                                     │
│ Connection:                         │
│ ○ New chain (stump)                 │
│ ○ Continues: [search existing note] │
│ ○ Branches from: [search + where]   │
│                                     │
│ [Create Note] [Cancel]              │
└─────────────────────────────────────┘
```

### Luhmann Connection Rules
- **Stump**: New thought chain, no connection (gets new ID like `42`)
- **Continues**: Extends an existing note (if note is `1`, this becomes `1a`)
- **Branches**: Inserts between notes (between `1a` and `1b` → becomes `1a1`)

The structure emerges from connections, not categories.

## Processed Tab

UI for viewing km notes with their connections:
- See note chains and branches
- Click to view full note
- "Add Note" to branch/continue from any note

## Integrated Tab (Phase 2)

Sticky note workspace for building arguments:

```
┌─────────────────────────────────────────────────┐
│  INTEGRATED: "Blockchain traceability claim"    │
│                                                 │
│  ┌──────┐              ┌──────┐                │
│  │Note  │ "therefore"  │Note  │  "leads to"    │
│  │1a2   │ ──────────►  │3b    │ ──────────►    │
│  └──────┘              └──────┘                │
│                             │                   │
│                             ▼                   │
│                        ┌──────┐                │
│                        │Note  │                │
│                        │7a1   │                │
│                        └──────┘                │
│                                                 │
│  [+ Pull note]              [Export to text]   │
└─────────────────────────────────────────────────┘
```

### Sticky Note Rules
- **Snapshots**: Copied from km, not linked (argument captures point-in-time)
- **Connections**: Freeform text ("therefore", "however", "this leads to", custom)
- **Export**: Notes in arranged order with connection text between

## Data Requirements

### Bookmark Model Changes
- Add `content` column (store Jina's full markdown)
- For YouTube: fetch transcript via `youtube-transcript-api`

### Zotero Integration
- Use Zotero Web API (user has synced library)
- Store API key in settings
- Table: `zotero_papers` - cache paper metadata
- Track which papers have km notes linked

### km Note Tracking
- Table: `km_notes` - track notes created through this UI
- Fields: `km_id`, `source_type` (bookmark/paper), `source_id`, `created_at`
- Used to determine "processed" status

## API Endpoints

### Phase 1: Sources → Processed

```
GET  /bookmarks/{id}/content      → Full content for note creation
POST /km/notes                    → Create km note (calls km CLI)

GET  /zotero/papers               → List papers from Zotero Web API
GET  /zotero/papers/{key}         → Paper details + PDF text
POST /zotero/papers/{key}/note    → Create km note from paper
```

### Phase 2: Processed Tab

```
GET  /km/notes                    → List all km notes with connections
GET  /km/notes/{id}               → Single note with chain context
```

### Phase 3: Integrated

```
POST /workspaces                  → Create argument workspace
GET  /workspaces/{id}             → Get workspace with sticky notes
POST /workspaces/{id}/notes       → Pull note snapshot into workspace
PUT  /workspaces/{id}/arrange     → Update arrangement + connections
POST /workspaces/{id}/export      → Export to text
```

## Implementation Phases

### Phase 1: Sources → Processed (FIRST)
1. Add `content` column to Bookmark model
2. Store full content when archiving (Jina markdown)
3. Build "Add Note" UI for bookmarks
4. Integrate Zotero Web API
5. Build "Add Note" UI for papers
6. Create km notes via CLI with connection support

### Phase 2: Processed Tab
1. Read km notes from filesystem
2. Build chain/branch visualization
3. Navigate note connections

### Phase 3: Integrated Workspace
1. Create workspace model
2. Build sticky note drag-and-drop UI
3. Freeform connection naming
4. Export to text

## Key Principles

1. **Addition, not extraction** - Notes must add your thinking, not summarize
2. **Forced connection** - Every note either starts a chain or connects
3. **Emergent structure** - Organization comes from connections, not categories
4. **Snapshots for arguments** - Arguments capture notes at a point in time
5. **Freeform logic** - Connection names are your reasoning made explicit
