# Retry Scrape Feature Design

**Date:** 2025-12-25
**Status:** Approved

## Overview

Add a button to retry scraping for bookmarks that failed initial content extraction.

## Detection Logic

A bookmark is considered "failed" if ANY of these conditions are true:
- `title` equals "Error" or "Error fetching content"
- `content` is NULL or empty string

Helper function:

```python
def is_scrape_failed(bookmark) -> bool:
    error_titles = {"Error", "Error fetching content"}
    has_error_title = bookmark.title in error_titles
    has_empty_content = not bookmark.content or not bookmark.content.strip()
    return has_error_title or has_empty_content
```

## API Endpoint

```
POST /bookmarks/{bookmark_id}/retry
```

**Behavior:**
- Calls existing `process_new_bookmark()` method (full pipeline: Jina → transcript → LLM summary → Web Archive)
- Returns updated bookmark on success

**Responses:**
- `200 OK` + updated bookmark JSON
- `404 Not Found` if bookmark doesn't exist
- `500 Internal Server Error` if retry fails

No request body needed.

## UI Changes

**Location:** Action panel in inbox view (right side)

**Button placement:**
```
┌────────────────────────────┐
│ [PROCESS]                  │
│ [Open] [Move ▾]            │
│ [RETRY SCRAPE]  ← new      │
│ [Delete]                   │
└────────────────────────────┘
```

**Visibility:** Only shown when `is_scrape_failed(bookmark)` is true.

**Behavior:**
1. Click → button shows "Retrying..." and disables
2. Fetch `POST /bookmarks/{id}/retry`
3. On success → page reload (shows updated content)
4. On failure → alert with error message, re-enable button

**Styling:** Same as other action buttons (`.action-btn`)

## Files to Modify

| File | Change |
|------|--------|
| `src/routers/bookmarks.py` | Add `POST /{id}/retry` endpoint |
| `src/templates/index.html` | Add retry button + JS handler |

## Scope

- ~30 lines Python
- ~20 lines JS/HTML
- Reuses existing `BackgroundJobService.process_new_bookmark()`
