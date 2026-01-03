# Mobile Bottom Navigation Design

## Problem

Navigation tabs (Inbox, Archive, Feeds) are cramped on mobile. At 375px width, "Feeds" gets cut off showing only "Fe".

## Solution

Replace header tabs with a fixed bottom navigation bar on mobile devices.

## Structure

- Fixed to viewport bottom on mobile (< 768px)
- 3 equal-width tabs: Inbox | Archive | Feeds
- Hidden on desktop - header tabs remain unchanged
- Height: 56px (comfortable thumb target)

```
┌─────────────────────────┐
│ Bookmarks               │  ← Header (no tabs on mobile)
├─────────────────────────┤
│                         │
│   [content scrolls]     │
│                         │
├─────────────────────────┤
│  Inbox │ Archive│ Feeds │  ← Fixed bottom nav
└─────────────────────────┘
```

## Styling

Brutalist monospace aesthetic:

- Background: White (#fff) with black top border (1px solid #000)
- Tabs: Equal width (33.33%), text-centered
- Active state: Inverted (black bg, white text)
- Typography: Inherit monospace font, 14px
- Touch targets: Full 56px height, entire area tappable
- Dividers: 1px solid black vertical borders between tabs

## Behavior

- Content padding: `padding-bottom: 60px` on mobile to prevent content hiding behind nav
- Detail panel overlay: z-index 100 (above bottom nav at z-index 50)
- Scroll: Bottom nav fixed, content scrolls beneath
- Navigation: Standard links, no JS required

## Breakpoints

- < 768px: Bottom nav visible, header tabs hidden
- ≥ 768px: Header tabs visible, bottom nav hidden

## Implementation

Modify `src/templates/base.html`:
1. Add `.bottom-nav` HTML structure before closing `</body>`
2. Add mobile CSS for bottom nav styling
3. Add media query to hide header tabs on mobile
4. Add body padding-bottom on mobile
