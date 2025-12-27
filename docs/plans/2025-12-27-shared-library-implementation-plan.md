# Shared Component Library Migration - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate all services to use shared component library with htmx SPA navigation.

**Architecture:** Extend shared/ with new components, update Dockerfiles to use root context, migrate each service's templates to use shared components and htmx partials for tab switching.

**Tech Stack:** Python/FastAPI, Jinja2, htmx, CSS (brutalist design tokens)

---

## Phase 1: Extend Shared Library

### Task 1: Add New CSS Components

**Files:**
- Modify: `shared/css/components.css`

**Step 1: Read current components.css**

Read `shared/css/components.css` to understand existing structure.

**Step 2: Add accordion component**

```css
/* Accordion */
.accordion {
  border: 1px solid var(--color-border);
  margin-bottom: var(--space-sm);
}

.accordion__header {
  display: flex;
  align-items: center;
  padding: var(--space-sm) var(--space-md);
  cursor: pointer;
  background: var(--color-hover);
  gap: var(--space-sm);
}

.accordion__header:hover {
  background: var(--color-border-light);
}

.accordion__toggle {
  font-size: var(--font-size-sm);
}

.accordion__title {
  flex: 1;
  font-weight: 500;
}

.accordion__count {
  color: var(--color-muted);
  font-size: var(--font-size-sm);
}

.accordion__content {
  display: none;
}

.accordion__content--open {
  display: block;
}
```

**Step 3: Add dropdown menu component**

```css
/* Dropdown Menu */
.dropdown {
  position: relative;
}

.dropdown__menu {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  z-index: 10;
}

.dropdown__menu--open {
  display: block;
}

.dropdown__item {
  display: block;
  width: 100%;
  padding: var(--space-sm) var(--space-md);
  border: none;
  background: var(--color-bg);
  font-family: inherit;
  font-size: var(--font-size-base);
  text-align: left;
  cursor: pointer;
}

.dropdown__item:hover {
  background: var(--color-hover);
}

.dropdown__item + .dropdown__item {
  border-top: 1px solid var(--color-border-light);
}

/* Mobile: dropdown becomes bottom sheet */
@media (max-width: 768px) {
  .dropdown__menu {
    position: fixed;
    top: auto;
    bottom: 0;
    left: 0;
    right: 0;
    border: none;
    border-top: 2px solid var(--color-border);
    z-index: 200;
  }

  .dropdown__item {
    min-height: 56px;
    display: flex;
    align-items: center;
    font-size: var(--font-size-lg);
  }

  .dropdown__backdrop {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 199;
  }

  .dropdown__backdrop--open {
    display: block;
  }
}
```

**Step 4: Add video embed component**

```css
/* Video Embed */
.video-embed {
  position: relative;
  width: 100%;
  padding-bottom: 56.25%; /* 16:9 */
  background: var(--color-border);
  margin-bottom: var(--space-sm);
}

.video-embed__iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: 1px solid var(--color-border);
}

.video-embed__status {
  font-size: var(--font-size-sm);
  color: var(--color-muted);
  margin-bottom: var(--space-md);
}
```

**Step 5: Add action panel component**

```css
/* Action Panel */
.action-panel {
  border: 1px solid var(--color-border);
  padding: var(--space-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  align-self: start;
}

.action-panel__row {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

@media (max-width: 768px) {
  .action-panel {
    position: fixed;
    bottom: 56px; /* Above bottom-nav */
    left: 0;
    right: 0;
    background: var(--color-bg);
    border: none;
    border-top: 2px solid var(--color-border);
    padding: var(--space-sm);
    z-index: 99;
  }

  .action-panel__row {
    flex-direction: row;
  }

  .action-panel__row > * {
    flex: 1;
  }

  .action-panel .btn {
    min-height: 48px;
    font-size: var(--font-size-sm);
  }

  .action-panel .btn--primary {
    width: 100%;
    order: -1;
  }
}
```

**Step 6: Add nav bar component**

```css
/* Nav Bar (back/forward navigation) */
.nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-sm) 0;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--space-md);
}

.nav-bar__btn {
  padding: var(--space-sm) var(--space-md);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  cursor: pointer;
  font-family: inherit;
  text-decoration: none;
}

.nav-bar__btn:hover {
  background: var(--color-hover);
}

.nav-bar__btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
```

**Step 7: Add source panel component**

