# Component Library Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract duplicated CSS from services into shared component library

**Architecture:** Add new BEM-named components to shared/css/components.css, update styleguide.html with examples, then refactor services to use shared components

**Tech Stack:** CSS, HTML, Jinja2

---

## Task 1: Extract .view-header Component

**Files:**
- Modify: `shared/css/components.css` (append at end)
- Modify: `shared/styleguide.html` (add example)

**Step 1: Add CSS to components.css**

Append to `shared/css/components.css`:

```css
/* ==========================================================================
   VIEW HEADER
   Section header with title and count (e.g., "INBOX (27)")
   ========================================================================== */

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.view-header__title {
  font-size: 1rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.view-header__count {
  font-size: 0.875rem;
  color: var(--color-muted);
}
```

**Step 2: Add example to styleguide.html**

Find the `<!-- Empty State -->` section and add BEFORE it:

```html
<!-- View Header -->
<section>
  <h2>View Header</h2>
  <p>Section header with title and optional count.</p>

  <div class="example">
    <div class="view-header">
      <span class="view-header__title">INBOX (27)</span>
    </div>
  </div>

  <div class="example">
    <div class="view-header">
      <span class="view-header__title">THESIS (12)</span>
      <span class="view-header__count">3 unread</span>
    </div>
  </div>
</section>
```

**Step 3: Commit**

```bash
git add shared/css/components.css shared/styleguide.html
git commit -m "feat(shared): add .view-header component"
```

---

## Task 2: Extract .detail-panel Component

**Files:**
- Modify: `shared/css/components.css` (append at end)
- Modify: `shared/styleguide.html` (add example)

**Step 1: Add CSS to components.css**

Append to `shared/css/components.css`:

```css
/* ==========================================================================
   DETAIL PANEL
   Right-side panel showing selected item details
   ========================================================================== */

.detail-panel {
  border: 1px solid var(--color-border);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.detail-panel__header {
  border-bottom: 1px solid var(--color-border-light);
  padding-bottom: var(--space-md);
}

.detail-panel__title {
  font-size: 1.25rem;
  font-weight: 500;
  margin-bottom: var(--space-xs);
}

.detail-panel__meta {
  color: var(--color-muted);
  font-size: 0.875rem;
}

.detail-panel__content {
  flex: 1;
  line-height: 1.6;
}

.detail-panel__actions {
  display: flex;
  gap: var(--space-sm);
  flex-wrap: wrap;
  padding-top: var(--space-md);
  border-top: 1px solid var(--color-border-light);
}

.detail-panel__empty {
  padding: 2rem;
  text-align: center;
  color: var(--color-muted);
}

@media (max-width: 768px) {
  .detail-panel {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 56px;
    background: var(--color-bg);
    z-index: 100;
    overflow-y: auto;
    display: none;
  }

  .detail-panel.active {
    display: flex;
  }

  .detail-panel__actions {
    flex-direction: column;
  }

  .detail-panel__actions .btn {
    width: 100%;
    min-height: 48px;
  }
}
```

**Step 2: Add example to styleguide.html**

Add after View Header section:

```html
<!-- Detail Panel -->
<section>
  <h2>Detail Panel</h2>
  <p>Panel showing selected item details. Hidden on mobile until activated.</p>

  <div class="example">
    <div class="detail-panel" style="max-width: 400px;">
      <div class="detail-panel__header">
        <div class="detail-panel__title">Article Title Here</div>
        <div class="detail-panel__meta">example.com · 2 hours ago</div>
      </div>
      <div class="detail-panel__content">
        This is the article description or content preview. It can be multiple lines of text.
      </div>
      <div class="detail-panel__actions">
        <button class="btn btn--primary">Open</button>
        <button class="btn">Archive</button>
        <button class="btn btn--danger">Delete</button>
      </div>
    </div>
  </div>

  <div class="example">
    <div class="detail-panel" style="max-width: 400px;">
      <div class="detail-panel__empty">Select an item to view details</div>
    </div>
  </div>
</section>
```

**Step 3: Commit**

```bash
git add shared/css/components.css shared/styleguide.html
git commit -m "feat(shared): add .detail-panel component"
```

---

## Task 3: Extract .layout--list-detail Component

**Files:**
- Modify: `shared/css/components.css` (append at end)
- Modify: `shared/styleguide.html` (add example)

**Step 1: Add CSS to components.css**

Append to `shared/css/components.css`:

```css
/* ==========================================================================
   LIST-DETAIL LAYOUT
   Two-column layout with list on left, detail panel on right
   ========================================================================== */

.layout--list-detail {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  min-height: 70vh;
  align-items: start;
}

@media (max-width: 768px) {
  .layout--list-detail {
    grid-template-columns: 1fr;
    min-height: auto;
  }
}
```

**Step 2: Add example to styleguide.html**

Add after Detail Panel section:

```html
<!-- List-Detail Layout -->
<section>
  <h2>List-Detail Layout</h2>
  <p>Two-column layout with list and detail panel. Stacks on mobile.</p>

  <div class="example">
    <div class="layout--list-detail" style="min-height: 200px;">
      <div class="list" style="border: 1px solid var(--color-border);">
        <div class="list__item list__item--selected">Item 1</div>
        <div class="list__item">Item 2</div>
        <div class="list__item">Item 3</div>
      </div>
      <div class="detail-panel">
        <div class="detail-panel__header">
          <div class="detail-panel__title">Item 1</div>
        </div>
        <div class="detail-panel__content">Details for item 1</div>
      </div>
    </div>
  </div>
</section>
```

**Step 3: Commit**

```bash
git add shared/css/components.css shared/styleguide.html
git commit -m "feat(shared): add .layout--list-detail component"
```

---

## Task 4: Extract .next-up Component

**Files:**
- Modify: `shared/css/components.css` (append at end)
- Modify: `shared/styleguide.html` (add example)

**Step 1: Add CSS to components.css**

Append to `shared/css/components.css`:

```css
/* ==========================================================================
   NEXT UP
   Preview list of upcoming items
   ========================================================================== */

.next-up {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border-light);
}

.next-up__header {
  font-size: 0.625rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.5rem;
  color: var(--color-muted);
}

.next-up__item {
  padding: 0.5rem 0;
  font-size: 0.875rem;
  color: var(--color-muted);
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
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

.next-up__meta {
  flex-shrink: 0;
  font-size: 0.75rem;
}
```

**Step 2: Add example to styleguide.html**

Add after List-Detail Layout section:

```html
<!-- Next Up -->
<section>
  <h2>Next Up</h2>
  <p>Preview list of upcoming items in a queue.</p>

  <div class="example" style="max-width: 400px;">
    <div class="next-up">
      <div class="next-up__header">Next Up</div>
      <div class="next-up__item">
        <span class="next-up__title">How to Build a Second Brain</span>
        <span class="next-up__meta">2h ago</span>
      </div>
      <div class="next-up__item">
        <span class="next-up__title">The Art of Doing Science and Engineering</span>
        <span class="next-up__meta">3h ago</span>
      </div>
      <div class="next-up__item">
        <span class="next-up__title">Thinking in Systems: A Primer</span>
        <span class="next-up__meta">5h ago</span>
      </div>
    </div>
  </div>
</section>
```

**Step 3: Commit**

```bash
git add shared/css/components.css shared/styleguide.html
git commit -m "feat(shared): add .next-up component"
```

---

## Task 5: Enhance .list Component with Hover Effects

**Files:**
- Modify: `shared/css/components.css` (find and update .list section)

**Step 1: Update .list__item in components.css**

Find the `.list__item` rule and update to:

```css
.list__item {
  padding: var(--space-sm) var(--space-md);
  border-bottom: 1px solid var(--color-border-light);
  cursor: pointer;
  transition: all 0.15s ease;
}

.list__item:last-child {
  border-bottom: none;
}

.list__item:hover {
  background: var(--color-hover);
  box-shadow: 3px 3px 0 var(--color-border);
}

.list__item--selected {
  background: var(--color-text);
  color: var(--color-bg);
}

.list__item--selected:hover {
  box-shadow: none;
}
```

**Step 2: Commit**

```bash
git add shared/css/components.css
git commit -m "feat(shared): enhance .list__item with hover shadow"
```

---

## Task 6: Add .action-panel__btn Variants

**Files:**
- Modify: `shared/css/components.css` (find and update .action-panel section)

**Step 1: Add button variants to .action-panel section**

Find the `.action-panel` section and append:

```css
.action-panel__btn {
  padding: 0.75rem 1rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  font-family: inherit;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: center;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-panel__btn:hover {
  background: var(--color-hover);
}

.action-panel__btn--primary {
  background: var(--color-text);
  color: var(--color-bg);
  border-color: var(--color-text);
}

.action-panel__btn--primary:hover {
  opacity: 0.9;
}

.action-panel__btn--danger {
  border-color: var(--color-danger);
  color: var(--color-danger);
}

.action-panel__btn--danger:hover {
  background: #fee;
}

@media (max-width: 768px) {
  .action-panel__btn {
    min-height: 48px;
    font-size: 0.875rem;
  }
}
```

