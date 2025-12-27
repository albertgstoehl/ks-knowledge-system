# Unified Layout System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a unified layout system so all services share the same header, navigation, and content container patterns.

**Architecture:** A single `_layout.html` macro provides consistent structure: header with title, responsive navigation (header tabs on desktop, bottom nav on mobile, neither if no tabs), and a bordered content container. Services extend this with their content only.

**Tech Stack:** Jinja2 macros, shared CSS components, htmx for SPA navigation

---

## Current State Analysis

| Service | Header | Desktop Tabs | Bottom Nav | Content Container | Issues |
|---------|--------|--------------|------------|-------------------|--------|
| Balance | Shared macro | Yes | Yes (shared) | No container | Edge-to-edge content, inconsistent |
| Canvas | Custom HTML | Yes (now shared) | No | No container | Missing mobile nav |
| Bookmark | Custom HTML | Custom | Custom (black) | Bordered cards | 800+ lines inline CSS |
| Kasten | Custom HTML | No | No | No container | No navigation |

## Target State

All services use:
```jinja2
{% call layout.page(title="Balance", tabs=[("Timer", "/"), ("Log", "/log")], active="Timer") %}
  <!-- Page content only -->
{% endcall %}
```

Produces:
- Desktop: Header with title + tabs, content in bordered container
- Mobile: Header with title only, content in bordered container, bottom nav at bottom
- No tabs: Just header with title, content, no navigation elements

---

### Task 1: Create Layout Macro

**Files:**
- Create: `shared/templates/_layout.html`

**Step 1: Create the layout macro file**

```jinja2
{# ==========================================================================
   UNIFIED PAGE LAYOUT

   {% import "_layout.html" as layout %}

   {% call layout.page("Balance", [("Timer", "/"), ("Log", "/log")], "Timer") %}
     <div>Page content here</div>
   {% endcall %}

   {% call layout.page("Kasten") %}
     <div>No tabs - just title and content</div>
   {% endcall %}
   ========================================================================== #}
{% macro page(title, tabs=[], active=none) %}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{{ caller.title if caller.title else title }}</title>
  <!-- Shared component library -->
  <link rel="stylesheet" href="/static/shared/css/variables.css">
  <link rel="stylesheet" href="/static/shared/css/base.css">
  <link rel="stylesheet" href="/static/shared/css/components.css">
  <link rel="stylesheet" href="/static/shared/css/utilities.css">
  <!-- htmx for SPA navigation -->
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>
</head>
<body{% if tabs %} class="has-bottom-nav"{% endif %}>
  {% import "components.html" as ui %}

  {# Header: always show title, tabs only on desktop when provided #}
  <header class="header">
    <h1 class="header__title">{{ title }}</h1>
    {% if tabs %}
    <nav class="tabs header__tabs">
      {% for label, url in tabs %}
      <a href="{{ url }}"
         class="tab{% if label == active %} tab--active{% endif %}"
         hx-get="{{ url }}"
         hx-target="#main-content"
         hx-swap="innerHTML"
         hx-push-url="true">{{ label }}</a>
      {% endfor %}
    </nav>
    {% endif %}
  </header>

  {# Main content container #}
  <main id="main-content" class="content-container">
    {{ caller() }}
  </main>

  {# Bottom nav: only shown on mobile when tabs provided #}
  {% if tabs %}
  <nav class="bottom-nav">
    <div class="bottom-nav__links">
      {% for label, url in tabs %}
      <a href="{{ url }}"
         class="bottom-nav__link{% if label == active %} bottom-nav__link--active{% endif %}"
         hx-get="{{ url }}"
         hx-target="#main-content"
         hx-swap="innerHTML"
         hx-push-url="true">{{ label }}</a>
      {% endfor %}
    </div>
  </nav>
  {% endif %}

  {# Shared JS utilities #}
  <script src="/static/shared/js/components.js"></script>

  {# htmx navigation handler #}
  {% if tabs %}
  <script>
  document.body.addEventListener('htmx:afterSettle', function() {
    var path = window.location.pathname;
    var search = window.location.search;
    var fullPath = path + search;

    // Update header tabs
    document.querySelectorAll('.header__tabs .tab').forEach(function(tab) {
      var href = tab.getAttribute('href');
      tab.classList.toggle('tab--active', href === path || href === fullPath);
    });

    // Update bottom nav
    document.querySelectorAll('.bottom-nav__link').forEach(function(link) {
      var href = link.getAttribute('href');
      link.classList.toggle('bottom-nav__link--active', href === path || href === fullPath);
    });
  });
  </script>
  {% endif %}
</body>
</html>
{% endmacro %}
```

