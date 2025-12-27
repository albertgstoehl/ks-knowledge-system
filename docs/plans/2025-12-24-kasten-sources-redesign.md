# Kasten Sources Redesign

## Philosophy

Kasten becomes the **permanent archive** for processed content. Sources are bookmarks that have been "processed" — meaning a note was created from them. Sources are accessed through notes, not independently.

```
Bookmark Manager (ephemeral) → Canvas (process) → Kasten (permanent)
                                                      ↓
                                               Sources + Notes
```

## Design Principles

1. **No separate Sources view** — Sources are attached to notes, discovered through exploration
2. **Sources as context** — The source explains *why* a note exists
3. **Expandable details** — Clean by default, full context available on demand
4. **Fits existing aesthetic** — Horizontal rules, monospace, brutalist

## Data Model Changes

### New `sources` table

```python
class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, nullable=False)
    title = Column(String)
    description = Column(Text)      # AI summary from Bookmark Manager
    content = Column(Text)          # Full content/transcript (optional)
    video_id = Column(String)       # For YouTube sources
    archived_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    notes = relationship("Note", back_populates="source")
```

### Update `notes` table

```python
class Note(Base):
    # ... existing fields ...
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)

    # Relationship
    source = relationship("Source", back_populates="notes")
```

## API Changes

### New endpoints

```
POST /api/sources
  - Body: { url, title, description, content, video_id }
  - Creates source, returns source_id
  - Called by Canvas when processing a bookmark

GET /api/sources/{id}
  - Get source details
  - Returns: { id, url, title, description, content, video_id, archived_at, note_ids }
```

### Updated endpoints

```
POST /api/notes
  - Body: { content, parent_id, source_id }
  - source_id is new optional field
  - Links note to source if provided

GET /api/notes/{id}
  - Now includes source data if note has source_id
  - Returns: { ...note_fields, source: { url, title, description, ... } }
```

## UI Changes

### Note View with Source

Source appears as a collapsible header between the nav bar and note content.

**Desktop — Collapsed:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ KASTEN                                                                      │
│ ──────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│    [←]              Push to Workspace                [→]                    │
│                                                                             │
│ ──────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│    Source: How the Algorithm Hijacked Monkey's Brain             [+]       │
│    youtu.be · Dec 24                                                        │
│                                                                             │
│ ──────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│    Note Title                                                               │
│                                                                             │
│    Note content here...                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Desktop — Expanded:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ KASTEN                                                                      │
│ ──────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│    [←]              Push to Workspace                [→]                    │
│                                                                             │
│ ──────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│    Source: How the Algorithm Hijacked Monkey's Brain             [−]       │
│    youtu.be · Dec 24                                                        │
│                                                                             │
│    This video explains how algorithmic feeds exploit dopamine               │
│    responses and why we struggle to learn from online content.              │
│                                                                             │
│    Open original                                                            │
│                                                                             │
│ ──────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│    Note Title                                                               │
│                                                                             │
│    Note content here...                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Mobile — Collapsed:**
```
┌─────────────────────────────┐
│ KASTEN                      │
│ ─────────────────────────── │
│                             │
│ [←]  Push to Workspace  [→] │
│                             │
│ ─────────────────────────── │
│                             │
│ Source: How the Algorithm   │
│ Hijacked Monkey's Brain [+] │
│ youtu.be · Dec 24           │
│                             │
│ ─────────────────────────── │
│                             │
│ Note Title                  │
│                             │
│ Note content here...        │
│                             │
└─────────────────────────────┘
```

**Mobile — Expanded:**
```
┌─────────────────────────────┐
│ KASTEN                      │
│ ─────────────────────────── │
│                             │
│ [←]  Push to Workspace  [→] │
│                             │
│ ─────────────────────────── │
│                             │
│ Source: How the Algorithm   │
│ Hijacked Monkey's Brain [−] │
│ youtu.be · Dec 24           │
│                             │
│ This video explains how     │
│ algorithmic feeds exploit   │
│ dopamine responses...       │
│                             │
│ Open original               │
│                             │
│ ─────────────────────────── │
│                             │
│ Note Title                  │
│                             │
│ Note content here...        │
│                             │
└─────────────────────────────┘
```

### Source Header Elements

| Element | Style |
|---------|-------|
| "Source:" label | Regular weight, same as body text |
| Title | Bold, truncated if too long |
| [+]/[−] | Text toggle, right-aligned |
| Domain + date | Muted text (smaller or lighter) |
| Description | Regular text, shown when expanded |
| "Open original" | Text link, shown when expanded |

### Notes Without Sources

Notes without a `source_id` display exactly as they do today — no source header section.

## Workflow Integration

### Canvas → Kasten Flow

When user clicks "Process" in Bookmark Manager:

1. Opens Canvas with bookmark content pre-loaded
2. User writes note, extracts insights
3. User clicks "Create Note" in Canvas
4. Canvas orchestrates:
   ```
   1. GET /bookmark-manager/bookmarks/{id}/export
      → { url, title, description, content, video_id }

   2. POST /kasten/sources
      → { source_id }

   3. POST /kasten/notes
      Body: { content, source_id }
      → { note_id }

   4. DELETE /bookmark-manager/bookmarks/{id}
   ```
5. Bookmark is now permanently in Kasten as a source linked to the new note

### Multiple Notes from One Source

A source can have multiple notes linked to it. Each note shows the same source header. This is useful when:
- Revisiting content and extracting additional insights
- Different aspects of the same source warrant separate notes

## Migration

1. Create `sources` table
2. Add `source_id` column to `notes` table
3. No data migration needed — existing notes will have `source_id = NULL` and display as before

## Configuration

No new configuration needed. Sources are created through the Canvas workflow.
