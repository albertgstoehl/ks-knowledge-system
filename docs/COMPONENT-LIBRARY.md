# Component Library

Shared UI components for all knowledge-system services.

## Quick Start

### 1. Import CSS and JS in base template

```html
<head>
  <link rel="stylesheet" href="/static/shared/css/variables.css">
  <link rel="stylesheet" href="/static/shared/css/base.css">
  <link rel="stylesheet" href="/static/shared/css/components.css">
  <link rel="stylesheet" href="/static/shared/css/utilities.css">
</head>
<body>
  <!-- content -->
  <script src="/static/shared/js/components.js"></script>
</body>
```

### 2. Import macros in template

```html
{% import "components.html" as ui %}
```

### 3. Use components

```html
{{ ui.header("Balance", [("Timer", "/"), ("Log", "/log")], active="Timer") }}
{{ ui.button("Save", primary=true) }}
```

## Visual Preview

Open `shared/styleguide.html` directly in browser to see all components rendered.

---

## Components

### header(title, tabs=[], active=none)

Top navigation with title and optional tabs.

```html
{{ ui.header("Service Name") }}
{{ ui.header("Balance", [("Timer", "/"), ("Log", "/log"), ("Stats", "/stats")], active="Timer") }}
```

### button(text, primary=false, danger=false, ghost=false, full=false, lg=false, sm=false, type="button", disabled=false)

Standard button.

```html
{{ ui.button("Save") }}
{{ ui.button("Submit", primary=true) }}
{{ ui.button("Delete", danger=true) }}
{{ ui.button("Cancel", ghost=true) }}
{{ ui.button("Full Width", primary=true, full=true) }}
{{ ui.button("Large", lg=true) }}
{{ ui.button("Submit", type="submit") }}
{{ ui.button("Disabled", disabled=true) }}
```

### link_button(text, href, primary=false, danger=false, full=false)

Anchor styled as button.

```html
{{ ui.link_button("Go Home", "/") }}
{{ ui.link_button("Dashboard", "/dashboard", primary=true) }}
```

### input(name, placeholder="", type="text", value="", required=false, autofocus=false)

Text input field.

```html
{{ ui.input("email", placeholder="you@example.com") }}
{{ ui.input("password", type="password", required=true) }}
{{ ui.input("search", placeholder="Search...", autofocus=true) }}
```

### textarea(name, placeholder="", value="", rows=4, required=false)

Multi-line text input.

```html
{{ ui.textarea("content", placeholder="Write something...") }}
{{ ui.textarea("notes", rows=6) }}
```

### form_group(label, for_id=none, help=none)

Wrapper for form fields with label. Use with `{% call %}`.

```html
{% call ui.form_group("Email", "email") %}
  {{ ui.input("email", placeholder="you@example.com") }}
{% endcall %}

{% call ui.form_group("Password", "password", help="Minimum 8 characters") %}
  {{ ui.input("password", type="password") }}
{% endcall %}
```

### card(hover=false)

Bordered container. Use with `{% call %}`.

```html
{% call ui.card() %}
  <p>Card content here</p>
{% endcall %}

{% call ui.card(hover=true) %}
  <p>Clickable card with hover effect</p>
{% endcall %}
```

### tabs(items, active=none)

Standalone tabs (not in header).

```html
{{ ui.tabs([("Tab 1", "/tab1"), ("Tab 2", "/tab2")], active="Tab 1") }}
```

### bottom_nav(items, active=none)

Mobile bottom navigation. Only visible on screens < 768px.

```html
{{ ui.bottom_nav([("Timer", "/"), ("Log", "/log"), ("Stats", "/stats")], active="Timer") }}
```

### progress(percent, lg=false)

Progress bar.

```html
{{ ui.progress(75) }}
{{ ui.progress(50, lg=true) }}
```

### empty_state(title, message=none)

Empty state placeholder. Optionally use `{% call %}` for action button.

```html
{{ ui.empty_state("No items", "Add your first item to get started.") }}

{% call ui.empty_state("No bookmarks") %}
  {{ ui.button("Add Bookmark", primary=true) }}
{% endcall %}
```