**Step 2: Verify file created**

Run: `cat shared/templates/_layout.html | head -20`
Expected: Shows the macro header

**Step 3: Commit**

```bash
git add shared/templates/_layout.html
git commit -m "feat: add unified page layout macro"
```

---

### Task 2: Add Content Container CSS

**Files:**
- Modify: `shared/css/components.css`

**Step 1: Add content container styles**

Add after the `.bottom-nav` styles (around line 290):

```css
/* ==========================================================================
   CONTENT CONTAINER
   ========================================================================== */

.content-container {
  border: 1px solid var(--color-border);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
  min-height: 50vh;
}

@media (max-width: 768px) {
  .content-container {
    border-left: none;
    border-right: none;
    padding: var(--space-md);
    margin-bottom: 0;
  }

  /* Add padding for bottom nav */
  body.has-bottom-nav .content-container {
    margin-bottom: calc(56px + var(--space-md));
  }
}
```

**Step 2: Verify styles applied**

Run: `grep -A 10 "CONTENT CONTAINER" shared/css/components.css`
Expected: Shows the content container styles

**Step 3: Commit**

```bash
git add shared/css/components.css
git commit -m "feat: add content container styles"
```

---

### Task 3: Fix Header Tabs Mobile Hiding

**Files:**
- Modify: `shared/css/components.css`

**Step 1: Update the mobile header tabs rule**

Find the existing rule (around line 282) and update it:

```css
@media (max-width: 768px) {
  .bottom-nav {
    display: block;
  }

  /* Hide header tabs on mobile when using bottom nav */
  .header__tabs {
    display: none;
  }

  /* Add padding for bottom nav */
  body.has-bottom-nav {
    padding-bottom: calc(56px + var(--safe-bottom));
  }
}
```

Note: We use `.header__tabs` class instead of `body:has(.bottom-nav) .header .tabs` for better browser support and specificity.

**Step 2: Verify change**

Run: `grep -B 2 -A 3 "header__tabs" shared/css/components.css`
Expected: Shows the updated rule

**Step 3: Commit**

```bash
git add shared/css/components.css
git commit -m "fix: header tabs hiding uses specific class"
```

---

### Task 4: Migrate Balance to Unified Layout

**Files:**
- Modify: `balance/src/templates/base.html`

**Step 1: Replace base.html with unified layout**

```jinja2
{% import "_layout.html" as layout %}

{% set tabs = [("Timer", "/"), ("Log", "/log"), ("Stats", "/stats"), ("Settings", "/settings")] %}

{% call layout.page("Balance", tabs, active_nav|default("Timer")|title) %}
  {% block content %}{% endblock %}
{% endcall %}

{% block head %}{% endblock %}
{% block scripts %}{% endblock %}
```

Wait - this won't work because we need to support blocks inside call. Let me revise the approach.

**Revised Step 1: Create a simpler base.html that uses shared patterns**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{% block title %}Balance{% endblock %}</title>
  <!-- Shared component library -->
  <link rel="stylesheet" href="/static/shared/css/variables.css">
  <link rel="stylesheet" href="/static/shared/css/base.css">
  <link rel="stylesheet" href="/static/shared/css/components.css">
  <link rel="stylesheet" href="/static/shared/css/utilities.css">
  <!-- Balance-specific styles -->
  <link rel="stylesheet" href="/static/css/style.css?v=5">
  <!-- htmx for SPA navigation -->
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>
  {% block head %}{% endblock %}
