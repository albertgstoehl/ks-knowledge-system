# Service Migration to Shared Component Library

**Date:** 2025-01-01
**Status:** Design
**Scope:** Full consolidation of Canvas, Kasten, and Balance to shared components

## Overview

Migrate all three remaining services to use the shared component library, eliminating CSS duplication and ensuring consistent UI patterns.

## Service Analysis

### Canvas (Minimal Work)
Already clean - only has 3 lines of service-specific CSS in `base.html`:
- `html, body { height: 100%; }`
- `body { max-width: 1200px; margin: 0 auto; }`
- `.save-status { ... }`

**Action:** No changes needed.

### Kasten (Minor Work)
Has inline CSS in `base.html` for:
- `.entry-list`, `.entry-item`, `.entry-id` - can use `.list`, `.list__item`
- `.note-content` - keep (unique to Kasten)
- `.graph-container` - keep (unique to Kasten)

**Files to modify:**
- `kasten/src/templates/base.html` - remove `.entry-*` styles
- `kasten/src/templates/landing.html` - use `.list__item` classes

### Balance (Major Work)
Has 1190 lines in `style.css`. Many patterns duplicate shared components.

## Balance Class Mapping

| Balance Classes | Shared Equivalent | Notes |
|-----------------|-------------------|-------|
| `.timer-display .time`, `.timer-large`, `.break-timer` | `.timer__value` | Large timer numbers |
| `.timer-display .time-label` | `.timer__label` | Timer caption |
| `.type-btn`, `.option-btn`, `.quick-btn`, `.intensity-btn`, `.feeling-btn`, `.connection-btn`, `.who-btn`, `.period-btn`, `.log-tab` | `.btn--option` | All toggle/option buttons |
| `.type-selection`, `.options`, `.quick-durations`, `.intensity-options`, `.feeling-options`, `.connection-options`, `.who-options`, `.log-tabs`, `.period-selector`, `.binary-options` | `.button-group` | All button containers |
| `.setting-row`, `.setting-label`, `.setting-value`, `.setting-input`, `.setting-unit` | `.setting-row__*` | Settings page |
| `.modal-overlay`, `.modal-content`, `.modal-*` | `.modal__*` | Rabbit hole modal |
| `.progress-bar`, `.progress-bar-fill` | `.progress`, `.progress__fill` | Break progress |
| `.btn-primary` | `.btn--primary` | Primary action button |
| `.btn-ghost` | `.btn--ghost` | Abandon session button |
| `.btn-full` | `.btn--full` | Full-width button |

## Balance-Specific CSS (Keep)

These patterns are unique to Balance and should stay in `style.css`:

- **Theme modes:** `.dark-mode`, `.break-mode`, `.evening-mode`
- **Progress ring:** SVG-based circular progress (lines 319-343)
- **Session type badge:** Pulsing badge animation (lines 303-317)
- **Break message:** Typography for break page (lines 457-488)
- **Checkmark:** Completion indicator (lines 380-390)
- **Stats grid:** 2x3 stat cards layout (lines 987-1012)
- **Compass grid:** 2x2 life compass (lines 1029-1056)
- **Intention box:** Focus display during session (lines 345-363)
- **Today progress:** Dots visualization (lines 224-264)
- **Session counter:** "Session X of Y" styling (lines 365-374)

## Implementation Plan

### Task 1: Kasten Migration
1. Update `landing.html`: `.entry-item` → `.list__item`
2. Update `base.html`: Remove duplicated `.entry-*` CSS, keep `.list__item` overrides

### Task 2: Balance Template Updates
Update all Balance templates to use shared class names:
- `_content_index.html`: timer, option buttons, button groups
- `_content_settings.html`: setting rows (already matches)
- `_content_log.html`: tabs, option buttons, button groups
- `_content_evening.html`: option buttons, button groups
- `_content_stats.html`: period selector

### Task 3: Balance CSS Cleanup
Remove migrated CSS from `style.css`:
- Timer classes (~30 lines)
- Option button variants (~150 lines)
- Button group patterns (~100 lines)
- Modal classes (~90 lines)
- Progress bar (~15 lines)
- Button modifiers (~45 lines)

**Estimated reduction:** ~430 lines (36% of file)

### Task 4: Testing
- Verify Kasten entry list displays correctly
- Verify all Balance pages render correctly
- Test dark mode, break mode, evening mode
- Verify mobile responsiveness

## File Summary

| File | Action |
|------|--------|
| `kasten/src/templates/base.html` | Simplify CSS |
| `kasten/src/templates/landing.html` | Update classes |
| `balance/src/templates/_content_*.html` (5 files) | Update classes |
| `balance/src/static/css/style.css` | Remove ~430 lines |