### list() / list_item(title, meta=none, selected=false)

List container and items.

```html
{% call ui.list() %}
  {{ ui.list_item("Item One", "Meta info") }}
  {{ ui.list_item("Item Two", "More info", selected=true) }}
{% endcall %}
```

### markdown_content()

Container for rendered markdown content with proper typography.

```html
<div class="markdown-content">
  {{ rendered_html }}
</div>
```

Styles headings, paragraphs, tables, lists, code, and horizontal rules.

### Chart

Simple SVG line chart for progression data.

```html
<div class="chart" id="my-chart"></div>
<script>
  renderLineChart('my-chart', [
    { y: 50, label: 'W1' },
    { y: 55, label: 'W2' },
    { y: 57.5, label: 'W3' }
  ]);
</script>
```

**JavaScript API:**
- `renderLineChart(containerId, data, options)` - Render line chart
  - `data`: Array of `{ y: number, label?: string }`
  - Automatically scales Y-axis to data range

### modal(title, id=none, hidden=true)

Modal dialog. Use with `{% call %}`.

```html
{% call ui.modal("Confirm", id="confirm-modal") %}
  <p>Are you sure?</p>
{% endcall %}

<button onclick="document.getElementById('confirm-modal').hidden = false">Open</button>
```

### label(text)

Small uppercase label.

```html
{{ ui.label("Status") }}
```

---

## CSS Classes

For custom markup, use these classes directly:

| Component | Classes |
|-----------|---------|
| Button | `.btn`, `.btn--primary`, `.btn--danger`, `.btn--ghost`, `.btn--full`, `.btn--lg`, `.btn--sm` |
| Header | `.header`, `.header__title` |
| Tabs | `.tabs`, `.tab`, `.tab--active` |
| Input | `.input`, `.input--sm`, `.textarea` |
| Card | `.card`, `.card--hover`, `.card__title`, `.card__meta` |
| List | `.list`, `.list__item`, `.list__item--selected`, `.list__item-title`, `.list__item-meta` |
| Progress | `.progress`, `.progress--lg`, `.progress__fill` |
| Modal | `.modal`, `.modal__content`, `.modal__header`, `.modal__title`, `.modal__body`, `.modal__footer` |
| Bottom Nav | `.bottom-nav`, `.bottom-nav__links`, `.bottom-nav__link`, `.bottom-nav__link--active` |
| Empty State | `.empty-state`, `.empty-state__title`, `.empty-state__message` |
| Form | `.form-group`, `.form-group__label`, `.form-group__help` |
| Label | `.label` |
| View Header | `.view-header`, `.view-header__title`, `.view-header__count` |
| Detail Panel | `.detail-panel`, `.detail-panel__header`, `.detail-panel__title`, `.detail-panel__meta`, `.detail-panel__content`, `.detail-panel__actions`, `.detail-panel__empty` |
| Layout | `.layout--list-detail`, `.layout-2col`, `.layout-2col--sidebar` |
| Next Up | `.next-up`, `.next-up__header`, `.next-up__item`, `.next-up__title`, `.next-up__timer` |
| Option Buttons | `.btn--option`, `.button-group`, `.button-group--vertical` |
| Timer | `.timer`, `.timer__value`, `.timer__label` |
| Setting Row | `.setting-row`, `.setting-row__label`, `.setting-row__value`, `.setting-row__input`, `.setting-row__unit` |
| Action Panel | `.action-panel`, `.action-panel__btn`, `.action-panel__btn--primary`, `.action-panel__btn--danger` |
| Priority List | `.priority-list`, `.priority-list__item`, `.priority-list__rank`, `.priority-list__name`, `.priority-list__meta`, `.priority-list__arrows`, `.priority-list__arrow` |
| Dropdown (extended) | `.dropdown__item--with-meta`, `.dropdown__item-meta` |
| Drift Alert | `.drift-alert`, `.drift-alert__header`, `.drift-alert__main`, `.drift-alert__context`, `.drift-alert__stat` |
| Markdown | `.markdown-content` |
| Chart | `.chart`, `.chart__svg`, `.chart__line`, `.chart__point`, `.chart__axis`, `.chart__label`, `.chart__grid` |