</head>
<body class="has-bottom-nav">
  {% import "components.html" as ui %}
  {% set tabs = [("Timer", "/"), ("Log", "/log"), ("Stats", "/stats"), ("Settings", "/settings")] %}

  <header class="header">
    <h1 class="header__title">Balance</h1>
    <nav class="tabs header__tabs">
      {% for label, url in tabs %}
      <a href="{{ url }}"
         class="tab{% if label == active_nav|default('Timer')|title %} tab--active{% endif %}"
         hx-get="{{ url }}"
         hx-target="#main-content"
         hx-swap="innerHTML"
         hx-push-url="true">{{ label }}</a>
      {% endfor %}
    </nav>
  </header>

  <main id="main-content" class="content-container">
    {% block content %}{% endblock %}
  </main>

  <nav class="bottom-nav">
    <div class="bottom-nav__links">
      {% for label, url in tabs %}
      <a href="{{ url }}"
         class="bottom-nav__link{% if label == active_nav|default('Timer')|title %} bottom-nav__link--active{% endif %}"
         hx-get="{{ url }}"
         hx-target="#main-content"
         hx-swap="innerHTML"
         hx-push-url="true">{{ label }}</a>
      {% endfor %}
    </div>
  </nav>

  <!-- Shared JS utilities -->
  <script src="/static/shared/js/components.js"></script>

  <!-- Core page scripts - loaded once -->
  <script src="/static/js/timer.js?v=5"></script>
  <script src="/static/js/log.js?v=3"></script>

  <script>
  // Update active tab state after htmx navigation
  document.body.addEventListener('htmx:afterSettle', function() {
    var path = window.location.pathname;
    document.querySelectorAll('.header__tabs .tab').forEach(function(tab) {
      tab.classList.toggle('tab--active', tab.getAttribute('href') === path);
    });
    document.querySelectorAll('.bottom-nav__link').forEach(function(link) {
      link.classList.toggle('bottom-nav__link--active', link.getAttribute('href') === path);
    });
    // Reinitialize page-specific JS
    if (path === '/' && typeof Balance !== 'undefined') Balance.init();
    if (path === '/log' && typeof LogPage !== 'undefined') LogPage.init();
  });
  </script>

  {% block scripts %}{% endblock %}
</body>
</html>
```

**Step 2: Verify the template renders**

Run: `docker compose -f docker-compose.dev.yml restart balance && sleep 2 && curl -s http://localhost:8005/ | grep -o "content-container"`
Expected: `content-container`

**Step 3: Commit**

```bash
git add balance/src/templates/base.html
git commit -m "refactor(balance): use unified layout pattern"
```

---

### Task 5: Update Balance Page Styles

**Files:**
- Modify: `balance/src/static/css/style.css`

**Step 1: Remove duplicate base styles, keep page-specific only**

The style.css should remove any styles that duplicate shared components (buttons, inputs, etc.) and only keep Balance-specific styles like timer display, session cards, etc.

Key removals:
- Remove `.btn` styles (use shared)
- Remove `.input` styles (use shared)
- Remove `.header` styles (use shared)
- Remove `.tabs` styles (use shared)
- Remove `.bottom-nav` styles (use shared)

Keep:
- Timer display (`.timer-display`)
- Session type buttons (`.type-btn`)
- Progress dots (`.dot`)
- Quick action buttons (`.quick-action`)
- Dark mode (`.dark-mode`)
- Break mode (`.break-mode`)

**Step 2: Test Balance pages visually**

Open http://localhost:8005/ and verify:
- Header shows "Balance" with tabs
- Content is in bordered container
- Bottom nav shows on mobile
- Timer page works
- Log page works

**Step 3: Commit**

```bash
git add balance/src/static/css/style.css
git commit -m "refactor(balance): remove duplicate styles, use shared"
```

---

### Task 6: Migrate Canvas to Unified Layout

**Files:**
- Modify: `canvas/src/templates/base.html`

**Step 1: Update canvas base.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{% block title %}Canvas{% endblock %}</title>
  <!-- Shared component library -->
  <link rel="stylesheet" href="/static/shared/css/variables.css">
  <link rel="stylesheet" href="/static/shared/css/base.css">
  <link rel="stylesheet" href="/static/shared/css/components.css">
  <link rel="stylesheet" href="/static/shared/css/utilities.css">
  <!-- htmx for SPA navigation -->
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>
  <style>
    /* Canvas-specific overrides only */
    html, body { height: 100%; }
    body { max-width: 1200px; margin: 0 auto; }
    .save-status { font-size: 0.875rem; color: var(--color-muted); }
    {% block extra_styles %}{% endblock %}
  </style>