```css
/* Source Panel */
.source-panel {
  padding: var(--space-md) 0;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--space-md);
}

.source-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.source-panel__info {
  flex: 1;
}

.source-panel__label {
  font-weight: normal;
}

.source-panel__title {
  font-weight: bold;
}

.source-panel__toggle {
  background: none;
  border: none;
  font-family: inherit;
  font-size: var(--font-size-lg);
  cursor: pointer;
  padding: 0;
}

.source-panel__toggle:hover {
  text-decoration: underline;
}

.source-panel__meta {
  font-size: var(--font-size-sm);
  color: var(--color-muted);
  margin-top: var(--space-xs);
}

.source-panel__details {
  margin-top: var(--space-md);
}

.source-panel__description {
  margin: 0 0 var(--space-sm) 0;
}

.source-panel__link {
  color: var(--color-text);
  text-decoration: underline;
}

.source-panel__link:hover {
  text-decoration: none;
}
```

**Step 8: Add toolbar and status bar components**

```css
/* Toolbar */
.toolbar {
  display: flex;
  gap: var(--space-sm);
  padding: var(--space-sm) 0;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--space-sm);
}

.toolbar__spacer {
  flex: 1;
}

.toolbar__info {
  color: var(--color-muted);
  font-size: var(--font-size-sm);
  display: flex;
  align-items: center;
}

/* Status Bar */
.status-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: var(--space-sm) 0;
  gap: var(--space-md);
}

.status-bar__text {
  font-size: var(--font-size-sm);
  color: var(--color-muted);
}

.status-bar__hint {
  font-size: var(--font-size-xs);
  color: var(--color-muted);
}
```

**Step 9: Add badge component**

```css
/* Badge */
.badge {
  display: inline-block;
  font-size: var(--font-size-xs);
  font-weight: 400;
  color: var(--color-muted);
  margin-right: var(--space-xs);
}
```

**Step 10: Add layout components**

```css
/* Layout 2-Column */
.layout-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-xl);
  min-height: 70vh;
  align-items: start;
}

@media (max-width: 768px) {
  .layout-2col {
    grid-template-columns: 1fr;
  }
}

/* Layout 2-Column Sidebar (wider main, narrower sidebar) */
.layout-2col--sidebar {
  grid-template-columns: 1fr 250px;
  gap: var(--space-md);
}

@media (max-width: 768px) {
  .layout-2col--sidebar {
    grid-template-columns: 1fr;
  }
}

/* Main content wrapper for htmx */
.main-content {
  /* No special styles needed, just a target for htmx */
}

/* Conveyor belt specific (bookmark-manager) */
.conveyor-item {
  border: 1px solid var(--color-border);
  padding: var(--space-lg);
  min-width: 0;
  overflow: hidden;
}

.conveyor-item__title {
  font-size: var(--font-size-xl);
  font-weight: 500;
  margin-bottom: var(--space-sm);
}

.conveyor-item__meta {
  color: var(--color-muted);
  margin-bottom: var(--space-md);
}

.conveyor-item__description {
  line-height: 1.6;
  margin-bottom: var(--space-lg);
  word-break: break-word;
  overflow-wrap: break-word;
}

/* Next up queue */
.next-up {
  margin-top: var(--space-lg);
  padding-top: var(--space-md);
  border-top: 1px solid var(--color-border-light);
}

.next-up__header {
  font-size: var(--font-size-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: var(--space-sm);
  color: var(--color-muted);
}

.next-up__item {
  padding: var(--space-sm) 0;
  font-size: var(--font-size-sm);
  color: var(--color-muted);
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-sm);
}

.next-up__item:hover {
  color: var(--color-text);
}

.next-up__title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.next-up__timer {
  flex-shrink: 0;
  font-size: var(--font-size-xs);
}

/* Expiry timer colors */
.timer--urgent {
  color: var(--color-danger);
}

.timer--warning {
  color: var(--color-text);
}

.timer--normal {
  color: var(--color-muted);
}
```

**Step 11: Commit**

```bash
git add shared/css/components.css
git commit -m "feat(shared): add new CSS components for migration"
```

---

### Task 2: Add New Jinja2 Macros

**Files:**
- Modify: `shared/templates/components.html`

**Step 1: Read current components.html**

Read `shared/templates/components.html` to understand existing macros.

**Step 2: Add accordion macro**

