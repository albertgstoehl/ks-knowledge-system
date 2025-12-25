# Canvas Source Linking Design

## Overview

When creating notes from Canvas, automatically extract source information from embedded quotes and link the note to that source in Kasten.

## Current State

1. **Bookmark-manager** sends quotes to Canvas with `{ text, source_url, source_title }`
2. **Canvas** embeds quotes as markdown: `> "quote"\n> — Title (url)`
3. **Canvas** creates notes via `POST /api/notes` with `{ title, content, parent }`
4. **Kasten** has Source model but notes created from Canvas have no source link

## Design

### Change Location

`canvas/src/templates/draft.html` - JavaScript only (no backend changes)

### Flow

```
User writes note with quotes
        ↓
User types "---" to create note
        ↓
Modal opens, user clicks "Create Note"
        ↓
createNote() parses content for first quote
        ↓
    ┌───────────────────────────────────┐
    │ Regex: /^>\s*—\s*(.+?)\s*\((\S+)\)\s*$/m │
    │ Extracts: title (group 1), url (group 2) │
    └───────────────────────────────────┘
        ↓
   Found source?
   ├── No  → source_id = null
   └── Yes → POST kasten/api/sources {url, title}
             → get source_id from response
        ↓
POST kasten/api/notes {title, content, parent, source_id}
        ↓
Note created with source header in Kasten
```

### Quote Format

```markdown
> "any quoted text here"
> — Source Title (https://example.com/path)
```

### Parsing Rules

- **First source wins** - only extract from first matching quote
- **No quotes** - note created without source (source_id = null)
- **Malformed quotes** - skip, no source linking
- **Duplicate URLs** - Kasten deduplicates (returns existing source)
- **Same source multiple times** - works naturally, URL deduplication handles it

### Implementation

Modify `createNote()` function in `draft.html`:

```javascript
window.createNote = async function() {
    if (!pendingNote) return;

    const parentSelect = document.getElementById('parent-select');
    const parent = parentSelect.value || null;

    // Parse first source from quotes
    let source_id = null;
    const sourceMatch = pendingNote.content.match(/^>\s*—\s*(.+?)\s*\((\S+)\)\s*$/m);

    if (sourceMatch) {
        const [, title, url] = sourceMatch;
        try {
            const sourceResp = await fetch(kastenUrl + '/api/sources', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, title })
            });
            if (sourceResp.ok) {
                const source = await sourceResp.json();
                source_id = source.id;
            }
        } catch (e) {
            console.warn('Failed to create source:', e);
            // Continue without source
        }
    }

    try {
        const resp = await fetch(kastenUrl + '/api/notes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: pendingNote.title,
                content: pendingNote.content,
                parent: parent,
                source_id: source_id
            })
        });
        // ... rest unchanged
    }
};
```

## No Changes Required

- **Bookmark-manager** - already sends url + title with quotes
- **Kasten backend** - already accepts source_id in POST /api/notes
- **Canvas backend** - frontend-only change

## Testing

1. Create note with quote from bookmark-manager → verify source header appears
2. Create note without quotes → verify no source header
3. Create note with multiple quotes → verify first source is used
4. Create two notes from same source → verify source is deduplicated