</head>
<body class="has-bottom-nav">
  {% import "components.html" as ui %}
  {% set tabs = [("Draft", "/draft"), ("Workspace", "/workspace")] %}

  <header class="header">
    <h1 class="header__title">Canvas</h1>
    <nav class="tabs header__tabs">
      {% for label, url in tabs %}
      <a href="{{ url }}"
         class="tab{% if label == active_tab|title %} tab--active{% endif %}"
         hx-get="{{ url }}"
         hx-target="#main-content"
         hx-swap="innerHTML"
         hx-push-url="true">{{ label }}</a>
      {% endfor %}
    </nav>
  </header>

  <main id="main-content" class="content-container">
    {% block content %}{% endblock %}
  </main>

  <nav class="bottom-nav">
    <div class="bottom-nav__links">
      {% for label, url in tabs %}
      <a href="{{ url }}"
         class="bottom-nav__link{% if label == active_tab|title %} bottom-nav__link--active{% endif %}"
         hx-get="{{ url }}"
         hx-target="#main-content"
         hx-swap="innerHTML"
         hx-push-url="true">{{ label }}</a>
      {% endfor %}
    </div>
  </nav>

  <!-- Shared JS utilities -->
  <script src="/static/shared/js/components.js"></script>

  {% block scripts %}{% endblock %}

  <script>
  // Update active tab state after htmx navigation
  document.body.addEventListener('htmx:afterSettle', function() {
    var path = window.location.pathname;
    document.querySelectorAll('.header__tabs .tab').forEach(function(tab) {
      tab.classList.toggle('tab--active', tab.getAttribute('href') === path);
    });
    document.querySelectorAll('.bottom-nav__link').forEach(function(link) {
      link.classList.toggle('bottom-nav__link--active', link.getAttribute('href') === path);
    });
  });
  </script>
</body>
</html>
```

**Step 2: Test canvas**

Run: `docker compose -f docker-compose.dev.yml restart canvas && sleep 2`
Open http://localhost:8002/ and verify:
- Header shows "Canvas" with tabs
- Content in bordered container
- Bottom nav shows on mobile (390px width)

**Step 3: Commit**

```bash
git add canvas/src/templates/base.html
git commit -m "refactor(canvas): use unified layout pattern with bottom nav"
```

---

### Task 7: Migrate Bookmark-Manager to Unified Layout

**Files:**
- Modify: `bookmark-manager/src/templates/base.html`
- Create: `bookmark-manager/src/static/css/style.css`

**Step 1: Extract bookmark-specific styles to external file**

Create `bookmark-manager/src/static/css/style.css` with only bookmark-specific styles (conveyor layout, modal, feed styles, etc.) - not base styles.

**Step 2: Update base.html to use unified pattern**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{% block title %}Bookmarks{% endblock %}</title>
  <!-- Shared component library -->
  <link rel="stylesheet" href="/static/shared/css/variables.css">
  <link rel="stylesheet" href="/static/shared/css/base.css">
  <link rel="stylesheet" href="/static/shared/css/components.css">
  <link rel="stylesheet" href="/static/shared/css/utilities.css">
  <!-- Bookmark-specific styles -->
  <link rel="stylesheet" href="/static/css/style.css?v=1">
  <!-- htmx for SPA navigation -->
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>
</head>
<body class="has-bottom-nav">
  {% import "components.html" as ui %}
  {% set tabs = [("Feeds", "/ui/?view=feeds"), ("Inbox", "/ui/?view=inbox"), ("Thesis", "/ui/?view=thesis"), ("Pins", "/ui/?view=pins")] %}
  {% set current_view = request.query_params.get('view', 'inbox') %}

  <header class="header">
    <h1 class="header__title">Bookmarks</h1>
    <nav class="tabs header__tabs">
      {% for label, url in tabs %}
      <a href="{{ url }}"
         class="tab{% if label|lower == current_view %} tab--active{% endif %}"
         hx-get="{{ url }}"
         hx-target="#main-content"
         hx-swap="innerHTML"
         hx-push-url="true">{{ label }}</a>
      {% endfor %}
    </nav>
  </header>

  <main id="main-content" class="content-container">
    {% block content %}{% endblock %}
  </main>

  <nav class="bottom-nav">
    <div class="bottom-nav__links">
      {% for label, url in tabs %}
      <a href="{{ url }}"
         class="bottom-nav__link{% if label|lower == current_view %} bottom-nav__link--active{% endif %}"
         hx-get="{{ url }}"
         hx-target="#main-content"
         hx-swap="innerHTML"
         hx-push-url="true">{{ label }}</a>
      {% endfor %}
    </div>
  </nav>

  <!-- Shared JS utilities -->
  <script src="/static/shared/js/components.js"></script>

  <script>
  // Update active tab state after htmx navigation
  document.body.addEventListener('htmx:afterSettle', function() {
    var url = new URL(window.location.href);
    var view = url.searchParams.get('view') || 'inbox';
    document.querySelectorAll('.header__tabs .tab').forEach(function(tab) {
      var href = tab.getAttribute('href');
      tab.classList.toggle('tab--active', href.includes('view=' + view));
    });
    document.querySelectorAll('.bottom-nav__link').forEach(function(link) {
      var href = link.getAttribute('href');
      link.classList.toggle('bottom-nav__link--active', href.includes('view=' + view));
    });
  });
  </script>

  {% block scripts %}{% endblock %}
</body>
</html>
```

