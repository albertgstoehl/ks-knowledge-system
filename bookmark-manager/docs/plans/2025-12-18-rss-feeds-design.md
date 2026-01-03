# RSS Feeds Feature Design

## Overview

Add RSS feed subscriptions to the bookmark manager. Feed items appear in a dedicated "Feeds" tab, auto-expire after 24 hours, and can be promoted to the bookmark archive.

## User Flow

1. User goes to Feeds tab
2. Pastes an RSS feed URL to subscribe
3. Feed items appear grouped by source
4. User can:
   - **Open** - View article in new tab
   - **Save to Bookmarks** - Promotes to bookmark archive (runs existing Jina + LLM pipeline)
   - **Dismiss** - Hides item immediately
5. All items auto-expire after 24 hours regardless of action taken

## Data Model

### Feed Table
```sql
CREATE TABLE feeds (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    last_fetched_at DATETIME,
    error_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### FeedItem Table
```sql
CREATE TABLE feed_items (
    id INTEGER PRIMARY KEY,
    feed_id INTEGER NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
    guid TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    description TEXT,
    published_at DATETIME,
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(feed_id, guid)
);
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/feeds` | Subscribe to feed `{url}` |
| GET | `/feeds` | List all feeds with items |
| PATCH | `/feeds/{id}` | Rename feed `{title}` |
| DELETE | `/feeds/{id}` | Unsubscribe (cascades to items) |
| POST | `/feeds/{feed_id}/items/{item_id}/save` | Promote item to bookmark |
| DELETE | `/feeds/{feed_id}/items/{item_id}` | Dismiss item early |

## UI Structure

### Feeds Tab (`/ui/?view=feeds`)

```
[Bookmarks] [Inbox] [Archive] [Feeds]

+------------------------------------------+
| Add Feed: [_________________________][+] |
+------------------------------------------+

v Blog Name (3 items)                   [...]
  +--------------------------------------+
  | Article Title                        |
  | 2 hours ago - First line of desc...  |
  +--------------------------------------+
  | Another Article                      |
  | 5 hours ago - Description preview... |
  +--------------------------------------+

> Another Feed (collapsed)              [...]
```

### Feed Header Menu (...)
- Rename
- Unsubscribe

### Item Detail Panel
- Title
- Source feed name
- Published date
- Full description
- Buttons: [Open] [Save to Bookmarks] [Dismiss]

## Background Jobs

### Feed Refresh (every 2 hours)
1. Loop through all feeds where `error_count < 3`
2. Fetch RSS XML
3. Parse with `feedparser`
4. Insert new items (skip duplicates by guid)
5. Update `last_fetched_at`
6. On error: increment `error_count`
7. On success: reset `error_count` to 0

### Cleanup (every hour)
1. Delete from `feed_items` where `fetched_at < now - 24 hours`

## Error Handling

- Feeds with `error_count >= 3` shown with error state in UI
- User can retry (resets error count) or delete
- Individual fetch failures don't block other feeds

## Dependencies

- `feedparser` - RSS/Atom parsing library

## Not Included

- Telegram bot integration for feeds
- Visual indicators for saved items
- Folders/tags for organizing feeds
- Auto-discovery of RSS from website URLs
