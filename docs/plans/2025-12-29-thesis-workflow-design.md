# Thesis Workflow Design

**Date:** 2025-12-29
**Status:** Draft
**Depends on:** Component Library Extraction (2025-12-30) - shared components must be extracted before implementing thesis UI

Scientific writing, outlining, and document production integrated into the knowledge system.

## Overview

Extends the knowledge system to support academic thesis writing with proper citation management, structured outlining, and portable document export.

**Philosophy:** The knowledge system handles DOI/ISBN-based sources automatically. Manual sources are handled via Zotero MCP in Claude sessions, then synced back.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Bookmark Manager          Canvas                Kasten      │
│  ┌──────────────┐         ┌──────────────┐     ┌──────────┐ │
│  │ + Zotero     │         │ + Outline    │     │ Atomic   │ │
│  │   integration│────────▶│   mode       │◀────│ notes    │ │
│  │ + PDF extract│         │ + Citations  │     │ + quotes │ │
│  │ + DOI/ISBN   │         │ + Export     │     │          │ │
│  └──────────────┘         └──────────────┘     └──────────┘ │
│         │                        │                    │      │
│         └────────────────────────┴────────────────────┘      │
│                               │                              │
│                    shared/citation.py                        │
│                    (APA 7 formatting)                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## New Components

### 1. Bookmark Manager: Zotero Integration

**New file:** `bookmark-manager/src/zotero.py`

Ported from zotero-mcp, self-contained for K3s deployment.

```python
class ZoteroClient:
    """Zotero Web API v3 client"""

    async def create_item(self, item_data: dict) -> str:
        """Create item in Zotero, return zotero_key"""

    async def get_pdf_attachment(self, item_key: str) -> bytes | None:
        """Download PDF attachment if exists"""

    async def get_citation_meta(self, item_key: str) -> dict:
        """Fetch citation metadata for item"""
```

**New file:** `bookmark-manager/src/identifiers.py`

```python
def detect_identifier(url: str, html: str) -> dict:
    """Detect DOI or ISBN from URL/content"""
    # Returns: {"type": "doi"|"isbn"|None, "value": "..."}
```

**New file:** `bookmark-manager/src/lookup.py`

```python
async def crossref_lookup(doi: str) -> dict:
    """Fetch metadata from CrossRef API"""

async def openlibrary_lookup(isbn: str) -> dict:
    """Fetch metadata from Open Library API"""
```

**New file:** `bookmark-manager/src/pdf.py`

```python
async def extract_pdf_text(pdf_path: str) -> list[dict]:
    """Extract text by page from PDF using PyMuPDF"""
    # Returns: [{"page": 1, "text": "..."}, ...]
```

**Model changes:** `bookmark-manager/src/models.py`

```python
class Bookmark(BaseModel):
    # ... existing fields ...

    # Zotero integration
    zotero_key: str | None = None
    citation_meta: dict | None = None  # {authors, year, title, journal, doi, isbn, source}

    # PDF content
    pdf_path: str | None = None
    pdf_content: list[dict] | None = None  # [{page, text}, ...]
    has_pdf: bool = False
```

**New endpoints:**

```
POST /api/bookmarks/{id}/sync-zotero
  - Detects DOI/ISBN or accepts user-provided
  - Looks up metadata (CrossRef/OpenLibrary)
  - Creates item in Zotero
  - Downloads PDF if available
  - Extracts text by page
  - Stores zotero_key + citation_meta + pdf_content

GET /api/bookmarks/{id}/pdf
  - Returns PDF content by page
  - Query param: ?page=8

GET /api/bookmarks/{id}/citation
  - Returns formatted APA 7 citation
  - Query params: ?page=8&format=inline|reference
```

---

### 2. Shared: Citation Formatting

**New file:** `shared/citation.py`

APA 7 formatting rules ported from `/home/ags/repos/zhaw-thesis/references/citation-guide.md`.

```python
def format_inline(meta: dict, page: str = None) -> str:
    """Format inline citation: (Author, Year, p. X)"""
    authors = meta.get("authors", [])
    year = meta.get("year", "n.d.")

    if len(authors) == 0:
        name = meta.get("title", "Unknown")[:20]
    elif len(authors) == 1:
        name = authors[0].get("family", "Unknown")
    elif len(authors) == 2:
        name = f"{authors[0]['family']} & {authors[1]['family']}"
    else:
        name = f"{authors[0]['family']} et al."

    if page:
        return f"({name}, {year}, p. {page})"
    return f"({name}, {year})"


def format_reference(meta: dict) -> str:
    """Format full APA 7 bibliography entry"""
    # Author(s). (Year). Title. Journal, Volume(Issue), Pages. DOI
    ...


def format_bibliography(metas: list[dict]) -> str:
    """Sort by first author and format full bibliography"""
    sorted_metas = sorted(metas, key=lambda m: m["authors"][0]["family"].lower())
    return "\n\n".join(format_reference(m) for m in sorted_metas)
```