**Step 2: Update styleguide.html action-panel example**

Find the Action Panel section and add button examples:

```html
<div class="example">
  <div class="action-panel" style="width: 200px;">
    <button class="action-panel__btn action-panel__btn--primary">Primary</button>
    <button class="action-panel__btn">Secondary</button>
    <button class="action-panel__btn action-panel__btn--danger">Danger</button>
  </div>
</div>
```

**Step 3: Commit**

```bash
git add shared/css/components.css shared/styleguide.html
git commit -m "feat(shared): add .action-panel__btn variants"
```

---

## Task 7: Extract .btn--option Component (from Balance)

**Files:**
- Modify: `shared/css/components.css` (append to button section)
- Modify: `shared/styleguide.html` (add example)

**Step 1: Add CSS to components.css**

Find the button section and append:

```css
/* Option/Toggle button - for multi-choice selections */
.btn--option {
  padding: var(--space-sm) var(--space-md);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn--option:hover {
  background: var(--color-hover);
}

.btn--option.selected,
.btn--option[aria-pressed="true"] {
  background: var(--color-text);
  color: var(--color-bg);
  border-color: var(--color-text);
}

/* Button group for option buttons */
.button-group {
  display: flex;
  gap: var(--space-xs);
  flex-wrap: wrap;
}

.button-group--vertical {
  flex-direction: column;
}
```

**Step 2: Add example to styleguide.html**

Add after Buttons section:

```html
<!-- Option Buttons -->
<section>
  <h2>Option Buttons</h2>
  <p>Toggle/multi-choice buttons for selections.</p>

  <div class="example">
    <div class="button-group">
      <button class="btn--option selected">Option A</button>
      <button class="btn--option">Option B</button>
      <button class="btn--option">Option C</button>
    </div>
  </div>

  <div class="example">
    <div class="button-group--vertical" style="width: 200px;">
      <button class="btn--option">15 min</button>
      <button class="btn--option selected">30 min</button>
      <button class="btn--option">45 min</button>
      <button class="btn--option">60 min</button>
    </div>
  </div>
</section>
```

**Step 3: Commit**

```bash
git add shared/css/components.css shared/styleguide.html
git commit -m "feat(shared): add .btn--option and .button-group components"
```

---

## Task 8: Extract .timer Component (from Balance)

**Files:**
- Modify: `shared/css/components.css` (append at end)
- Modify: `shared/styleguide.html` (add example)

**Step 1: Add CSS to components.css**

Append to `shared/css/components.css`:

```css
/* ==========================================================================
   TIMER DISPLAY
   Large timer for countdowns and time display
   ========================================================================== */

.timer {
  text-align: center;
}

.timer__value {
  font-size: 6rem;
  font-weight: 300;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.timer__label {
  font-size: var(--font-size-sm);
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: var(--space-sm);
}

@media (min-width: 769px) {
  .timer__value {
    font-size: 8rem;
  }
}
```

**Step 2: Add example to styleguide.html**

Add after Progress section:

```html
<!-- Timer -->
<section>
  <h2>Timer</h2>
  <p>Large timer display for countdowns.</p>

  <div class="example">
    <div class="timer">
      <div class="timer__value">25:00</div>
      <div class="timer__label">Focus Time</div>
    </div>
  </div>
</section>
```

**Step 3: Commit**

```bash
git add shared/css/components.css shared/styleguide.html
git commit -m "feat(shared): add .timer component"
```

---

## Task 9: Extract .setting-row Component (from Balance)

**Files:**
- Modify: `shared/css/components.css` (append at end)
- Modify: `shared/styleguide.html` (add example)

**Step 1: Add CSS to components.css**

Append to `shared/css/components.css`:

```css
/* ==========================================================================
   SETTING ROW
   Key-value pairs for settings/config display
   ========================================================================== */

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-sm) 0;
  border-bottom: 1px solid var(--color-border-light);
}

.setting-row:last-child {
  border-bottom: none;
}

.setting-row__label {
  font-size: var(--font-size-sm);
}

.setting-row__value {
  font-size: var(--font-size-sm);
  color: var(--color-muted);
}

.setting-row__input {
  width: 60px;
  padding: var(--space-xs);
  border: 1px solid var(--color-border);
  font-family: inherit;
  font-size: var(--font-size-sm);
  text-align: center;
}

.setting-row__unit {
  font-size: var(--font-size-xs);
  color: var(--color-muted);
  margin-left: var(--space-xs);
}
```

