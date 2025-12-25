# Knowledge System Terminal Style Guide

A unified design system for Bookmark Manager, Canvas, and Kasten.

**Philosophy:** Industrial terminal aesthetic. Function over decoration. High information density on desktop, generous touch targets on mobile. Every pixel earns its place.

---

## Typography

```css
--font-family: ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, Consolas, monospace;
--font-size-base: 1rem;        /* 16px - body text */
--font-size-sm: 0.875rem;      /* 14px - metadata, secondary */
--font-size-xs: 0.75rem;       /* 12px - labels, hints */
--font-size-xxs: 0.625rem;     /* 10px - section headers */
--font-weight-normal: 400;
--font-weight-medium: 500;     /* titles, emphasis */
--font-weight-bold: 700;       /* section headers */
--line-height: 1.6;
```

**Rules:**
- All text in monospace - no exceptions
- Titles: `font-weight: 500`, same size as body or `1.25rem` for page titles
- Section headers: `0.625rem`, `font-weight: 700`, `letter-spacing: 0.1em`, `text-transform: uppercase`
- Code inline: same font, no special styling needed (already monospace)

---

## Colors

```css
/* Core palette - black and white only */
--color-bg: #fff;
--color-text: #000;
--color-muted: #666;           /* metadata, hints, disabled */
--color-border: #000;
--color-hover: #f5f5f5;
--color-selected: #f5f5f5;     /* same as hover for consistency */
--color-danger: #c00;

/* Semantic aliases */
--color-primary: #000;
--color-primary-text: #fff;
--color-overlay: rgba(0, 0, 0, 0.5);
```

**Rules:**
- No gradients
- No colored backgrounds except inverted states
- Shadows only on hover: `3px 3px 0 #000`
- Links inherit color, no underline by default

---

## Spacing Scale

```css
--space-1: 0.25rem;   /* 4px  - tight */
--space-2: 0.5rem;    /* 8px  - compact */
--space-3: 0.75rem;   /* 12px - default padding */
--space-4: 1rem;      /* 16px - standard gap */
--space-5: 1.5rem;    /* 24px - section spacing */
--space-6: 2rem;      /* 32px - large gaps */
```

---

## Borders

```css
--border-width: 1px;
--border-width-thick: 2px;
--border-style: solid;
--border-color: #000;
--border: 1px solid #000;
--border-radius: 0;            /* NO border radius anywhere */
```

---

## Components

### Buttons

```css
.btn {
    padding: var(--space-2) var(--space-4);  /* 8px 16px */
    border: var(--border);
    background: var(--color-bg);
    color: var(--color-text);
    font-family: inherit;
    font-size: var(--font-size-sm);
    cursor: pointer;
    transition: all 0.15s ease;
}

.btn:hover {
    background: var(--color-hover);
}

.btn:active {
    transform: translate(1px, 1px);
}

.btn-primary {
    background: var(--color-primary);
    color: var(--color-primary-text);
}

.btn-primary:hover {
    background: #333;
}

.btn-danger {
    border-color: var(--color-danger);
    color: var(--color-danger);
}

.btn-danger:hover {
    background: #fee;
}

.btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
}
```

**Button Hierarchy:**
1. **Primary** (black): Main action - PROCESS, Connect, Save
2. **Secondary** (white): Supporting actions - Open, Cite, Export
3. **Danger** (red border): Destructive - Delete, Dismiss

### Tabs / Navigation

```css
.tabs {
    display: flex;
    gap: var(--space-4);
}

.tab {
    padding: var(--space-2) var(--space-4);
    border: var(--border);
    background: var(--color-bg);
    cursor: pointer;
}

.tab:hover {
    background: var(--color-hover);
}

.tab.active {
    background: var(--color-primary);
    color: var(--color-primary-text);
}
```

### Cards / Panels

```css
.card {
    border: var(--border);
    padding: var(--space-5);   /* 24px */
}

.card-compact {
    padding: var(--space-3);   /* 12px */
}
```

### List Items

```css
.list-item {
    padding: var(--space-3);
    border-bottom: 1px solid #eee;
    cursor: pointer;
    transition: all 0.15s ease;
}

.list-item:last-child {
    border-bottom: none;
}

.list-item:hover {
    background: var(--color-hover);
    box-shadow: 3px 3px 0 #000;
}

.list-item.selected {
    background: var(--color-selected);
}

.list-item:active {
    background: var(--color-primary);
    color: var(--color-primary-text);
}
```

### Form Inputs

```css
.input {
    width: 100%;
    padding: var(--space-3);
    border: var(--border);
    font-family: inherit;
    font-size: var(--font-size-base);
}

.input:focus {
    outline: 2px solid #000;
    outline-offset: 2px;
}

.input::placeholder {
    color: var(--color-muted);
}
```

### Modals

Full-screen takeover with black frame:

```css
.modal {
    position: fixed;
    inset: 0;
    background: var(--color-primary);
    z-index: 1000;
    display: flex;
    padding: 2px;              /* Creates black frame effect */
}

.modal-content {
    background: var(--color-bg);
    width: 100%;
    display: flex;
    flex-direction: column;
}

.modal-header {
    padding: var(--space-3) var(--space-4);
    background: var(--color-primary);
    color: var(--color-primary-text);
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--border-width-thick) solid #000;
}

.modal-header h2 {
    font-size: var(--font-size-sm);
    font-weight: 400;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.modal-body {
    flex: 1;
    padding: var(--space-4);
    overflow-y: auto;
}

.modal-footer {
    display: flex;
    border-top: var(--border-width-thick) solid #000;
    background: var(--color-primary);
}

.modal-footer .btn {
    flex: 1;
    border: none;
    padding: var(--space-4);
    font-size: var(--font-size-xs);
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.modal-footer .btn:first-child {
    background: var(--color-bg);
    border-right: var(--border-width-thick) solid #000;
}

.modal-footer .btn-primary {
    background: var(--color-primary);
    color: var(--color-primary-text);
}
```

### Bottom Sheet (Mobile Menus)

```css
.bottom-sheet {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--color-bg);
    border-top: var(--border-width-thick) solid #000;
    z-index: 200;
    transform: translateY(100%);
    transition: transform 0.2s ease;
}

.bottom-sheet.visible {
    transform: translateY(0);
}

.bottom-sheet-backdrop {
    position: fixed;
    inset: 0;
    background: var(--color-overlay);
    z-index: 199;
}

.bottom-sheet-item {
    padding: var(--space-4);
    border-bottom: 1px solid #eee;
    min-height: 48px;          /* Touch target */
    display: flex;
    align-items: center;
}
```

### Expandable Sections

```css
.expandable-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-3);
    background: var(--color-hover);
    cursor: pointer;
}

.expandable-toggle {
    font-size: var(--font-size-xs);
}

/* Use ▼ when expanded, ▶ when collapsed */
```

### Progress Bar

```css
.progress-bar {
    height: 4px;
    background: #eee;
    border: var(--border);
}

.progress-bar-fill {
    height: 100%;
    background: var(--color-primary);
    transition: width 0.3s ease;
}
```

### Status Indicators

Use **monochrome unicode symbols** that render correctly in monospace fonts.
Color emoji (🎥 📄 📌) don't work - they render as boxes in monospace.

**Recommended symbols:**
```
▶  Video/Play
◆  Document/Paper/Thesis
●  Pinned
○  Unpinned/Empty
▼  Expanded
▶  Collapsed
■  Filled/Active
□  Empty/Inactive
```

**Alternative - text labels (most terminal-like):**
```
[VID]  [DOC]  [PIN]  [RSS]
```

```css
/* Unicode symbols */
.indicator-video::before { content: "▶ "; }
.indicator-paper::before { content: "◆ "; }
.indicator-pinned::before { content: "● "; }
.indicator-thesis::before { content: "◆ "; }

/* Text labels alternative */
.indicator-video::before { content: "[VID] "; }
.indicator-paper::before { content: "[DOC] "; }
.indicator-pinned::before { content: "[PIN] "; }

/* Style */
.indicator::before {
    color: var(--color-text);  /* Black, not muted */
    margin-right: var(--space-1);
}
```

---

## Layout Patterns

### App Header

```
┌─────────────────────────────────────────────────────────┐
│ APP NAME                          [Tab1] [Tab2] [Tab3]  │
├─────────────────────────────────────────────────────────┤
```

```css
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: var(--space-4);
    margin-bottom: var(--space-5);
    border-bottom: var(--border);
}

.header h1 {
    font-size: 1.25rem;
    font-weight: 400;
}
```

### Two-Column Layout (Desktop)

```
┌──────────────────────┬──────────────────────┐
│                      │                      │
│    List / Content    │    Detail Panel      │
│                      │                      │
└──────────────────────┴──────────────────────┘
```

```css
.layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-6);
    align-items: start;
}

@media (max-width: 768px) {
    .layout {
        grid-template-columns: 1fr;
    }
}
```

### Conveyor Belt Layout (Single Focus)

```
┌──────────────────────────────────────┬─────────────────┐
│                                      │  [PRIMARY]      │
│         Current Item                 │  [Secondary]    │
│         (Large, focused)             │  [Secondary]    │
│                                      │  [Danger]       │
├──────────────────────────────────────┴─────────────────┤
│ Next Up: item1, item2, item3...                        │
├────────────────────────────────────────────────────────┤
│ ████████████░░░░░░░░░ Progress                         │
└────────────────────────────────────────────────────────┘
```

---

## Mobile Patterns

### Touch Targets

```css
/* Minimum 48px for all interactive elements */
--touch-target-min: 48px;

.touch-target {
    min-height: var(--touch-target-min);
    min-width: var(--touch-target-min);
}
```

### Mobile Action Bar

Replaces cramped horizontal buttons with structured layout:

```css
.mobile-action-bar {
    position: fixed;
    bottom: 56px;              /* Above bottom nav */
    left: 0;
    right: 0;
    background: var(--color-bg);
    border-top: var(--border-width-thick) solid #000;
    padding: var(--space-2);
    z-index: 99;
}

/* Primary action: full-width */
.mobile-action-bar .btn-primary {
    width: 100%;
    padding: var(--space-3);
    margin-bottom: var(--space-2);
}

/* Secondary actions: icon row */
.mobile-action-bar .action-row {
    display: flex;
    gap: var(--space-2);
}

.mobile-action-bar .action-row .btn {
    flex: 1;
    padding: var(--space-3);
    min-height: var(--touch-target-min);
}
```

### Bottom Navigation

```css
.bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 56px;
    background: var(--color-primary);
    z-index: 50;
}

.bottom-nav-links {
    display: flex;
    height: 100%;
    background: var(--color-bg);
}

.bottom-nav-link {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: var(--font-size-sm);
    border-right: var(--border);
}

.bottom-nav-link:last-child {
    border-right: none;
}

.bottom-nav-link.active {
    background: var(--color-primary);
    color: var(--color-primary-text);
}
```

### Mobile Detail Panel (Overlay)

```css
@media (max-width: 768px) {
    .detail-panel {
        position: fixed;
        inset: 0;
        bottom: 56px;
        background: var(--color-bg);
        z-index: 100;
        padding: var(--space-4);
        display: none;
    }

    .detail-panel.active {
        display: block;
    }

    .detail-panel .back-btn {
        margin-bottom: var(--space-4);
    }
}
```

---

## Interaction States

### Hover
```css
:hover {
    background: var(--color-hover);  /* #f5f5f5 */
}
```

### Active/Pressed
```css
:active {
    transform: translate(1px, 1px);
}
/* OR for toggle states: */
.active {
    background: var(--color-primary);
    color: var(--color-primary-text);
}
```

### Focus
```css
:focus {
    outline: 2px solid #000;
    outline-offset: 2px;
}
```

### Selected
```css
.selected {
    background: var(--color-selected);
}
```

### Disabled
```css
:disabled, .disabled {
    opacity: 0.3;
    cursor: not-allowed;
}
```

---

## Animation

Minimal, functional animations only:

```css
--transition-fast: 0.15s ease;
--transition-normal: 0.2s ease;
--transition-slow: 0.3s ease;
```

**Allowed animations:**
- Hover state transitions
- Button press feedback (`transform`)
- Panel slide-in/out
- Progress bar fill
- Modal fade-in

**Not allowed:**
- Bouncing, scaling, or spring physics
- Color animations (except fade)
- Decorative animations

---

## Responsive Breakpoints

```css
/* Mobile-first approach */
@media (min-width: 768px) { /* Tablet/Desktop */ }

/* Or max-width for overrides */
@media (max-width: 768px) { /* Mobile */ }
```

---

## Shared Components Across Apps

### Navigation Graph (Kasten/Canvas)

```css
.nav-graph {
    /* SVG-based, black fill for nodes */
}

.nav-graph-node {
    fill: var(--color-primary);
}

.nav-graph-label {
    font-family: var(--font-family);
    font-size: var(--font-size-xs);
}
```

### Source Attribution

```css
.source-block {
    border: var(--border-width-thick) solid #000;
    padding: var(--space-4);
}

.source-block::before {
    content: 'SOURCE';
    display: block;
    font-size: var(--font-size-xxs);
    font-weight: var(--font-weight-bold);
    letter-spacing: 0.2em;
    margin-bottom: var(--space-3);
    padding-bottom: var(--space-2);
    border-bottom: var(--border);
}
```

### Blockquotes

```css
blockquote, .quote {
    padding-left: var(--space-4);
    border-left: var(--border-width-thick) solid #000;
    color: var(--color-muted);
}

/* Or terminal-style with > prefix */
.quote-line::before {
    content: '> ';
    color: var(--color-muted);
}
```

---

## Anti-Patterns (Never Do)

1. **No color emoji** - Use monochrome unicode symbols (▶ ◆ ● ▼) or text labels
2. **No border-radius** - Sharp corners only
3. **No gradients** - Solid colors only
4. **No colored backgrounds** - Black, white, or gray only
5. **No browser dialogs** - Use custom modals (no `alert()`, `prompt()`, `confirm()`)
6. **No decorative shadows** - Only offset shadow on hover
7. **No web fonts** - System monospace stack only
8. **No icons libraries** - Text or CSS-only indicators

---

## Implementation Checklist

When building new features:

- [ ] All interactive elements have 48px+ touch targets on mobile
- [ ] Buttons follow Primary > Secondary > Danger hierarchy
- [ ] Modals use full-screen black frame pattern
- [ ] Lists have hover states with offset shadow
- [ ] No color emoji - use unicode symbols (▶ ◆ ●) or text labels
- [ ] Tab navigation uses inverted active state
- [ ] Forms have visible focus states
- [ ] Mobile has bottom sheet menus, not dropdowns
- [ ] Progress/status uses text or simple shapes
- [ ] Transitions are 0.15s-0.3s, ease timing