```html
{% macro accordion(title, id, count=none, open=false) %}
<div class="accordion" data-accordion-id="{{ id }}">
  <div class="accordion__header" onclick="toggleAccordion('{{ id }}')">
    <span class="accordion__toggle" id="toggle-{{ id }}">{{ '▼' if open else '▶' }}</span>
    <span class="accordion__title">{{ title }}</span>
    {% if count is not none %}
    <span class="accordion__count">({{ count }})</span>
    {% endif %}
    {{ caller() if caller else '' }}
  </div>
  <div class="accordion__content {{ 'accordion__content--open' if open else '' }}" id="content-{{ id }}">
    {{ caller() if caller else '' }}
  </div>
</div>
{% endmacro %}
```

**Step 3: Add dropdown macro**

```html
{% macro dropdown(trigger_text, id) %}
<div class="dropdown">
  <button class="btn" onclick="toggleDropdown('{{ id }}')">{{ trigger_text }} ▾</button>
  <div class="dropdown__menu" id="dropdown-{{ id }}">
    {{ caller() }}
  </div>
  <div class="dropdown__backdrop" id="backdrop-{{ id }}" onclick="closeDropdown('{{ id }}')"></div>
</div>
{% endmacro %}

{% macro dropdown_item(label, onclick=none, href=none) %}
{% if href %}
<a href="{{ href }}" class="dropdown__item">{{ label }}</a>
{% else %}
<button class="dropdown__item" onclick="{{ onclick }}">{{ label }}</button>
{% endif %}
{% endmacro %}
```

**Step 4: Add video embed macro**

```html
{% macro video_embed(video_id, start=0, id="yt-player") %}
<div class="video-embed">
  <iframe id="{{ id }}"
    src="https://www.youtube-nocookie.com/embed/{{ video_id }}?start={{ start }}&enablejsapi=1"
    frameborder="0"
    allowfullscreen
    allow="autoplay; fullscreen"
    class="video-embed__iframe">
  </iframe>
</div>
{% endmacro %}
```

**Step 5: Add action panel macro**

```html
{% macro action_panel(id="action-panel") %}
<aside class="action-panel" id="{{ id }}">
  {{ caller() }}
</aside>
{% endmacro %}

{% macro action_row() %}
<div class="action-panel__row">
  {{ caller() }}
</div>
{% endmacro %}
```

**Step 6: Add nav bar macro**

```html
{% macro nav_bar(center_content=none) %}
<nav class="nav-bar">
  <button class="nav-bar__btn" onclick="history.back()" title="Back">←</button>
  {% if center_content %}
  {{ center_content }}
  {% else %}
  {{ caller() if caller else '' }}
  {% endif %}
  <button class="nav-bar__btn" onclick="history.forward()" title="Forward">→</button>
</nav>
{% endmacro %}
```

**Step 7: Add source panel macro**

```html
{% macro source_panel(source) %}
{% if source %}
<section class="source-panel" id="source-panel">
  <div class="source-panel__header">
    <div class="source-panel__info">
      <span class="source-panel__label">Source:</span>
      <span class="source-panel__title">{{ source.title or 'Untitled' }}</span>
    </div>
    <button class="source-panel__toggle" onclick="toggleSourcePanel()" id="source-toggle">[+]</button>
  </div>
  <div class="source-panel__meta">{{ source.domain }} · {{ source.archived_at.strftime('%b %d') if source.archived_at else '' }}</div>
  <div class="source-panel__details" id="source-details" style="display: none;">
    {% if source.description %}
    <p class="source-panel__description">{{ source.description }}</p>
    {% endif %}
    <a href="{{ source.url }}" target="_blank" class="source-panel__link">Open original</a>
  </div>
</section>
{% endif %}
{% endmacro %}
```

**Step 8: Add toolbar and status bar macros**

```html
{% macro toolbar() %}
<div class="toolbar">
  {{ caller() }}
</div>
{% endmacro %}

{% macro toolbar_spacer() %}
<span class="toolbar__spacer"></span>
{% endmacro %}

{% macro toolbar_info(text) %}
<span class="toolbar__info">{{ text }}</span>
{% endmacro %}

{% macro status_bar(status_text, hint=none, status_id="save-status") %}
<div class="status-bar">
  <span class="status-bar__text" id="{{ status_id }}">{{ status_text }}</span>
  {% if hint %}
  <span class="status-bar__hint">{{ hint }}</span>
  {% endif %}
</div>
{% endmacro %}
```

**Step 9: Add badge macro**

```html
{% macro badge(type) %}
<span class="badge">[{{ type | upper }}]</span>
{% endmacro %}
```

**Step 10: Add layout macros**

