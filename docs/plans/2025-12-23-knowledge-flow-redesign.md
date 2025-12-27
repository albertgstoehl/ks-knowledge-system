# Knowledge Flow Redesign: Expiry + Source Archive in Kasten

## Problem

Current flow has no pressure to process content:
- Bookmark Manager inbox grows indefinitely
- No friction between "save" and "archive"
- Archive is just "things I read" not "things I learned from"

## Solution

1. **Inbox expires** — Unprocessed items auto-delete after N days
2. **Processing = note creation** — To keep a source, must create a Kasten note referencing it
3. **Kasten owns the archive** — Sources table stores archived bookmarks, linked to notes

## New Architecture

```
BOOKMARK MANAGER (ephemeral)          KASTEN (permanent)
┌──────────────────────┐              ┌──────────────────────┐
│       INBOX          │              │       SOURCES        │
│  - capture via bot   │──────────────│  - title, url        │
│  - auto-expire 7d    │  on note     │  - summary, content  │
│  - triage UI         │  creation    │  - archived_at       │
└──────────────────────┘              ├──────────────────────┤
         │                            │        NOTES         │
         │ expires                    │  - content           │
         ▼                            │  - source_id (FK)    │
     (deleted)                        │  - links to others   │
                                      └──────────────────────┘
```

## Data Model Changes

### Kasten: New `sources` table

```python
class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, nullable=False)
    title = Column(String)
    description = Column(Text)  # AI summary from Bookmark Manager
    content = Column(Text)      # Full content/transcript
    video_id = Column(String)   # For YouTube sources
    archived_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    notes = relationship("Note", back_populates="source")
```

### Kasten: Update `notes` table

```python
class Note(Base):
    # ... existing fields ...
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)

    # Relationship
    source = relationship("Source", back_populates="notes")
```

### Bookmark Manager: Add expiry

```python
class Bookmark(Base):
    # ... existing fields ...
    expires_at = Column(DateTime)  # Set to added_at + 7 days
```

## API Changes

### Kasten: New endpoints

```
POST /api/sources
  - Body: { url, title, description, content, video_id }
  - Creates source, returns source_id
  - Called by Canvas when archiving a bookmark

GET /api/sources
  - List all sources (the archive)

GET /api/sources/{id}
  - Get source with linked notes

GET /api/notes/{id}/source
  - Get source for a note
```

### Kasten: Update note creation

```
POST /api/notes
  - Body: { content, parent_id, source_id }  # source_id is new
  - Links note to source if provided
```

### Bookmark Manager: New endpoints

```
GET /api/bookmarks/{id}/export
  - Returns full bookmark data for archiving to Kasten
  - { url, title, description, content, video_id }

DELETE /api/bookmarks/{id}
  - Explicit delete (after archived to Kasten)

GET /api/bookmarks/expiring
  - List items expiring in next 24h (for notification)
```

### Bookmark Manager: Expiry job

```python
# Run daily via cron
async def expire_old_bookmarks():
    cutoff = datetime.utcnow() - timedelta(days=7)
    await db.execute(
        delete(Bookmark).where(
            Bookmark.state == "inbox",
            Bookmark.added_at < cutoff
        )
    )
```

## Workflow

### Happy path: Content → Insight

1. User sends URL to Telegram bot
2. Bookmark Manager saves to inbox, sets `expires_at = now + 7 days`
3. User opens Canvas, pushes quote from bookmark
4. User drafts note in Canvas connecting insight to existing knowledge
5. User creates note → Canvas calls:
   - `GET /bookmarks/{id}/export` (get full data)
   - `POST /kasten/sources` (archive to Kasten)
   - `DELETE /bookmarks/{id}` (remove from inbox)
   - `POST /kasten/notes` with `source_id`
6. Source lives in Kasten forever, linked to note(s)

### Expiry path: Content → Forgotten

1. User sends URL to Telegram bot
2. Bookmark Manager saves to inbox
3. 7 days pass, user never processed it
4. Cron job deletes bookmark
5. Content is gone (and that's okay)

## UI Changes

### Bookmark Manager

- Show "Expires in X days" on each inbox item
- Sort by expiry (most urgent first)
- Optional: Daily digest notification of expiring items

### Kasten

- New "Sources" view listing archived bookmarks
- Each source shows linked notes
- Note view shows source citation if present

### Canvas

- "Archive & Create Note" button when working with bookmark content
- Handles the full flow (export → archive → create note → delete)

## Migration

1. Add `sources` table to Kasten
2. Add `source_id` to Kasten notes table
3. Add `expires_at` to Bookmark Manager
4. Set `expires_at` for existing inbox items (maybe grandfather them with 30 days?)
5. Move existing archived bookmarks to Kasten sources (one-time migration)
6. Remove archive state from Bookmark Manager

## Configuration

```
# Bookmark Manager
INBOX_EXPIRY_DAYS=7
EXPIRY_WARNING_DAYS=1  # Notify when 1 day left

# Optional
EXPIRY_ENABLED=true  # Feature flag during rollout
```

## Benefits

1. **Pressure to process** — Expiry creates natural triage rhythm
2. **Meaningful archive** — Sources are tied to actual insights
3. **Clean separation** — BM = capture, Kasten = knowledge
4. **Citation trail** — Notes have provenance (where did this insight come from?)
5. **Permission to forget** — Most content should expire, and that's healthy

## Open Questions

1. Should videos have longer expiry (14 days)? They take more time to consume.
2. Pin/paper bookmarks — do they expire? Or exempt?
3. Notification mechanism for expiring items?
4. What about RSS feed items — same expiry logic?