---

## Layout Components

### View Header

Section header with title and optional count.

```html
<div class="view-header">
  <span class="view-header__title">INBOX (27)</span>
  <span class="view-header__count">3 unread</span>
</div>
```

### Detail Panel

Panel showing selected item details.

```html
<div class="detail-panel">
  <div class="detail-panel__header">
    <div class="detail-panel__title">Title</div>
    <div class="detail-panel__meta">Meta info</div>
  </div>
  <div class="detail-panel__content">Content here</div>
  <div class="detail-panel__actions">
    <button class="btn btn--primary">Action</button>
  </div>
</div>

<!-- Empty state -->
<div class="detail-panel">
  <div class="detail-panel__empty">Select an item</div>
</div>
```

### List-Detail Layout

Two-column layout with list and detail panel.

```html
<div class="layout--list-detail">
  <div class="list">...</div>
  <div class="detail-panel">...</div>
</div>
```

### Next Up

Preview list of upcoming items.

```html
<div class="next-up">
  <div class="next-up__header">Next Up</div>
  <div class="next-up__item">
    <span class="next-up__title">Item title</span>
    <span class="next-up__timer">2h ago</span>
  </div>
</div>
```

---

## Interactive Components

### Option Buttons

Toggle/multi-choice buttons.

```html
<div class="button-group">
  <button class="btn--option selected">Option A</button>
  <button class="btn--option">Option B</button>
</div>

<div class="button-group--vertical">
  <button class="btn--option">15 min</button>
  <button class="btn--option selected">30 min</button>
</div>
```

### Timer

Large timer display.

```html
<div class="timer">
  <div class="timer__value">25:00</div>
  <div class="timer__label">Focus Time</div>
</div>
```

### Setting Row

Key-value pairs for settings.

```html
<div class="setting-row">
  <span class="setting-row__label">Duration</span>
  <span class="setting-row__value">25 min</span>
</div>

<div class="setting-row">
  <span class="setting-row__label">Goal</span>
  <div>
    <input type="number" class="setting-row__input" value="4">
    <span class="setting-row__unit">sessions</span>
  </div>
</div>
```

### Priority List

Reorderable list with up/down arrow buttons.

```html
{{ ui.priority_list(priorities, id="priority-list") }}
```

Where `priorities` is a list of dicts: `[{"id": 1, "name": "Thesis", "meta": "2 sessions"}, ...]`

**Manual HTML:**

```html
<div class="priority-list" id="priority-list">
  <div class="priority-list__item" data-id="1">
    <span class="priority-list__rank">1</span>
    <span class="priority-list__name">Thesis</span>
    <span class="priority-list__meta">2 sessions</span>
    <span class="priority-list__arrows">
      <button class="priority-list__arrow" data-dir="up" onclick="movePriority(this, 'up')" disabled>&#9650;</button>
      <button class="priority-list__arrow" data-dir="down" onclick="movePriority(this, 'down')">&#9660;</button>
    </span>
  </div>
</div>
```

The `movePriority(btn, direction)` function handles reordering and updates rank numbers automatically.

### Dropdown with Meta

Extended dropdown items showing secondary info (like rank).

```html
<div class="dropdown dropdown--full">
  <button class="btn" onclick="toggleDropdown('my-dropdown')">
    Select...
    <span>▾</span>
  </button>
  <div class="dropdown__menu" id="dropdown-my-dropdown">
    <button class="dropdown__item dropdown__item--with-meta" onclick="...">
      <span>Option Name</span>
      <span class="dropdown__item-meta">#1</span>
    </button>
  </div>
  <div class="dropdown__backdrop" id="backdrop-my-dropdown" onclick="closeDropdown('my-dropdown')"></div>
</div>
```

---

## Design Tokens

CSS variables defined in `variables.css`:

### Colors