```html
{% macro layout_2col(sidebar=false) %}
<div class="layout-2col {{ 'layout-2col--sidebar' if sidebar else '' }}">
  {{ caller() }}
</div>
{% endmacro %}

{% macro conveyor_item() %}
<section class="conveyor-item">
  {{ caller() }}
</section>
{% endmacro %}

{% macro next_up(items) %}
<div class="next-up">
  <div class="next-up__header">Next Up</div>
  {% for item in items %}
  <div class="next-up__item" data-id="{{ item.id }}">
    {% if item.video_id %}<span class="badge">[VID]</span>{% endif %}
    {% if item.pinned %}<span class="badge">[PIN]</span>{% endif %}
    {% if item.is_thesis %}<span class="badge">[DOC]</span>{% endif %}
    <span class="next-up__title">{{ item.title or 'Untitled' }}</span>
    {% if item.expires_at %}
    <span class="next-up__timer" data-expires="{{ item.expires_at.isoformat() }}Z">{{ item.expires_at | expiry }}</span>
    {% endif %}
  </div>
  {% endfor %}
</div>
{% endmacro %}
```

**Step 11: Update bottom_nav with htmx**

Find and update the existing bottom_nav macro:

```html
{% macro bottom_nav(items, active=none) %}
<nav class="bottom-nav">
  <div class="bottom-nav__links">
    {% for label, href in items %}
    <a href="{{ href }}"
       class="bottom-nav__link {{ 'bottom-nav__link--active' if active == label else '' }}"
       hx-get="{{ href }}"
       hx-target="#main-content"
       hx-swap="innerHTML"
       hx-push-url="true">{{ label }}</a>
    {% endfor %}
  </div>
</nav>
{% endmacro %}
```

**Step 12: Commit**

```bash
git add shared/templates/components.html
git commit -m "feat(shared): add new Jinja2 macros for migration"
```

---

### Task 3: Add Shared JavaScript Utilities

**Files:**
- Create: `shared/js/components.js`

**Step 1: Create shared JS file with component utilities**

```javascript
// Accordion
function toggleAccordion(id) {
  const content = document.getElementById('content-' + id);
  const toggle = document.getElementById('toggle-' + id);
  const isOpen = content.classList.contains('accordion__content--open');

  if (isOpen) {
    content.classList.remove('accordion__content--open');
    toggle.textContent = '▶';
  } else {
    content.classList.add('accordion__content--open');
    toggle.textContent = '▼';
  }
}

// Dropdown
function toggleDropdown(id) {
  const menu = document.getElementById('dropdown-' + id);
  const backdrop = document.getElementById('backdrop-' + id);
  menu.classList.toggle('dropdown__menu--open');
  if (backdrop) backdrop.classList.toggle('dropdown__backdrop--open');
}

function closeDropdown(id) {
  const menu = document.getElementById('dropdown-' + id);
  const backdrop = document.getElementById('backdrop-' + id);
  menu.classList.remove('dropdown__menu--open');
  if (backdrop) backdrop.classList.remove('dropdown__backdrop--open');
}

// Source panel
function toggleSourcePanel() {
  const details = document.getElementById('source-details');
  const toggle = document.getElementById('source-toggle');
  if (details.style.display === 'none') {
    details.style.display = 'block';
    toggle.textContent = '[-]';
  } else {
    details.style.display = 'none';
    toggle.textContent = '[+]';
  }
}

// Close dropdowns on outside click
document.addEventListener('click', function(e) {
  if (!e.target.closest('.dropdown')) {
    document.querySelectorAll('.dropdown__menu--open').forEach(menu => {
      const id = menu.id.replace('dropdown-', '');
      closeDropdown(id);
    });
  }
});
```

**Step 2: Commit**

```bash
git add shared/js/components.js
git commit -m "feat(shared): add JavaScript utilities for components"
```

---

## Phase 2: Infrastructure Updates

### Task 4: Update rebuild-k3s.sh

**Files:**
- Modify: `scripts/rebuild-k3s.sh`

**Step 1: Update build command to use root context for all services**

Change lines 44-51 from:

```bash
for svc in "${selected[@]}"; do
    echo "=== Building $svc ==="
    if [[ "$svc" == "balance" ]]; then
        # Balance needs root context for shared/ directory
        docker build -f "$svc/Dockerfile" -t "$svc:latest" .
    else
        docker build -t "$svc:latest" "./$svc"
    fi
```

To:

```bash
for svc in "${selected[@]}"; do
    echo "=== Building $svc ==="
    # All services use root context for shared/ directory
    docker build -f "$svc/Dockerfile" -t "$svc:latest" .
```

**Step 2: Commit**

```bash
git add scripts/rebuild-k3s.sh
git commit -m "fix(scripts): all services build from root context for shared/"
```

---

### Task 5: Update bookmark-manager Dockerfile

**Files:**
- Modify: `bookmark-manager/Dockerfile`

**Step 1: Update Dockerfile to use root context and copy shared**

Update the COPY commands to use service prefix and add shared:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js for Claude CLI
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    cron \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Copy requirements (with service prefix for root context)
COPY bookmark-manager/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application and shared library
COPY bookmark-manager/src/ ./src/
COPY bookmark-manager/scripts/ ./scripts/
COPY shared/ ./shared/

# Create data directory
RUN mkdir -p /app/data /app/data/backups

# Setup cron for daily backups and feed jobs
RUN (echo "0 2 * * * /app/scripts/backup_cron.sh"; \
     echo "0 */2 * * * cd /app && /usr/local/bin/python scripts/feed_refresh.py >> /var/log/feed_refresh.log 2>&1"; \
     echo "0 * * * * cd /app && /usr/local/bin/python scripts/feed_cleanup.py >> /var/log/feed_cleanup.log 2>&1") | crontab -

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["sh", "-c", "cron && uvicorn src.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
```

**Step 2: Commit**

```bash
git add bookmark-manager/Dockerfile
git commit -m "fix(bookmark-manager): use root context, add shared/"
```

---

### Task 6: Update canvas Dockerfile

**Files:**
- Modify: `canvas/Dockerfile`

**Step 1: Update Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY canvas/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY canvas/src/ src/
COPY canvas/static/ static/
COPY shared/ ./shared/

RUN mkdir -p data

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
```

**Step 2: Commit**

```bash
git add canvas/Dockerfile
git commit -m "fix(canvas): use root context, add shared/"
```

---

### Task 7: Update kasten Dockerfile

**Files:**
- Modify: `kasten/Dockerfile`

**Step 1: Update Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY kasten/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kasten/src/ src/
COPY kasten/static/ static/
COPY shared/ ./shared/

RUN mkdir -p data

ENV NOTES_PATH=/app/notes

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
```

**Step 2: Commit**

```bash
git add kasten/Dockerfile
git commit -m "fix(kasten): use root context, add shared/"
```

---

## Phase 3: Migrate Services

### Task 8: Update bookmark-manager main.py

**Files:**
- Modify: `bookmark-manager/src/main.py`

**Step 1: Add static file mounts for shared**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from src.services.background_jobs import BackgroundJobService
from src.routers import bookmarks, search, backup, ui, feeds, canvas
import os

app = FastAPI(
    title="Bookmark Manager API",
    description="Minimal bookmark management with semantic search",
    version="0.1.0"
)

# Mount shared CSS and JS
app.mount("/static/shared", StaticFiles(directory="shared/css"), name="shared-css")
app.mount("/static/shared/js", StaticFiles(directory="shared/js"), name="shared-js")

# Initialize services
jina_api_key = os.getenv("JINA_API_KEY")
oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
background_job_service = BackgroundJobService(
    jina_api_key=jina_api_key,
    oauth_token=oauth_token
)

@app.on_event("startup")
async def startup():
    from src.database import init_db
    await init_db()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return RedirectResponse(url="/ui/")

# Register routers
app.include_router(bookmarks.router)
app.include_router(search.router)
app.include_router(backup.router)
app.include_router(ui.router)
app.include_router(feeds.router)
app.include_router(canvas.router)
```

**Step 2: Commit**

```bash
git add bookmark-manager/src/main.py
git commit -m "feat(bookmark-manager): mount shared static files"
```

---

### Task 9: Update bookmark-manager UI router for shared templates

**Files:**
- Modify: `bookmark-manager/src/routers/ui.py`

**Step 1: Update templates path to include shared**

Change:
```python
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
```

To:
```python
templates_dir = Path(__file__).parent.parent / "templates"
shared_templates_dir = Path(__file__).parent.parent.parent / "shared" / "templates"
templates = Jinja2Templates(directory=[str(templates_dir), str(shared_templates_dir)])
```

**Step 2: Add htmx partial detection to routes**

Update the ui_index function to detect htmx requests:

```python
@router.get("/", response_class=HTMLResponse)
async def ui_index(
    request: Request,
    view: str = "inbox",
    q: str = None,
    filter: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
):
    """Main UI page"""
    # ... existing query logic ...

    context = {
        "request": request,
        "bookmarks": bookmarks,
        "view": view,
        "query": q,
        "filter": filter,
        "inbox_count": inbox_count,
        "canvas_url": CANVAS_EXTERNAL_URL
    }

    # htmx request → return partial
    if request.headers.get("HX-Request"):
        if view == "feeds":
            return templates.TemplateResponse("_content_feeds.html", {**context, "feeds": feeds_with_items})
        return templates.TemplateResponse("_content_index.html", context)

    # Full page request
    if view == "feeds":
        return templates.TemplateResponse("feeds.html", {**context, "feeds": feeds_with_items})
    return templates.TemplateResponse("index.html", context)
```

**Step 3: Commit**

```bash
git add bookmark-manager/src/routers/ui.py
git commit -m "feat(bookmark-manager): add shared templates, htmx partial detection"
```

---

### Task 10: Create bookmark-manager base.html with shared components

**Files:**
- Modify: `bookmark-manager/src/templates/base.html`
- Create: `bookmark-manager/src/static/css/style.css`

**Step 1: Create service-specific CSS file**

Move the unique bookmark-manager styles to `src/static/css/style.css` (conveyor belt, video player, etc).

**Step 2: Update base.html to use shared**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>{% block title %}Bookmarks{% endblock %}</title>
    <!-- Shared component library -->
    <link rel="stylesheet" href="/static/shared/variables.css">
    <link rel="stylesheet" href="/static/shared/base.css">
    <link rel="stylesheet" href="/static/shared/components.css">
    <link rel="stylesheet" href="/static/shared/utilities.css">
    <!-- Service-specific styles -->
    <link rel="stylesheet" href="/static/css/style.css">
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    {% block head %}{% endblock %}
</head>
<body>
    {% import "components.html" as ui %}

    {{ ui.header("Bookmarks", [
        ("Feeds", "/ui/?view=feeds"),
        ("Inbox", "/ui/?view=inbox"),
        ("Thesis", "/ui/?view=thesis"),
        ("Pins", "/ui/?view=pins")
    ], active=view|default("inbox")|title) }}

    <main id="main-content">
        {% block content %}{% endblock %}
    </main>

    {{ ui.bottom_nav([
        ("Feeds", "/ui/?view=feeds"),
        ("Inbox", "/ui/?view=inbox"),
        ("Thesis", "/ui/?view=thesis"),
        ("Pins", "/ui/?view=pins")
    ], active=view|default("inbox")|title) }}

    <!-- Shared JS utilities -->
    <script src="/static/shared/js/components.js"></script>

    {% block scripts %}{% endblock %}
</body>
</html>
```

**Step 3: Commit**

```bash
git add bookmark-manager/src/templates/base.html bookmark-manager/src/static/css/style.css
git commit -m "feat(bookmark-manager): migrate to shared component library"
```

---

### Task 11-15: Create content partials for bookmark-manager

Create `_content_index.html`, `_content_feeds.html` partials and update index.html/feeds.html to include them.

(Similar pattern - extract content block, create partial, update main template to include partial)

---

### Task 16-20: Migrate canvas

Similar pattern:
- Update main.py with shared mounts
- Update templates path in ui router
- Create base.html with shared components
- Create content partials
- Extract service-specific CSS

---

### Task 21-25: Migrate kasten

Similar pattern (no bottom_nav, no htmx partials):
- Update main.py with shared mounts
- Update templates path
- Create base.html with shared header only
- Extract service-specific CSS

---

### Task 26: Update Balance with htmx partials

Balance already uses shared library, just add htmx partials:
- Create `_content_*.html` partials
- Update router to detect HX-Request
- Test tab switching

---

### Task 27: Final testing

**Step 1: Rebuild all services**

```bash
./scripts/rebuild-k3s.sh
# Select: a (all)
```

**Step 2: Test each service**

- Verify shared CSS loads
- Test tab navigation (no full page reload)
- Test mobile bottom nav
- Test all components render correctly

**Step 3: Commit any fixes**

---

## Verification Checklist

- [ ] All services build successfully from root context
- [ ] Shared CSS loads on all services
- [ ] Header component renders correctly
- [ ] Bottom nav works on Balance, Bookmark, Canvas
- [ ] Tab switching uses htmx (no full reload)
- [ ] Mobile layout works
- [ ] All existing functionality preserved
