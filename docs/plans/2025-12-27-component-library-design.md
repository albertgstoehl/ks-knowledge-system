# Component Library Design

**Date:** 2025-12-27
**Status:** Approved

## Overview

A shared component library for all knowledge-system services (bookmark-manager, canvas, kasten, balance) providing consistent UI and faster development with Claude Code.

## Goals

1. **Consistency** - All sites look identical (same spacing, same components)
2. **Maintainability** - Single source of truth, changes propagate everywhere
3. **Speed** - Faster to build new features by reusing tested components

## Distribution Strategy

**Copy at build/deploy time** - A `shared/` directory in the repo root gets copied into each service during Docker build. Services remain self-contained with no runtime dependencies.

## File Structure

```
knowledge-system/
├── shared/
│   ├── css/
│   │   ├── variables.css      # Colors, fonts, spacing tokens
│   │   ├── base.css           # Reset, body, typography
│   │   ├── components.css     # Buttons, tabs, cards, modals
│   │   └── utilities.css      # Spacing helpers, responsive
│   │
│   ├── templates/
│   │   └── components.html    # Jinja2 macros
│   │
│   ├── styleguide.html        # Visual preview (open in browser)
│   └── README.md              # Quick reference
│
├── docs/
│   └── COMPONENT-LIBRARY.md   # Full documentation for Claude
```

## CSS Tokens

```css
:root {
  /* Colors - Brutalist palette */
  --color-bg: #fff;
  --color-text: #000;
  --color-muted: #666;
  --color-border: #000;
  --color-border-light: #eee;
  --color-hover: #f5f5f5;
  --color-danger: #c00;
  --color-danger-bg: #fee;

  /* Typography */
  --font-mono: ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, Consolas, monospace;
  --font-size-xs: 0.625rem;   /* 10px */
  --font-size-sm: 0.75rem;    /* 12px */
  --font-size-base: 0.875rem; /* 14px */
  --font-size-lg: 1rem;       /* 16px */
  --font-size-xl: 1.25rem;    /* 20px */

  /* Spacing scale */
  --space-xs: 0.25rem;  /* 4px */
  --space-sm: 0.5rem;   /* 8px */
  --space-md: 1rem;     /* 16px */
  --space-lg: 1.5rem;   /* 24px */
  --space-xl: 2rem;     /* 32px */

  /* Breakpoints */
  --breakpoint-mobile: 768px;
  --safe-bottom: env(safe-area-inset-bottom, 0px);
}

/* Dark mode variant */
[data-theme="dark"] {
  --color-bg: #000;
  --color-text: #fff;
  --color-muted: #888;
  --color-border: #fff;
  --color-border-light: #333;
  --color-hover: #111;
}
```

## Components

### CSS Classes (BEM-like naming)

| Component | Classes |
|-----------|---------|
| Button | `.btn`, `.btn--primary`, `.btn--danger`, `.btn--ghost`, `.btn--full` |
| Header | `.header`, `.header__title` |
| Tabs | `.tabs`, `.tab`, `.tab--active` |
| Input | `.input` |
| Card | `.card` |
| Bottom Nav | `.bottom-nav`, `.bottom-nav__link`, `.bottom-nav__link--active` |

### Jinja2 Macros

```html
{% import "components.html" as ui %}

{{ ui.header("Balance", [("Timer", "/"), ("Log", "/log")], active="Timer") }}
{{ ui.button("Save", primary=true) }}
{{ ui.button("Cancel", danger=true) }}
{{ ui.input("intention", placeholder="What's the one thing?") }}

{% call ui.card() %}
  Card content here
{% endcall %}
```

**Macro signatures:**

- `header(title, tabs=[], active=none)` - Top nav with title and tabs
- `button(text, primary=false, danger=false, ghost=false, full=false, type="button", disabled=false)`
- `link_button(text, href, primary=false)` - Anchor styled as button
- `input(name, placeholder="", type="text", value="", required=false)`
- `card()` - Use with `{% call %}` block

## Service Integration

### Dockerfile

```dockerfile
COPY shared/ ./shared/
COPY src/ ./src/
```

### FastAPI (main.py)

```python
from fastapi.staticfiles import StaticFiles

app.mount("/static/shared", StaticFiles(directory="shared/css"), name="shared")
app.mount("/static", StaticFiles(directory="src/static"), name="static")

templates = Jinja2Templates(directory=["src/templates", "shared/templates"])
```

### Base Template

```html
<head>
  <link rel="stylesheet" href="/static/shared/variables.css">
  <link rel="stylesheet" href="/static/shared/base.css">
  <link rel="stylesheet" href="/static/shared/components.css">
  <link rel="stylesheet" href="/static/shared/utilities.css">
</head>
```

## Styleguide

Open `shared/styleguide.html` directly in browser to preview all components. No server needed.

## Migration Strategy

1. Create `shared/` directory with all CSS and macros
2. Update one service (Balance) to use shared components
3. Verify everything works
4. Migrate remaining services one at a time
5. Remove duplicate CSS from each service after migration
