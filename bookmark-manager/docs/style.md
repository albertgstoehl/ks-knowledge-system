# Bookmark Manager Style Guide

## Design Philosophy

**Brutalist/Utilitarian** - Function over decoration. Clear, honest interfaces.

## Typography

- **Font**: `ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, Consolas, monospace`
- **Body size**: 1rem (16px)
- **Small text**: 0.875rem (14px)
- **Headings**: Same font, weight 500, size 1.25rem

## Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#fff` | Page background |
| `--color-text` | `#000` | Primary text |
| `--color-muted` | `#666` | Secondary text, metadata |
| `--color-border` | `#000` | Borders, dividers |
| `--color-hover` | `#f5f5f5` | Hover states |
| `--color-danger` | `#c00` | Delete actions |

No gradients. No shadows except offset box-shadow (`3px 3px 0 #000`) on hover.

## Components

### Buttons
```css
.btn {
    padding: 0.5rem 1rem;
    border: 1px solid #000;
    background: #fff;
    font-family: inherit;
}
.btn-primary { background: #000; color: #fff; }
.btn-danger { border-color: #c00; color: #c00; }
```

### Cards/Panels
- 1px solid black border
- No border-radius
- Padding: 0.75rem to 1.5rem

### Form Inputs
- 1px solid black border
- Padding: 0.75rem
- Focus: 2px solid black outline, 2px offset

### Navigation Tabs
- Row of bordered buttons
- Active: inverted (black bg, white text)
- Mobile: bottom fixed bar, 56px height

## Layout

### Desktop (≥768px)
- Max-width: 1200px, centered
- Two-column grid: list | detail panel
- 2rem gap

### Mobile (<768px)
- Single column
- Detail panel: full-screen overlay
- Bottom navigation bar
- No min-height constraints

## Spacing Scale

- `0.25rem` (4px) - tight
- `0.5rem` (8px) - compact
- `0.75rem` (12px) - default padding
- `1rem` (16px) - standard gap
- `1.5rem` (24px) - section spacing
- `2rem` (32px) - large gaps

## Interaction States

- **Hover**: Light gray background (`#f5f5f5`), optional offset shadow
- **Active/Selected**: Inverted colors or gray background
- **Focus**: 2px black outline with offset
- **Disabled**: Not used (remove element instead)

## Mobile Considerations

- Touch targets: minimum 48px
- Bottom nav covers safe area with black background
- Viewport: `width=device-width, initial-scale=1.0, viewport-fit=cover`

## Content Rules

- No emojis unless user requests
- Dates: `Dec 18, 14:30` format
- URLs: Show domain only in lists, full URL in detail

## Filter Icons

Toggle buttons for filtering by category (paper/pin).

```css
.filter-icon {
    width: 40px;
    height: 40px;
    border: 1px solid #000;
    background: #fff;
}
.filter-icon.active {
    background: #000;
    filter: invert(1);
}
```

- Default: White background, black border
- Active: Inverted (black bg, white icon via filter)
- Only one active at a time

## Progress Bar

Shows processing progress in inbox.

```css
.progress-bar {
    height: 4px;
    background: #eee;
    border: 1px solid #000;
}
.progress-bar-fill {
    background: #000;
}
```

## Conveyor Belt Layout

Inbox single-item focus view.

- Desktop: 2-column grid (content | actions)
- Mobile: Stacked, tap to show action panel
- Shows "Next Up" queue below current item
- Progress bar at bottom

## Archive Void Layout

Search-first archive design.

- Empty state: "Search to begin" + recently archived list
- Search triggers standard two-column result layout
- Filter icons work on search results
