# Bookmark Categorization Design

## Problem

Single "inbox" doesn't distinguish between:
- Papers (thesis material → Zotero pipeline)
- Regular reading (blogs, news, articles)
- Tools/sites to try (pinboard concept)

## Solution

Two new fields on Bookmark model, smart filtering for views.

## Data Model Changes

```python
class Bookmark(Base):
    # ... existing fields ...
    is_paper = Column(Boolean, default=False, index=True)
    pinned = Column(Boolean, default=False, index=True)
    zotero_key = Column(String, nullable=True)  # Link to Zotero item
```

## Views (UI Filtering)

| View | Filter | Purpose |
|------|--------|---------|
| Inbox | `state=inbox AND NOT pinned AND NOT is_paper` | Regular reading |
| Papers | `is_paper=true AND state=inbox` | Thesis queue |
| Pinboard | `pinned=true AND state=inbox` | Tools to try |
| Archive Pins | `pinned=true AND state=read` | Tried & worth keeping |
| Read | `state=read AND NOT pinned` | Processed content |

## Telegram Bot Commands

| Command | Action |
|---------|--------|
| `<url>` | Save to inbox (auto-detects papers) |
| `/paper <url>` | Save as paper OR convert existing to paper |
| `/pin <url>` | Save and pin OR pin existing |

## Paper Auto-Detection

Match URL against academic domains:

```python
ACADEMIC_DOMAINS = [
    # Preprint servers
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
    "ssrn.com",
    "osf.io",
    "zenodo.org",
    "cogprints.org",

    # DOI resolvers
    "doi.org",

    # Databases / indexes
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "europepmc.org",
    "semanticscholar.org",
    "scholar.google.com",
    "core.ac.uk",
    "doaj.org",
    "jstor.org",
    "philpapers.org",
    "repec.org",
    "dblp.dagstuhl.de",
    "inspirehep.net",
    "citeseerx.ist.psu.edu",
    "scienceopen.com",

    # Publishers
    "sciencedirect.com",
    "springer.com",
    "springerlink.com",
    "link.springer.com",
    "nature.com",
    "wiley.com",
    "onlinelibrary.wiley.com",
    "tandfonline.com",
    "sagepub.com",
    "cambridge.org",
    "academic.oup.com",
    "oup.com",
    "plos.org",
    "frontiersin.org",
    "mdpi.com",
    "hindawi.com",
    "bioone.org",
    "ingentaconnect.com",
    "muse.jhu.edu",
    "rsc.org",

    # Tech/CS specific
    "ieee.org",
    "ieeexplore.ieee.org",
    "acm.org",
    "dl.acm.org",
    "portal.acm.org",
    "aclanthology.org",

    # Government/institutional
    "nih.gov",
    "eric.ed.gov",
    "nber.org",
    "osti.gov",
]
```

## Zotero Integration

### When: Mark paper as "read" in UI

### Flow:
1. Extract DOI from URL (arxiv pattern, doi.org, etc.)
2. If DOI found:
   - `fetchMetadataByDOI(doi)` from CrossRef
   - `createItem(metadata)` in Zotero
   - Add tag: `bookmark-manager`
3. If no DOI:
   - Create basic item with URL + title
   - Add tags: `bookmark-manager`, `needs-doi`
4. Store `zotero_key` on bookmark

### Zotero Tags
| Scenario | Tags |
|----------|------|
| DOI found, auto-imported | `bookmark-manager` |
| No DOI, needs manual fix | `bookmark-manager`, `needs-doi` |

### Environment Variables
```
ZOTERO_API_KEY=xxx
ZOTERO_USER_ID=xxx
```

## Archive Service Changes

Skip web.archive.org for:
- `pinned=true` (want live site to try)
- `is_paper=true` (PDF lives in Zotero)

## UI Changes

> Follow [docs/style.md](../style.md) for all UI components (brutalist/utilitarian, monospace, 1px black borders, no shadows except hover).

### Navigation Tabs
```
[Inbox] [Papers] [Pinboard] [Read]
```

### Inbox View
- Hide papers and pinned items
- Same card layout as before

### Papers View
- Filter: `is_paper=true AND state=inbox`
- "Mark Read" triggers Zotero sync
- Show Zotero status indicator if synced

### Pinboard View
- Filter: `pinned=true AND state=inbox`
- "Tried it" → moves to read (stays pinned = archive pins)
- "Not interesting" → delete

### Read View
- Sub-filter toggle: "Show archive pins"
- Archive pins = `pinned=true AND state=read`

### Card Actions
- Pin/unpin toggle (pin icon)
- Convert to paper (paper icon, only in inbox)

## Implementation Order

1. Database migration (add fields)
2. API changes (filters, new endpoints)
3. Telegram bot commands (/paper, /pin)
4. Paper auto-detection
5. UI tabs and filtering
6. Zotero sync service
7. Archive service exclusion
