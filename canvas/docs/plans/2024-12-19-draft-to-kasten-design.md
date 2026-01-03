# Draft to Kasten Note Creation

## Overview

Create notes in Kasten directly from the Canvas Draft editor using markdown-style delimiters.

## User Flow

1. User writes freely in Draft editor
2. When ready to promote text to a note, wraps it:
   ```
   ### My Note Title
   Content goes here with [[251219a]] links.
   ---
   ```
3. On typing `---` + Enter, modal appears
4. User optionally selects a parent note (searchable by ID)
5. Note is created as markdown file in Kasten
6. Delimited text is removed from Draft

## Delimiter Format

- `### Title` on its own line = start of note (title)
- `---` on its own line = end of note (triggers modal)
- Content between = note body

## Modal

**Contains:**
- Preview: title + first ~100 chars of content
- Parent dropdown: searchable by note ID, fetched via HTMX
- Default option: "No parent (new starting point)"
- Buttons: Cancel / Create Note

## Generated File

**ID Format:** `YYMMDD + letter` (e.g., `251219f`)

**File Location:** `/home/ags/notes/{id}.md`

**File Structure (with parent):**
```markdown
---
parent: 251219a
---
My Note Title

Content goes here with [[251219a]] links.
```

**File Structure (no parent):**
```markdown
My Note Title

Content goes here with [[251219a]] links.
```

## Safety Rules

1. Ignore `###` inside quote blocks (lines starting with `>`)
2. Ignore if content between `###` and `---` is empty
3. Ignore if no `###` found before `---`
4. On API error: show message, keep text in draft (don't lose work)

## API Requirements

**New endpoint needed in Kasten:**
- `GET /api/notes` - list all notes (for parent dropdown)
- `POST /api/notes` - create new note file

**Canvas calls Kasten API** (not workspace) to create notes.

## Visual Hint

Status bar shows: `### Title ... --- to create note`