---

### 3. Canvas: Outline Mode

New mode alongside Draft and Workspace.

**New tables:** `canvas/src/database.py`

```sql
CREATE TABLE IF NOT EXISTS outline_sections (
    id TEXT PRIMARY KEY,
    parent_id TEXT,
    position INTEGER,
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    status TEXT DEFAULT 'empty',  -- empty | draft | done
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (parent_id) REFERENCES outline_sections(id)
);

CREATE TABLE IF NOT EXISTS section_citations (
    id TEXT PRIMARY KEY,
    section_id TEXT NOT NULL,
    bookmark_id TEXT NOT NULL,
    quote_text TEXT,
    page_number TEXT,
    position INTEGER,
    FOREIGN KEY (section_id) REFERENCES outline_sections(id)
);

CREATE TABLE IF NOT EXISTS section_sources (
    id TEXT PRIMARY KEY,
    section_id TEXT NOT NULL,
    kasten_note_id TEXT NOT NULL,
    original_text TEXT,  -- Snapshot when inserted
    position INTEGER,
    hidden INTEGER DEFAULT 0,
    FOREIGN KEY (section_id) REFERENCES outline_sections(id)
);
```

**New router:** `canvas/src/routers/outline.py`

```python
# Section management
GET    /api/outline                     # Full outline tree with word counts
POST   /api/outline/sections            # Create section
PUT    /api/outline/sections/{id}       # Update section content
DELETE /api/outline/sections/{id}       # Delete section
PUT    /api/outline/sections/{id}/move  # Reorder (parent_id, position)

# Insert from Kasten
POST   /api/outline/sections/{id}/insert-note
       # Body: {kasten_note_id: "1224a"}
       # Copies note content as starting point

# Citations
POST   /api/outline/sections/{id}/cite
       # Body: {bookmark_id, quote_text, page_number}
DELETE /api/outline/citations/{id}

# Export
GET    /api/outline/export              # Full document markdown
GET    /api/outline/export/bib          # BibTeX bibliography
GET    /api/outline/export/references   # APA 7 references section
GET    /api/outline/stats               # Word count per section + total
```

**New template:** `canvas/src/templates/outline.html`

Three-column layout:
1. Left: Collapsible outline tree with word counts and status
2. Center: Section editor (markdown)
3. Right: Insert panel (search notes, search sources)

---

## Flows

### Flow 1: Add Paper for Screening

```
User finds paper
       │
       ▼
Bookmark Manager: Add URL
       │
       ▼
Auto-detect: academic domain → is_thesis = true
Auto-detect: DOI/ISBN from URL/meta tags
       │
       ▼
Lands in Inbox for screening
```

### Flow 2: Sync to Zotero (DOI/ISBN path)

```
User clicks [Add to Zotero]
       │
       ▼
Identifier detected?
       │
   ┌───┴───┐
  YES      NO
   │        │
   ▼        ▼
Lookup    User provides DOI/ISBN
(CrossRef/   or "Handle via Zotero"
OpenLibrary)
   │
   ▼
Verification modal
(confirm metadata, source: crossref/openlibrary)
   │
   ▼
Create in Zotero via API
   │
   ▼
Check for PDF attachment
   │
   ├─ PDF exists → Download, extract text by page
   │
   └─ No PDF → has_pdf = false (can still cite, no page quotes)
   │
   ▼
Store: zotero_key, citation_meta, pdf_content
Archive bookmark (screening complete)
```

### Flow 3: Quote to Kasten Note

```
User viewing paper in Bookmark Manager
PDF content displayed by page
       │
       ▼
User selects text, clicks [Quote to Note]
       │
       ▼
Modal: Create new note or select existing
       │
       ▼
System inserts:
  - Quote block with citation reference
  - Source added to note frontmatter
       │
       ▼
Kasten note file:

---
id: 1224a
title: KG-RAG advantage
sources:
  - bookmark_id: "abc123"
    doi: "10.1109/TKDE.2024.3352100"
    url: "https://arxiv.org/abs/2306.08302"
    citation: "Pan et al., 2024"
---

# KG-RAG advantage

> "KGs encode explicit relationships..."
> — Pan et al. (2024, p. 8) <!-- ref:abc123|doi:10.1109/TKDE.2024.3352100|https://arxiv.org/abs/2306.08302 -->
```

### Flow 4: Build Outline

```
User opens Canvas Outline mode
       │
       ▼
Create thesis structure (sections, subsections)
       │
       ▼
Select section, click [+ Insert Note]
       │
       ▼
Search Kasten notes, select one
       │
       ▼
Note content inserted as starting point
Source tracked in section_sources
       │
       ▼
User formalizes prose in section editor
Citations render dynamically from bookmark metadata
       │
       ▼
Repeat for all sections
```

