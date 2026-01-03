# UI Redesign: Conveyor Belt Inbox + Void Archive

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate navigation to 3 tabs (Inbox/Archive/Feeds) with filter icons, redesign Inbox as focused "conveyor belt" and Archive as search-first "void".

**Architecture:** Remove separate Papers/Pins views, add toggle filter icons [📌][📄] to Inbox and Archive. Inbox becomes single-item focus mode. Archive shows empty state until search.

**Tech Stack:** Jinja2 templates, vanilla JS, CSS (brutalist style per docs/style.md)

---

## Design Overview

### Navigation Changes

**Before:**
- Tabs: Inbox | Papers | Pins | Archive | Feeds
- Bottom nav: Inbox | Papers | Pins | Archive | Feeds

**After:**
- Tabs: Inbox | Archive | Feeds
- Bottom nav: Inbox | Archive | Feeds
- Filter icons [📌][📄] in Inbox and Archive views

### Filter Icons Behavior

```
┌─────────────────────────────────────┐
│ [📌] [📄]                           │
└─────────────────────────────────────┘
```

- **Default:** White background, black border, black icon
- **Active:** Black background, white icon (inverted)
- **Hover:** Light gray background (#f5f5f5)
- **Interaction:** Toggle on click, only one active at a time, click again to deselect

---

## Inbox: Conveyor Belt Design

### Desktop Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ INBOX (12)                                         [📌] [📄]    │
├─────────────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────┬────────────────────────────┐ │
│ │                                │                            │ │
│ │ How to Build a Second Brain    │ [ARCHIVE]                  │ │
│ │ fortelabs.com                  │                            │ │
│ │                                │ [MARK AS PAPER]            │ │
│ │ A comprehensive system for     │                            │ │
│ │ capturing, organizing, and     │ [PIN FOR LATER]            │ │
│ │ sharing your knowledge...      │                            │ │
│ │                                ├────────────────────────────┤ │
│ │                                │ [Open] [Edit] [Cite]       │ │
│ │                                │ [Delete]                   │ │
│ ├────────────────────────────────┤                            │ │
│ │ NEXT UP:                       │                            │ │
│ │ · Why We Sleep                 │                            │ │
│ │ · Recursive Backprop           │                            │ │
│ │ · The Pragmatic Programmer     │                            │ │
│ └────────────────────────────────┴────────────────────────────┘ │
│                                                                 │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  9/12 remaining      │
└─────────────────────────────────────────────────────────────────┘
```

**Key elements:**
- Header shows count: `INBOX (12)`
- Filter icons top-right
- Left panel: Current item (large) + "NEXT UP" queue (small)
- Right panel: Stacked action buttons + secondary actions
- Progress bar at bottom

### Mobile Layout

**List view:**
```
┌─────────────────────────────┐
│ INBOX (12)      [📌] [📄]   │
├─────────────────────────────┤
│ ┌─────────────────────────┐ │
│ │ How to Build a Second   │ │
│ │ Brain                   │ │
│ │ fortelabs.com           │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ Why We Sleep            │ │
│ │ nature.com              │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ Recursive Backprop      │ │
│ │ arxiv.org               │ │
│ └─────────────────────────┘ │
│                             │
│ ░░░░░░░░░░░░░░  9/12       │
├─────────────────────────────┤
│ Inbox │ Archive │ Feeds     │
└─────────────────────────────┘
```

**Focus view (tap item):**
```
┌─────────────────────────────┐
│ ← Back              1 of 12 │
├─────────────────────────────┤
│                             │
│ How to Build a Second Brain │
│ fortelabs.com               │
│                             │
│ A comprehensive system for  │
│ capturing, organizing...    │
│                             │
├─────────────────────────────┤
│ [ARCHIVE]                   │
│ [MARK AS PAPER]             │
│ [PIN FOR LATER]             │
├─────────────────────────────┤
│ [Open] [Cite] [Delete]      │
└─────────────────────────────┘
```

### Empty State

```
┌─────────────────────────────────────┐
│ INBOX (0)               [📌] [📄]   │
├─────────────────────────────────────┤
│                                     │
│                                     │
│            INBOX ZERO               │
│                                     │
│     All bookmarks processed         │
│                                     │
│                                     │
└─────────────────────────────────────┘
```

---

## Archive: Void Design

### Desktop Layout - Empty State

```
┌─────────────────────────────────────────────────────────────────┐
│ [📌] [📄]  [Search archive...                                 ] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                                                                 │
│                        Search to begin                          │
│                                                                 │
│                                                                 │
│              ┌────────────────────────────────┐                 │
│              │ RECENTLY ARCHIVED              │                 │
│              ├────────────────────────────────┤                 │
│              │ How to Auth with OAuth2    2h  │                 │
│              │ Next.js Deployment Guide   1d  │                 │
│              │ React Hooks Deep Dive      3d  │                 │
│              │ GraphQL Best Practices     5d  │                 │
│              └────────────────────────────────┘                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Desktop Layout - Search Results

```
┌─────────────────────────────────────────────────────────────────┐
│ [📌] [📄]  [react                                     ] [Clear] │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────┐  ┌────────────────────────────┐ │
│ │ React Hooks Deep Dive       │  │ React Hooks Deep Dive      │ │
│ │ dev.to                      │  │ dev.to                     │ │
│ ├─────────────────────────────┤  │                            │ │
│ │ The Epic Saga of React      │  │ A comprehensive guide to   │ │
│ │ medium.com                  │  │ building custom hooks...   │ │
│ ├─────────────────────────────┤  │                            │ │
│ │ React Query Patterns        │  │ [Open] [Edit] [Cite]       │ │
│ │ github.com                  │  │ [Restore] [Delete]         │ │
│ └─────────────────────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Mobile Layout - Empty State

```
┌─────────────────────────────┐
│ [📌] [📄]                   │
│ [Search archive...        ] │
├─────────────────────────────┤
│                             │
│      Search to begin        │
│                             │
│  ┌───────────────────────┐  │
│  │ RECENTLY ARCHIVED     │  │
│  ├───────────────────────┤  │
│  │ OAuth2 Guide      2h  │  │
│  │ Next.js Deploy    1d  │  │
│  │ React Hooks       3d  │  │
│  └───────────────────────┘  │
│                             │
├─────────────────────────────┤
│ Inbox │ Archive │ Feeds     │
└─────────────────────────────┘
```

### Mobile - Search Results + Detail

Same pattern as current: tap item → fullscreen detail panel with "← Back" button.

---

## CSS Additions

### Filter Icons

```css
.filter-icons {
    display: flex;
    gap: 0.5rem;
}

.filter-icon {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #000;
    background: #fff;
    cursor: pointer;
    font-size: 1rem;
    transition: all 0.15s ease;
}

.filter-icon:hover {
    background: #f5f5f5;
}

.filter-icon.active {
    background: #000;
    filter: invert(1);
}
```

### Progress Bar

```css
.progress-bar {
    height: 4px;
    background: #eee;
    border: 1px solid #000;
    margin-top: 1rem;
}

.progress-bar-fill {
    height: 100%;
    background: #000;
    transition: width 0.3s ease;
}

.progress-text {
    font-size: 0.75rem;
    color: #666;
    text-align: right;
    margin-top: 0.25rem;
}
```

### Conveyor Belt Layout

```css
.conveyor-layout {
    display: grid;
    grid-template-columns: 1fr 250px;
    gap: 1rem;
    min-height: 60vh;
}

.current-item {
    border: 1px solid #000;
    padding: 1.5rem;
}

.current-item-title {
    font-size: 1.25rem;
    font-weight: 500;
    margin-bottom: 0.5rem;
}

.current-item-domain {
    color: #666;
    margin-bottom: 1rem;
}

.current-item-description {
    line-height: 1.6;
    margin-bottom: 1.5rem;
}

.next-up {
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid #eee;
}

.next-up-header {
    font-size: 0.625rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.5rem;
    color: #666;
}

.next-up-item {
    padding: 0.5rem 0;
    font-size: 0.875rem;
    color: #666;
    cursor: pointer;
}

.next-up-item:hover {
    color: #000;
}

.action-panel {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.action-btn {
    padding: 1rem;
    border: 1px solid #000;
    background: #fff;
    font-family: inherit;
    font-size: 0.875rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    cursor: pointer;
    transition: all 0.15s ease;
}

.action-btn:hover {
    background: #f5f5f5;
}

.action-btn-primary {
    background: #000;
    color: #fff;
}

.action-btn-primary:hover {
    background: #333;
}

@media (max-width: 768px) {
    .conveyor-layout {
        grid-template-columns: 1fr;
    }
}
```

### Archive Void Layout

```css
.archive-void {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 50vh;
    text-align: center;
}

.archive-void-message {
    color: #666;
    margin-bottom: 2rem;
}

.recently-archived {
    border: 1px solid #000;
    width: 100%;
    max-width: 400px;
}

.recently-archived-header {
    padding: 0.75rem;
    background: #f5f5f5;
    font-size: 0.625rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    border-bottom: 1px solid #000;
}

.recently-archived-item {
    display: flex;
    justify-content: space-between;
    padding: 0.75rem;
    border-bottom: 1px solid #eee;
    cursor: pointer;
    transition: all 0.15s ease;
}

.recently-archived-item:last-child {
    border-bottom: none;
}

.recently-archived-item:hover {
    background: #f5f5f5;
}

.recently-archived-time {
    color: #999;
    font-size: 0.75rem;
}
```

---

## Implementation Tasks

### Task 1: Remove Papers/Pins Tabs
- **Files:** `src/templates/index.html`, `src/templates/base.html`
- Remove Papers and Pinboard tabs from header
- Remove from bottom navigation
- Keep only: Inbox | Archive | Feeds

### Task 2: Add Filter Icons Component
- **Files:** `src/templates/base.html` (CSS), `src/templates/index.html`
- Add filter icons [📌][📄] to Inbox header
- Add filter icons to Archive search bar area
- Implement toggle behavior (click to activate, click again to deselect)
- Active state: inverted colors

### Task 3: Update UI Router for Filters
- **Files:** `src/routers/ui.py`
- Add `filter` query param: `?filter=paper` or `?filter=pin`
- Inbox: filter bookmarks by is_paper or pinned
- Archive: filter search results by is_paper or pinned
- Remove separate papers/pinboard/archive-pins views

### Task 4: Implement Conveyor Belt Inbox (Desktop)
- **Files:** `src/templates/index.html`
- New layout: current item (large) + next up queue (small) on left
- Action panel on right with stacked buttons
- Progress bar at bottom
- Item count in header

### Task 5: Implement Conveyor Belt Inbox (Mobile)
- **Files:** `src/templates/index.html`
- List view with progress bar
- Tap → fullscreen focus with stacked action buttons
- Position indicator (1 of 12)

### Task 6: Implement Archive Void (Desktop)
- **Files:** `src/templates/index.html`
- Empty state: "Search to begin" + recently archived section
- Search results: two-column layout (list + detail)
- Clear button appears when searching
- Recently archived fetched from API (last 5, state=read, order by read_at desc)

### Task 7: Implement Archive Void (Mobile)
- **Files:** `src/templates/index.html`
- Filter icons above search
- Empty state centered
- Search results → tap for fullscreen detail

### Task 8: Add Recently Archived API
- **Files:** `src/routers/bookmarks.py`
- New endpoint: `GET /bookmarks/recent-archived?limit=5`
- Returns last 5 archived bookmarks ordered by read_at desc

### Task 9: Update Style Guide
- **Files:** `docs/style.md`
- Add Filter Icons component
- Add Progress Bar component
- Add Conveyor Belt layout
- Add Archive Void layout
- Document empty states

### Task 10: Test and Deploy
- Test all views on desktop and mobile
- Verify filter toggle behavior
- Verify progress bar updates
- Deploy to k3s