**Step 2: Add example to styleguide.html**

Add after Timer section:

```html
<!-- Setting Row -->
<section>
  <h2>Setting Row</h2>
  <p>Key-value pairs for settings display.</p>

  <div class="example" style="max-width: 400px;">
    <div class="setting-row">
      <span class="setting-row__label">Focus Duration</span>
      <span class="setting-row__value">25 min</span>
    </div>
    <div class="setting-row">
      <span class="setting-row__label">Break Duration</span>
      <span class="setting-row__value">5 min</span>
    </div>
    <div class="setting-row">
      <span class="setting-row__label">Daily Goal</span>
      <div>
        <input type="number" class="setting-row__input" value="4">
        <span class="setting-row__unit">sessions</span>
      </div>
    </div>
  </div>
</section>
```

**Step 3: Commit**

```bash
git add shared/css/components.css shared/styleguide.html
git commit -m "feat(shared): add .setting-row component"
```

---

## Task 10: Update COMPONENT-LIBRARY.md Documentation

**Files:**
- Modify: `docs/COMPONENT-LIBRARY.md`

**Step 1: Add documentation for new components**

Append to `docs/COMPONENT-LIBRARY.md`:

```markdown
## View Header

Section header with title and optional count.

```html
<div class="view-header">
  <span class="view-header__title">INBOX (27)</span>
  <span class="view-header__count">3 unread</span>
</div>
```

## Detail Panel

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

## List-Detail Layout

Two-column layout with list and detail panel.

```html
<div class="layout--list-detail">
  <div class="list">...</div>
  <div class="detail-panel">...</div>
</div>
```

## Next Up

Preview list of upcoming items.

```html
<div class="next-up">
  <div class="next-up__header">Next Up</div>
  <div class="next-up__item">
    <span class="next-up__title">Item title</span>
    <span class="next-up__meta">2h ago</span>
  </div>
</div>
```

## Option Buttons

Toggle/multi-choice buttons.

```html
<div class="button-group">
  <button class="btn--option selected">Option A</button>
  <button class="btn--option">Option B</button>
</div>
```

## Timer

Large timer display.

```html
<div class="timer">
  <div class="timer__value">25:00</div>
  <div class="timer__label">Focus Time</div>
</div>
```

## Setting Row

Key-value pairs for settings.

```html
<div class="setting-row">
  <span class="setting-row__label">Duration</span>
  <span class="setting-row__value">25 min</span>
</div>
```
```

**Step 2: Commit**

```bash
git add docs/COMPONENT-LIBRARY.md
git commit -m "docs: add new component documentation"
```

---

## Task 11: Refactor Bookmark-Manager to Use Shared Components

**Files:**
- Modify: `bookmark-manager/src/templates/base.html`
- Modify: `bookmark-manager/src/templates/_content_index.html`

**Step 1: Update base.html - Remove duplicated CSS**

In `bookmark-manager/src/templates/base.html`, remove these CSS blocks (they're now in shared):
- `.inbox-header`, `.inbox-count` → use `.view-header`
- `.list-layout` → use `.layout--list-detail`
- `.bookmark-list`, `.bookmark-item` → use `.list`, `.list__item`
- `.detail-panel` (inline) → use shared `.detail-panel`
- `.next-up` styles → use shared `.next-up`

**Step 2: Update _content_index.html - Use new classes**

Replace class names:
- `inbox-header` → `view-header`
- `inbox-count` → `view-header__title`
- `list-layout` → `layout--list-detail`
- `bookmark-list` → `list`
- `bookmark-item` → `list__item`
- `bookmark-title` → `list__item-title`
- `bookmark-domain` → `list__item-meta`
- `next-up-header` → `next-up__header`
- `next-up-item` → `next-up__item`
- `next-up-title` → `next-up__title`

**Step 3: Test visually**

Run: `cd bookmark-manager && python -m uvicorn src.main:app --reload --port 8001`
Open: http://localhost:8001/ui/
Verify: All views (Inbox, Thesis, Pins, Feeds) look correct

**Step 4: Commit**

```bash
git add bookmark-manager/src/templates/
git commit -m "refactor(bookmark-manager): use shared components"
```

---

**Plan complete and saved to `docs/plans/2025-12-30-component-library-extraction-plan.md`.**

**Two execution options:**

1. **Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

2. **Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