| Variable | Value | Usage |
|----------|-------|-------|
| `--color-bg` | #fff | Background |
| `--color-text` | #000 | Primary text |
| `--color-muted` | #666 | Secondary text |
| `--color-border` | #000 | Borders |
| `--color-border-light` | #eee | Subtle borders |
| `--color-hover` | #f5f5f5 | Hover states |
| `--color-danger` | #c00 | Error/danger |
| `--color-danger-bg` | #fee | Danger background |

### Typography

| Variable | Value | Usage |
|----------|-------|-------|
| `--font-mono` | ui-monospace, ... | All text |
| `--font-size-xs` | 0.625rem (10px) | Micro labels |
| `--font-size-sm` | 0.75rem (12px) | Labels, captions |
| `--font-size-base` | 0.875rem (14px) | Body text |
| `--font-size-lg` | 1rem (16px) | Inputs |
| `--font-size-xl` | 1.25rem (20px) | Titles |

### Spacing

| Variable | Value |
|----------|-------|
| `--space-xs` | 0.25rem (4px) |
| `--space-sm` | 0.5rem (8px) |
| `--space-md` | 1rem (16px) |
| `--space-lg` | 1.5rem (24px) |
| `--space-xl` | 2rem (32px) |
| `--space-2xl` | 3rem (48px) |

### Themes

Apply dark mode with `data-theme="dark"` attribute:

```html
<body data-theme="dark">
  <!-- Dark mode colors apply -->
</body>
```

---

## Utility Classes

### Spacing

- Margin: `.m-{xs|sm|md|lg|xl}`, `.mt-*`, `.mb-*`, `.mx-auto`
- Padding: `.p-{xs|sm|md|lg|xl}`, `.pt-*`, `.pb-*`

### Layout

- Flex: `.flex`, `.flex-col`, `.flex-wrap`, `.flex-1`
- Alignment: `.items-center`, `.items-start`, `.justify-center`, `.justify-between`
- Gap: `.gap-{xs|sm|md|lg}`
- Grid: `.grid`, `.grid-cols-2`, `.grid-cols-3`

### Typography

- Size: `.text-{xs|sm|base|lg|xl|2xl|3xl}`
- Color: `.text-muted`, `.text-danger`
- Align: `.text-center`, `.text-right`
- Style: `.text-uppercase`, `.font-medium`, `.font-bold`

### Display

- `.hidden`, `.block`, `.inline-block`
- `.hidden-mobile` (hidden < 768px)
- `.hidden-desktop` (hidden >= 769px)

### Borders

- `.border`, `.border-t`, `.border-b`, `.border-light`

### Other

- `.w-full`, `.max-w-sm`, `.max-w-md`, `.max-w-lg`
- `.truncate`, `.overflow-hidden`
- `.cursor-pointer`

---

## JavaScript Utilities

The shared library includes `js/components.js` with utility functions for interactive components:

| Function | Purpose |
|----------|---------|
| `toggleAccordion(id)` | Expand/collapse accordion content |
| `toggleDropdown(id)` | Open/close dropdown menu |
| `closeDropdown(id)` | Close specific dropdown |
| `toggleSourcePanel()` | Show/hide source details panel |
| `movePriority(btn, direction)` | Move priority item up/down, updates ranks automatically |
| `renderLineChart(containerId, data, options)` | Render SVG line chart with data points |

Dropdowns auto-close when clicking outside.

---

## Service Integration

### Dockerfile

```dockerfile
COPY shared/ ./shared/
COPY src/ ./src/
```

### FastAPI (main.py)

```python
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Mount entire shared directory (contains css/, js/, templates/)
app.mount("/static/shared", StaticFiles(directory="shared"), name="shared")
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Include shared templates in search path
templates = Jinja2Templates(directory=["src/templates", "shared/templates"])
```

### Base Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}{% endblock %}</title>
  <link rel="stylesheet" href="/static/shared/css/variables.css">
  <link rel="stylesheet" href="/static/shared/css/base.css">
  <link rel="stylesheet" href="/static/shared/css/components.css">
  <link rel="stylesheet" href="/static/shared/css/utilities.css">
</head>
<body>
  {% import "components.html" as ui %}
  {% block content %}{% endblock %}
  <script src="/static/shared/js/components.js"></script>
</body>
</html>
```
