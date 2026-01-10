# Component Library Extraction Design

**Date:** 2025-12-30
**Status:** Draft
**Depends on:** Nothing
**Blocks:** Thesis Workflow Design (2025-12-29)

## Problem

Services have duplicated CSS that should be in the shared component library:
- **bookmark-manager**: ~400 lines of inline CSS in base.html
- **balance**: ~1190 lines in style.css, 40-50% duplicated patterns
- **canvas**: Duplicate modal styles in templates
- **kasten**: Re-implements existing `.source-panel`

This causes:
- Inconsistent styling across services
- Maintenance burden (fix bugs in multiple places)
- New features can't reuse patterns

## Solution

Extract reusable components to `shared/css/components.css` as independent, bite-sized tasks. Each extraction:
1. Adds CSS to shared library
2. Adds visual example to styleguide.html
3. Updates one service to use it
4. Can be done in any order (no dependencies between tasks)

## Components to Extract

### From Bookmark-Manager (Priority: High)

| Component | Current Class | New Shared Class | Lines |
|-----------|--------------|------------------|-------|
| View Header | `.inbox-header`, `.inbox-count` | `.view-header`, `.view-header__title`, `.view-header__count` | ~15 |
| List Layout | `.list-layout` | `.layout--list-detail` | ~20 |
| Bookmark List | `.bookmark-list`, `.bookmark-item` | Enhance existing `.list`, `.list__item` | ~25 |
| Detail Panel | `.detail-panel`, `.detail-title`, etc. | `.detail-panel`, `.detail-panel__header`, `.detail-panel__content`, `.detail-panel__actions` | ~40 |
| Action Buttons | `.action-btn`, `.action-btn-primary` | `.action-panel__btn`, `.action-panel__btn--primary`, `.action-panel__btn--danger` | ~30 |
| Next Up | `.next-up`, `.next-up-header`, `.next-up-item` | `.next-up`, `.next-up__header`, `.next-up__item` | ~20 |
| Move Menu | `.move-menu`, `.move-menu-backdrop` | Enhance existing `.dropdown` | ~25 |
| Labels | `.label` | `.label` (enhance existing) | ~5 |

### From Balance (Priority: Medium)

| Component | Current Class | New Shared Class | Lines |
|-----------|--------------|------------------|-------|
| Option Buttons | `.type-btn`, `.option-btn`, `.quick-btn`, etc. (8 variants) | `.btn--option`, `.btn--option.selected` | ~20 |
| Timer Display | `.timer-display`, `.timer-large` | `.timer`, `.timer__value`, `.timer__label` | ~25 |
| Progress Ring | `.progress-ring` | `.progress-ring` (SVG-based) | ~30 |
| Settings Row | `.setting-row`, `.setting-label`, `.setting-value` | `.setting-row`, `.setting-row__label`, `.setting-row__value` | ~15 |

### From Canvas/Kasten (Priority: Low)

| Component | Current Class | New Shared Class | Lines |
|-----------|--------------|------------------|-------|
| Graph Container | `.workspace-canvas`, `.graph-container` | `.graph-container` | ~15 |
| Zoom Controls | `.zoom-controls`, `.zoom-btn` | `.button-group--compact` | ~15 |

### Services to Refactor (Use Existing Shared)

| Service | Duplicate | Should Use |
|---------|-----------|------------|
| Canvas | Custom `.modal` | Shared `.modal` |
| Balance | Custom `.modal-overlay` | Shared `.modal` |
| Balance | `.log-tabs` | Shared `.tabs` |
| Balance | `.progress-bar` | Shared `.progress` |
| Kasten | Custom source panel | Shared `.source-panel` |

## Non-Goals

- **No new animations file** - Keep animations in service CSS for now
- **No theme modes extraction** - Balance's dark/break/evening modes stay service-specific
- **No JavaScript changes** - CSS only

## File Changes

| File | Change |
|------|--------|
| `shared/css/components.css` | Add ~250 lines of new components |
| `shared/styleguide.html` | Add visual examples for each new component |
| `shared/templates/components.html` | Add Jinja macros for new components |
| `docs/COMPONENT-LIBRARY.md` | Document new component APIs |
| `bookmark-manager/src/templates/base.html` | Remove ~300 lines, use shared |
| `balance/src/static/css/style.css` | Remove ~200 lines, use shared |
| `canvas/src/templates/*.html` | Remove duplicate modal styles |
| `kasten/src/templates/*.html` | Use shared source-panel |

## Success Criteria

1. All services use shared components (no duplicate CSS)
2. styleguide.html shows all components
3. COMPONENT-LIBRARY.md documents all APIs
4. No visual regressions in any service
