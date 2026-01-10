# UI Design Workflow

Process for designing new UI features that integrate with the existing component library.

## The Process

### 1. Brainstorm the Feature

Discuss the feature with the user. Clarify:
- What problem does it solve?
- What actions can the user take?
- What data does it display?
- Desktop and mobile requirements?

### 2. Audit Existing Components

Before creating anything new, check what exists:

```
docs/COMPONENT-LIBRARY.md    # Component API reference
shared/styleguide.html       # Visual preview (open in browser)
shared/css/components.css    # CSS implementation
shared/templates/components.html  # Jinja macros
```

Look for patterns that already solve the problem:
- **Modal** for dialogs, confirmations, forms
- **Action panel** for primary/secondary actions
- **Dropdown** for menus (becomes bottom sheet on mobile)
- **List** for selectable items
- **Tabs** for view switching
- **Bottom nav** for mobile navigation

### 3. Identify Gaps

If no existing component fits:
1. Check if an existing component can be extended
2. Propose a new component only if necessary
3. Design the new component to be reusable across services

### 4. Create Mockups

**Preferred: Add mockup route to the service.** This ensures CSS paths work correctly and the mockup is accessible via existing Docker setup.

**Dev-only route pattern (recommended):**

```python
# In main.py - gated by DEV_MODE env var
if os.getenv("DEV_MODE", "").lower() == "true":
    @app.get("/mockup", response_class=HTMLResponse)
    async def mockup_page(request: Request):
        """UI mockup for design iteration (dev only)."""
        return templates.TemplateResponse("mockup.html", {"request": request})
```

**Configuration:**
- Local dev: `export DEV_MODE=true` before starting service
- Production: Variable not set, route doesn't exist

**Mockup template:**

```html
<!-- templates/mockup.html -->
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="/static/shared/css/variables.css">
  <link rel="stylesheet" href="/static/shared/css/base.css">
  <link rel="stylesheet" href="/static/shared/css/components.css">
  <link rel="stylesheet" href="/static/shared/css/utilities.css">
  <style>
    /* Mockup-specific styles - nav between screens, etc. */
    .mockup-nav { display: flex; gap: 1rem; padding: 1rem; border-bottom: 2px solid var(--color-border); }
    .mockup-nav a { padding: 0.5rem 1rem; border: 1px solid var(--color-border); cursor: pointer; }
    .mockup-nav a.active { background: var(--color-text); color: var(--color-bg); }
    .screen { display: none; padding: 2rem; max-width: 600px; margin: 0 auto; }
    .screen.active { display: block; }
  </style>
</head>
<body>
  <nav class="mockup-nav">
    <a class="active" onclick="showScreen('screen1', this)">Screen 1</a>
    <a onclick="showScreen('screen2', this)">Screen 2</a>
    <a href="/" style="margin-left: auto;">Back to App</a>
  </nav>

  <div id="screen1" class="screen active">
    <!-- Screen 1 mockup content -->
  </div>

  <div id="screen2" class="screen">
    <!-- Screen 2 mockup content -->
  </div>

  <script src="/static/shared/js/components.js"></script>
  <script>
    function showScreen(id, link) {
      document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
      document.querySelectorAll('.mockup-nav a').forEach(a => a.classList.remove('active'));
      document.getElementById(id).classList.add('active');
      link.classList.add('active');
    }
  </script>
</body>
</html>
```

Access at `http://localhost:800X/mockup` (where X is the service port).

**To view mockups:**
1. Set `DEV_MODE=true` in your environment
2. Start/restart the service
3. Navigate to `/mockup`

Mockups should:
- Import shared CSS (`/static/shared/css/variables.css`, etc.)
- Use existing component classes (`.modal`, `.btn`, `.action-panel`)
- Show realistic content, not lorem ipsum
- Include both desktop (768px+) and mobile (375px) versions

### 5. Review with User

Access the mockup directly in the browser:
- **Service route:** `http://localhost:800X/mockup`
- **Temp folder:** `python3 -m http.server 8899` then `http://localhost:8899/`

Use Playwright to screenshot each view if needed. Present to user for feedback.

### 6. Iterate

Repeat steps 4-5 until the design is approved. Common iterations:
- Reuse more existing components
- Adjust layout for mobile
- Simplify actions
- Match existing patterns more closely

### 7. Document Changes

**New components MUST be added to the shared library.** Do not create service-specific CSS.

If new components were created:
1. Add CSS to `shared/css/components.css` (required)
2. Add Jinja macro to `shared/templates/components.html`
3. Update `docs/COMPONENT-LIBRARY.md` with API reference
4. Update `shared/styleguide.html` with visual examples

All four steps are required for any new reusable component.

## Key Principles

**Reuse first.** Every new component adds maintenance burden. Prefer extending existing patterns.

**Mobile and desktop together.** Design both from the start. Components should adapt, not duplicate.

**Realistic content.** Use real data in mockups. Abstract placeholders hide layout problems.

**Black and white.** The design system uses monochrome with black borders. No colors except for errors.

**Shared component library.** All services import from `shared/`. Changes propagate everywhere.

## Component Patterns Reference

| Need | Use |
|------|-----|
| Confirmation dialog | `.modal` with `.modal__footer` buttons |
| Action buttons | `.action-panel` (becomes fixed bar on mobile) |
| Selection from list | `.dropdown` (becomes bottom sheet on mobile) |
| Search + select | `.modal` with search input and `.modal__list` |
| Tab navigation | `.tabs` in header, `.bottom-nav` on mobile |
| Progress indicator | `.progress` bar |
| Empty state | `.empty-state` with optional action |