### Flow 5: Export

```
User clicks [Export]
       │
       ▼
System collects:
  - All section content
  - All citations used
       │
       ▼
Resolves citation references:
  <!-- ref:abc123|doi:...|url --> → (Pan et al., 2024, p. 8)
       │
       ▼
Generates:
  - thesis.md (complete document)
  - references.bib (BibTeX)
       │
       ▼
Output is standalone, no system dependency
```

---

## Citation Reference Format

Citations stored as references with fallback chain:

```markdown
> "Quote text..."
> — Pan et al. (2024, p. 8) <!-- ref:abc123|doi:10.1109/TKDE.2024.3352100|https://arxiv.org/abs/2306.08302 -->
```

**Fallback chain:**
1. `abc123` — Bookmark ID (system lookup)
2. `doi:10.1109/...` — Universal identifier (CrossRef lookup)
3. `https://...` — URL (last resort, still findable)

**Dynamic updates:** When source metadata is corrected (via Zotero MCP session), running `km sync-citations` updates the human-readable citation text while preserving the reference comment.

---

## Source Handling

| Has... | Lookup | Flow |
|--------|--------|------|
| DOI | CrossRef API | Automatic |
| ISBN | Open Library API | Automatic |
| Neither | — | Handle via Zotero MCP in Claude session, sync back |

**No manual citation entry in UI.** Sources without DOI/ISBN are added via Zotero MCP, then imported.

---

## Data Flow Summary

```
Zotero (source of truth, PDFs)
       │
       ▼ sync
Bookmark Manager (citation_meta, pdf_content)
       │
       ▼ quote
Kasten Note (frontmatter + reference comment)
       │
       ▼ insert
Canvas Outline (formalize prose)
       │
       ▼ export
Standalone Markdown + Bibliography
```

---

## File Structure

```
knowledge-system/
├── shared/
│   └── citation.py              # NEW: APA 7 formatting
├── bookmark-manager/
│   ├── src/
│   │   ├── zotero.py            # NEW: Zotero API client
│   │   ├── identifiers.py       # NEW: DOI/ISBN detection
│   │   ├── lookup.py            # NEW: CrossRef/OpenLibrary
│   │   ├── pdf.py               # NEW: PDF text extraction
│   │   ├── models.py            # MODIFIED: +zotero fields
│   │   ├── database.py          # MODIFIED: migration
│   │   └── routers/
│   │       └── bookmarks.py     # MODIFIED: +sync-zotero
│   └── data/
│       └── pdfs/                # NEW: cached PDFs
├── canvas/
│   └── src/
│       ├── database.py          # MODIFIED: +outline tables
│       ├── routers/
│       │   └── outline.py       # NEW: outline endpoints
│       └── templates/
│           └── outline.html     # NEW: outline UI
└── k8s/
    └── secrets.yaml             # MODIFIED: +Zotero credentials
```

---

## Environment Variables

```yaml
# K8s secrets
ZOTERO_API_KEY: "..."      # From https://www.zotero.org/settings/keys
ZOTERO_USER_ID: "..."      # Visible in API key settings
ZOTERO_COLLECTION: "..."   # Optional: sync specific collection only
```

---

## Dependencies

```
# bookmark-manager/requirements.txt
PyMuPDF==1.24.0    # PDF text extraction
httpx==0.27.0      # Async HTTP client (for CrossRef, OpenLibrary, Zotero APIs)
```

---

## UI Mockups

### Bookmark Manager: Sync Modal

```
┌───────────────────────────────────────────────────────────┐
│  SYNC TO ZOTERO                                           │
│  ─────────────────────────────────────────────────────    │
│                                                           │
│  Detected: DOI 10.1109/TKDE.2024.3352100  ✓ CrossRef     │
│                                                           │
│  Authors: Pan, S., Luo, L., Wang, Y., ...                │
│  Year:    2024                                            │
│  Title:   Unifying Large Language Models and Knowledge...│
│  Journal: IEEE TKDE                                       │
│                                                           │
│  Preview: (Pan et al., 2024)                             │
│                                                           │
│                           [Cancel]  [Confirm & Sync]      │
└───────────────────────────────────────────────────────────┘
```

### Bookmark Manager: No Identifier

```
┌───────────────────────────────────────────────────────────┐
│  SYNC TO ZOTERO                                           │
│  ─────────────────────────────────────────────────────    │
│                                                           │
│  ⚠ No identifier detected                                │
│                                                           │
│  ○ DOI:  [                              ] [Lookup]       │
│  ○ ISBN: [                              ] [Lookup]       │
│                                                           │
│  No DOI or ISBN? Add via Zotero directly, then sync.     │
│                                                           │
│                                            [Cancel]       │
└───────────────────────────────────────────────────────────┘
```

