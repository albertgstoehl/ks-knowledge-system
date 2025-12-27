# Shared Component Library Migration

**Date:** 2025-12-27
**Status:** Approved

## Overview

Migrate all services (bookmark-manager, canvas, kasten) to use the shared component library from `shared/`. Balance already uses this pattern and serves as the reference implementation.

## Goals

1. Consistent UI across all services
2. Single source of truth for components
3. Reduced code duplication
4. SPA-like navigation with htmx (no full page reloads)

## 1. Shared Library Extensions

### New CSS Components (`shared/css/components.css`)

| Component | CSS Class | Description |
|-----------|-----------|-------------|
| Accordion | `.accordion`, `.accordion__header`, `.accordion__content` | Collapsible sections (feed headers) |
| Dropdown Menu | `.dropdown`, `.dropdown__trigger`, `.dropdown__menu` | Click-triggered menus |
| Video Embed | `.video-embed` | 16:9 responsive container |
| Action Panel | `.action-panel`, `.action-panel__bar` | Conveyor belt actions (mobile-aware) |
| Nav Bar | `.nav-bar`, `.nav-bar__btn` | Back/forward navigation |
| Source Panel | `.source-panel`, `.source-panel__header`, `.source-panel__details` | Collapsible citation |
| Toolbar | `.toolbar` | Horizontal button bar |
| Status Bar | `.status-bar` | Right-aligned status indicator |
| Badge | `.badge`, `.badge--vid`, `.badge--doc`, `.badge--pin` | Inline labels |
| Layout 2-col | `.layout-2col` | Two-column responsive grid |

### Updated Components

- `bottom_nav` - Add htmx attributes for SPA navigation
- `modal` - Add brutalist fullscreen variant (`.modal--fullscreen`)

### New Jinja2 Macros (`shared/templates/components.html`)

```html
{% macro accordion(title, id, count=none, open=true) %}
{% macro dropdown_menu(trigger_text, items) %}
{% macro video_embed(video_id, start=0) %}
{% macro action_panel() %}  {# caller() for content #}
{% macro nav_bar(back=true, forward=true) %}
{% macro source_panel(source) %}
{% macro toolbar() %}  {# caller() for buttons #}
{% macro status_bar(text) %}
{% macro badge(type) %}  {# type: vid, doc, pin #}
{% macro layout_2col() %}  {# caller() for content #}
```

## 2. Infrastructure Changes

### Dockerfiles

All services use root context to access `shared/`:

```dockerfile
# bookmark-manager/Dockerfile, canvas/Dockerfile, kasten/Dockerfile
FROM python:3.11-slim
WORKDIR /app

COPY <service>/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY <service>/src/ ./src/
COPY shared/ ./shared/

# ... rest unchanged
```

### rebuild-k3s.sh

Remove special case for balance - all services build from root:

```bash
for svc in "${selected[@]}"; do
    echo "=== Building $svc ==="
    docker build -f "$svc/Dockerfile" -t "$svc:latest" .
    # ... rest unchanged
done
```

### FastAPI Setup (each service main.py)

```python
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Mount shared CSS first, then service-specific
app.mount("/static/shared", StaticFiles(directory="shared/css"), name="shared")
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Include shared templates in search path
templates = Jinja2Templates(directory=["src/templates", "shared/templates"])
```

## 3. Template Migration

### Base Template Pattern

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}{% endblock %}</title>
  <!-- Shared component library -->
  <link rel="stylesheet" href="/static/shared/variables.css">
  <link rel="stylesheet" href="/static/shared/base.css">
  <link rel="stylesheet" href="/static/shared/components.css">
  <link rel="stylesheet" href="/static/shared/utilities.css">
  <!-- Service-specific styles -->
  <link rel="stylesheet" href="/static/css/style.css">
  {% block head %}{% endblock %}
</head>
<body>
  {% import "components.html" as ui %}

  {{ ui.header("Service Name", tabs, active=active_tab) }}

  <main id="main-content">
    {% block content %}{% endblock %}
  </main>

  {{ ui.bottom_nav(tabs, active=active_tab) }}

  {% block scripts %}{% endblock %}
</body>
</html>
```

### Migration Per Service

| Service | Current | After |
|---------|---------|-------|
| bookmark-manager | ~800 lines inline CSS in base.html | Shared + `src/static/css/style.css` |
| canvas | ~60 lines inline CSS in base.html | Shared + `src/static/css/style.css` |
| kasten | ~130 lines inline CSS in base.html | Shared + `src/static/css/style.css` |

### What Goes Where

| Shared Library | Service-Specific CSS |
|----------------|---------------------|
| Buttons, inputs, cards | Conveyor belt layout (bookmark) |
| Header, tabs, bottom_nav | Video player controls (bookmark) |
| Modal, empty_state, progress | Graph/SVG styles (kasten) |
| Badge, accordion, dropdown | Editor styles (canvas) |
| Layout utilities | Workspace vis.js styles (canvas) |

## 4. htmx SPA Navigation

### Template Structure

```
templates/
  base.html                 # Full page shell
  _content_index.html       # Content partial (underscore prefix)
  index.html                # Extends base + includes partial
  _content_log.html
  log.html
  ...
```

### Router Pattern

```python
@router.get("/log")
async def log_page(request: Request):
    context = {"request": request, "active_nav": "log"}

    # htmx request → return just content partial
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("_content_log.html", context)

    # Full page request → return complete page
    return templates.TemplateResponse("log.html", context)
```

### Updated bottom_nav Macro

```html
{% macro bottom_nav(items, active=none) %}
<nav class="bottom-nav">
  <div class="bottom-nav__links">
    {% for label, href in items %}
    <a href="{{ href }}"
       class="bottom-nav__link {% if active == label %}bottom-nav__link--active{% endif %}"
       hx-get="{{ href }}"
       hx-target="#main-content"
       hx-swap="innerHTML"
       hx-push-url="true">{{ label }}</a>
    {% endfor %}
  </div>
</nav>
{% endmacro %}
```

### Benefits

- ~80% bandwidth reduction on tab switches
- Instant-feeling navigation
- Browser back/forward still works (hx-push-url)
- Graceful degradation (works without JS)

## 5. Services Summary

| Service | bottom_nav | htmx Partials | Tabs |
|---------|------------|---------------|------|
| Balance | Yes | Yes | Timer, Log, Stats, Settings |
| Bookmark-manager | Yes | Yes | Feeds, Inbox, Thesis, Pins |
| Canvas | Yes | Yes | Draft, Workspace |
| Kasten | No | No | Header only |

## Implementation Order

1. **Extend shared library** - Add new components to `shared/`
2. **Update infrastructure** - Dockerfiles, rebuild script
3. **Migrate bookmark-manager** - Most complex, validates all components
4. **Migrate canvas** - Simple, validates htmx pattern
5. **Migrate kasten** - Simplest, no bottom_nav
6. **Update Balance** - Add htmx partials (already uses shared)
7. **Test all services** - Verify mobile, desktop, htmx navigation

## Files Changed

### New/Modified in shared/
- `shared/css/components.css` - New components
- `shared/templates/components.html` - New macros

### Per Service
- `<service>/Dockerfile` - Add COPY shared/
- `<service>/src/main.py` - Mount shared, update templates path
- `<service>/src/templates/base.html` - Use shared CSS + components
- `<service>/src/templates/_content_*.html` - New partials
- `<service>/src/static/css/style.css` - Service-specific styles

### Scripts
- `scripts/rebuild-k3s.sh` - All services use root context