**Step 3: Update main.py to serve static CSS**

Ensure bookmark-manager serves `/static/css/` directory.

**Step 4: Test bookmark-manager**

Open http://localhost:8001/ and verify:
- Header shows "Bookmarks" with tabs
- Content in bordered container (same style as before)
- Bottom nav is white with black active state (like Balance)
- All views work: Feeds, Inbox, Thesis, Pins

**Step 5: Commit**

```bash
git add bookmark-manager/src/templates/base.html bookmark-manager/src/static/css/style.css
git commit -m "refactor(bookmark-manager): use unified layout, extract styles"
```

---

### Task 8: Migrate Kasten to Unified Layout

**Files:**
- Modify: `kasten/src/templates/base.html`

**Step 1: Update kasten base.html (no tabs version)**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{% block title %}Kasten{% endblock %}</title>
  <!-- Shared component library -->
  <link rel="stylesheet" href="/static/shared/css/variables.css">
  <link rel="stylesheet" href="/static/shared/css/base.css">
  <link rel="stylesheet" href="/static/shared/css/components.css">
  <link rel="stylesheet" href="/static/shared/css/utilities.css">
  <!-- htmx for SPA navigation -->
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>
  <style>
    body { max-width: 800px; margin: 0 auto; padding: 1rem; }
    {% block extra_styles %}{% endblock %}
  </style>
</head>
<body>
  {% import "components.html" as ui %}

  <header class="header">
    <h1 class="header__title"><a href="/" style="text-decoration:none">Kasten</a></h1>
  </header>

  <main id="main-content" class="content-container">
    {% block content %}{% endblock %}
  </main>

  <!-- Shared JS utilities -->
  <script src="/static/shared/js/components.js"></script>

  {% block scripts %}{% endblock %}
</body>
</html>
```

Note: Kasten has no tabs, so no `has-bottom-nav` class and no bottom nav element.

**Step 2: Test kasten**

Open http://localhost:8003/ and verify:
- Header shows "Kasten"
- Content in bordered container
- No bottom nav (correct - no tabs)

**Step 3: Commit**

```bash
git add kasten/src/templates/base.html
git commit -m "refactor(kasten): use unified layout pattern"
```

---

### Task 9: Final Testing

**Step 1: Restart all services**

```bash
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up --build -d
```

**Step 2: Visual comparison checklist**

Test each service at both desktop (1200px) and mobile (390px) widths:

| Service | Desktop Header | Desktop Tabs | Mobile Header | Mobile Bottom Nav | Content Container |
|---------|---------------|--------------|---------------|-------------------|-------------------|
| Balance (8005) | "Balance" | Timer/Log/Stats/Settings | "Balance" | Timer/Log/Stats/Settings | Bordered |
| Canvas (8002) | "Canvas" | Draft/Workspace | "Canvas" | Draft/Workspace | Bordered |
| Bookmark (8001) | "Bookmarks" | Feeds/Inbox/Thesis/Pins | "Bookmarks" | Feeds/Inbox/Thesis/Pins | Bordered |
| Kasten (8003) | "Kasten" | None | "Kasten" | None | Bordered |

**Step 3: htmx navigation test**

For each service with tabs, click through all tabs and verify:
- No full page reload
- URL updates
- Active tab highlighting updates
- Content swaps correctly

**Step 4: Commit final state**

```bash
git add -A
git commit -m "test: verify unified layout across all services"
```

---

## Summary

After completing all tasks:

1. **Consistent Pattern**: All services follow the same layout structure
2. **Responsive Navigation**: Header tabs on desktop, bottom nav on mobile
3. **No Tabs = No Nav**: Kasten demonstrates clean title-only header
4. **Content Container**: All content in bordered container
5. **Shared Styles**: No duplicated CSS across services
6. **htmx Built-in**: Navigation works without page reloads