### Bookmark Manager: PDF Quote Selection

```
┌───────────────────────────────────────────────────────────┐
│  Pan et al. (2024)                     [<] Page 8/23 [>] │
│  ─────────────────────────────────────────────────────    │
│                                                           │
│  ...retrieval systems. However, vector similarity         │
│  alone cannot capture the explicit relationships          │
│  encoded in knowledge graphs.                             │
│                                                           │
│  ║ KGs encode explicit relationships between entities,  ║ │
│  ║ enabling multi-hop reasoning that retrieval alone    ║ │
│  ║ cannot perform.                                      ║ │
│         ↑ (selected text)                                 │
│                                                           │
│  This limitation motivates the integration of...          │
│                                                           │
│                    [Quote to Canvas]  [Quote to Note]     │
└───────────────────────────────────────────────────────────┘
```

### Canvas Outline

```
┌─────────────────────────────────────────────────────────────────┐
│  CANVAS              [Draft] [Workspace] [Outline]              │
├─────────────────────────────────────────────────────────────────┤
│  OUTLINE                │  SECTION: 2.3 KG-RAG         [287w]  │
│  ────────────────────   │  ─────────────────────────────────   │
│  ▼ 1. Introduction      │                                       │
│    ├─ 1.1 Problem [428w]│  ┌─ from: 1224a ──────────────────┐  │
│    ├─ 1.2 RQ [312w] ✓   │  │ > "KGs encode explicit..."     │  │
│    └─ 1.3 Scope [215w]  │  │ Vector similarity finds...     │  │
│  ▼ 2. Theory            │  └─────────────────────────────────┘  │
│    ├─ 2.1 KGs [286w] ✓  │                                       │
│    ├─ 2.2 RAG [312w] ✓  │  ▼ FORMALIZED                        │
│    └─ 2.3 KG-RAG [287w] │  ┌─────────────────────────────────┐  │
│  ▶ 3. Method            │  │ Knowledge graph-augmented       │  │
│  ▶ 4. Results           │  │ retrieval (KG-RAG) addresses    │  │
│  ▶ 5. Discussion        │  │ a fundamental limitation of...  │  │
│  ▶ 6. Conclusion        │  │                                 │  │
│                         │  └─────────────────────────────────┘  │
│  ────────────────────   │                                       │
│  Total: 8,847 / 10,000  │  [+ Insert Note]  [+ Insert Quote]   │
│  Sources: 28 cited      │                                       │
└─────────────────────────┴───────────────────────────────────────┘
```

---

## Implementation Priority

1. **Phase 1: Citation Infrastructure**
   - `shared/citation.py` — APA 7 formatting
   - `bookmark-manager/src/identifiers.py` — DOI/ISBN detection
   - `bookmark-manager/src/lookup.py` — CrossRef/OpenLibrary lookup

2. **Phase 2: Zotero Integration**
   - `bookmark-manager/src/zotero.py` — API client
   - `bookmark-manager/src/pdf.py` — PDF extraction
   - Sync endpoint + UI modal

3. **Phase 3: Quote Flow**
   - PDF viewer in Bookmark Manager
   - Quote to Kasten note with reference format
   - Frontmatter source tracking

4. **Phase 4: Canvas Outline**
   - Database tables
   - Outline router + endpoints
   - Outline UI with section editor

5. **Phase 5: Export**
   - Markdown export with resolved citations
   - Bibliography generation
   - BibTeX export

---

## Design Principles

- **DOI/ISBN = automatic, everything else = manual via Zotero MCP**
- **References, not copies** — Citations stored as references, rendered dynamically
- **Fallback chain** — bookmark_id | doi | url for portability
- **Portable output** — Exported files work standalone, no system dependency
- **Self-contained services** — All logic in K3s services, no external MCP dependency

---

## Future Enhancements (Nice-to-Have)

### PDF.js Viewer for Quote Selection

Currently the PDF quote view displays extracted text. A future enhancement would use **PDF.js** (Mozilla's JavaScript PDF renderer) to show the actual PDF with figures, tables, and formatting intact.

**Benefits:**
- See figures/tables in context when quoting
- Visual confirmation of page layout
- Better UX for academic work

**Implementation:**
- PDF.js library (~500KB)
- Bookmark-manager serves PDFs via `/api/papers/{id}/pdf`
- Text selection in PDF.js → maps to page coordinates → quote sidebar
- PyMuPDF still needed server-side for search/indexing

**Complexity:** Medium. PDF.js is well-supported but adds bundle size and coordinate mapping complexity.

**Priority:** Phase 2+ — implement after core quote flow works with extracted text.
