# Next Up UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Next Up UI to Balance home screen (capture + list) and timer screen (mini capture).

**Architecture:** Extend existing `timer.js` with Next Up state management. Add HTML sections to `_content_index.html`. Reuse `priority-list` CSS pattern for the list display.

**Tech Stack:** Vanilla JS, Jinja2 templates, existing shared CSS components

**Design Doc:** `docs/plans/2026-01-03-next-up-design.md`

**Mockup:** `balance/src/templates/mockup.html` (view with `DEV_MODE=true`)

**Prerequisite:** Next Up API complete (`/api/nextup` endpoints working)

---

## Task 1: Add Next Up HTML to Home Screen

**Files:**
- Modify: `balance/src/templates/_content_index.html`

**Step 1: Add capture input and list section**

In `_content_index.html`, add after the status paragraph (line 4) and before the timer div:

```html
      <!-- Next Up Capture -->
      <div class="nextup-capture">
        <input type="text" id="nextup-input" class="input" placeholder="+ Add task..." maxlength="100">
        <div class="nextup-hint">Press Enter · <span id="slots-left">5</span> slots left</div>
      </div>

      <!-- Next Up List -->
      <div class="nextup-section">
        <div class="view-header">
          <span class="view-header__title">NEXT UP</span>
        </div>
        <div class="priority-list" id="nextup-list">
          <!-- Populated by JS -->
        </div>
      </div>
```

**Step 2: Verify HTML renders**

```bash
cd balance && DEV_MODE=true uvicorn src.main:app --reload --port 8005
# Visit http://localhost:8005 - should see empty capture input and list container
```

**Step 3: Commit**

```bash
git add balance/src/templates/_content_index.html
git commit -m "feat(balance): add Next Up HTML section to home screen"
```

---

## Task 2: Add Next Up CSS

**Files:**
- Modify: `balance/src/static/css/balance.css`

**Step 1: Add Next Up styles**

Add to `balance/src/static/css/balance.css`:

```css
/* Next Up */
.nextup-capture {
  margin-bottom: 1rem;
}

.nextup-hint {
  font-size: var(--font-size-xs);
  color: var(--color-muted);
  margin-top: 0.25rem;
}

.nextup-section {
  margin-bottom: 1.5rem;
}

.nextup-section .priority-list {
  max-height: 280px;
  overflow-y: auto;
}

.nextup-item {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.nextup-item.selected {
  background: var(--color-hover);
  border-left: 3px solid var(--color-text);
}

.nextup-item__text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nextup-item__meta {
  font-size: var(--font-size-sm);
  color: var(--color-muted);
  white-space: nowrap;
}

.nextup-item__delete {
  opacity: 0;
  transition: opacity 0.15s;
  padding: 0 0.5rem;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--color-muted);
}

.nextup-item:hover .nextup-item__delete {
  opacity: 1;
}

.nextup-empty {
  border: 1px dashed var(--color-border-light);
  background: none !important;
  color: var(--color-muted);
  font-size: var(--font-size-sm);
  padding: var(--space-sm) var(--space-md);
}

.nextup-empty + .nextup-empty {
  border-top: none;
}
```

**Step 2: Verify styles**

```bash
# Refresh http://localhost:8005 - capture input should be styled
```

**Step 3: Commit**

```bash
git add balance/src/static/css/balance.css
git commit -m "feat(balance): add Next Up CSS styles"
```

---

## Task 3: Add Next Up State to timer.js

**Files:**
- Modify: `balance/src/static/js/timer.js`

**Step 1: Add state variables**

In `timer.js`, add to the Balance object state (after line 41):

```javascript
  // Next Up state
  nextUpItems: [],
  selectedNextUpId: null,
  maxNextUpItems: 5,
```

**Step 2: Cache Next Up elements**

In `cacheElements()`, add after the YouTube duration section (around line 114):

```javascript
    // Next Up
    this.el.nextupInput = document.getElementById('nextup-input');
    this.el.nextupList = document.getElementById('nextup-list');
    this.el.slotsLeft = document.getElementById('slots-left');
```

**Step 3: Commit**

```bash
git add balance/src/static/js/timer.js
git commit -m "feat(balance): add Next Up state variables to timer.js"
```

---

## Task 4: Load and Render Next Up List

**Files:**
- Modify: `balance/src/static/js/timer.js`

**Step 1: Add loadNextUp function**

Add to Balance object (after `loadPriorities()`):

```javascript
  async loadNextUp() {
    try {
      const response = await fetch('/api/nextup');
      const data = await response.json();
      this.nextUpItems = data.items;
      this.maxNextUpItems = data.max;
      this.renderNextUp();
    } catch (err) {
      console.error('Failed to load Next Up:', err);
    }
  },

  renderNextUp() {
    if (!this.el.nextupList) return;

    const count = this.nextUpItems.length;
    this.el.slotsLeft.textContent = this.maxNextUpItems - count;

    let html = '';

    // Render items
    this.nextUpItems.forEach(item => {
      const dueStr = item.due_date ? this.formatDueDate(item.due_date) : '';
      const priorityStr = item.priority_name ? `${item.priority_name}` : '';
      const meta = [priorityStr, dueStr].filter(Boolean).join(' · ');
      const selected = item.id === this.selectedNextUpId ? 'selected' : '';

      html += `
        <div class="priority-list__item nextup-item ${selected}" data-id="${item.id}">
          <span class="nextup-item__text">${this.escapeHtml(item.text)}</span>
          ${meta ? `<span class="nextup-item__meta">${meta}</span>` : ''}
          <button class="nextup-item__delete" onclick="event.stopPropagation(); Balance.deleteNextUp(${item.id})">✕</button>
        </div>
      `;
    });

    // Render empty slots
    for (let i = count; i < this.maxNextUpItems; i++) {
      html += `<div class="priority-list__item nextup-empty">${i + 1}. empty slot</div>`;
    }

    this.el.nextupList.innerHTML = html;

    // Bind click events for selection
    this.el.nextupList.querySelectorAll('.nextup-item:not(.nextup-empty)').forEach(item => {
      item.addEventListener('click', () => this.selectNextUp(parseInt(item.dataset.id)));
    });
  },

  formatDueDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  },

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },
```

**Step 2: Call loadNextUp in syncWithServer**

In `syncWithServer()`, add after `await this.loadPriorities();` (around line 288):

```javascript
      // Load Next Up items
      await this.loadNextUp();
```

**Step 3: Verify list renders**

```bash
# Refresh http://localhost:8005 - should see 5 empty slots
# Add items via API: curl -X POST "http://localhost:8005/api/nextup" -H "Content-Type: application/json" -d '{"text":"Test task"}'
# Refresh - should see task in list
```

**Step 4: Commit**

```bash
git add balance/src/static/js/timer.js
git commit -m "feat(balance): add Next Up list loading and rendering"
```

---

## Task 5: Add Capture Input Handler

**Files:**
- Modify: `balance/src/static/js/timer.js`

**Step 1: Add capture function**

Add to Balance object:

```javascript
  async addNextUp(text) {
    if (!text.trim()) return;

    try {
      const response = await fetch('/api/nextup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim() })
      });

      if (response.ok) {
        this.el.nextupInput.value = '';
        await this.loadNextUp();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to add task');
      }
    } catch (err) {
      console.error('Failed to add Next Up:', err);
    }
  },
```

**Step 2: Bind Enter key in bindEvents**

In `bindEvents()`, add after the quick actions section (around line 218):

```javascript
    // Next Up capture input
    this.el.nextupInput?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        this.addNextUp(e.target.value);
      }
    });
```

**Step 3: Test capture**

```bash
# Refresh http://localhost:8005
# Type "Buy groceries" in capture input, press Enter
# Task should appear in list
```

**Step 4: Commit**

```bash
git add balance/src/static/js/timer.js
git commit -m "feat(balance): add Next Up capture input handler"
```

---

## Task 6: Add Delete Handler

**Files:**
- Modify: `balance/src/static/js/timer.js`

**Step 1: Add delete function**

Add to Balance object:

```javascript
  async deleteNextUp(id) {
    try {
      await fetch(`/api/nextup/${id}`, { method: 'DELETE' });

      // Clear selection if deleting selected item
      if (this.selectedNextUpId === id) {
        this.selectedNextUpId = null;
        this.el.intentionInput.value = '';
        this.intention = '';
      }

      await this.loadNextUp();
    } catch (err) {
      console.error('Failed to delete Next Up:', err);
    }
  },
```

**Step 2: Test delete**

```bash
# Click ✕ on a task - should be removed
```

**Step 3: Commit**

```bash
git add balance/src/static/js/timer.js
git commit -m "feat(balance): add Next Up delete handler"
```

---

## Task 7: Add Selection for Expected Sessions

**Files:**
- Modify: `balance/src/static/js/timer.js`

**Step 1: Add selectNextUp function**

Add to Balance object:

```javascript
  selectNextUp(id) {
    // Toggle selection
    if (this.selectedNextUpId === id) {
      this.selectedNextUpId = null;
      this.el.intentionInput.value = '';
      this.intention = '';
    } else {
      this.selectedNextUpId = id;
      const item = this.nextUpItems.find(i => i.id === id);
      if (item) {
        this.el.intentionInput.value = item.text;
        this.intention = item.text;
        this.el.charCount.textContent = item.text.length;
      }
    }

    this.renderNextUp();
    this.updateStartButton();
  },
```

**Step 2: Update updateStartButton to require selection**

Replace existing `updateStartButton()`:

```javascript
  updateStartButton() {
    if (this.sessionType === 'expected') {
      // Expected requires priority AND Next Up selection (if items exist)
      const hasPriority = !this.priorities.length || this.selectedPriorityId;
      const hasNextUp = !this.nextUpItems.length || this.selectedNextUpId;
      this.el.startBtn.disabled = !(hasPriority && hasNextUp);
    } else {
      this.el.startBtn.disabled = false;
    }
  },
```

**Step 3: Clear selection on type change**

In the type selection click handler (inside bindEvents), add after setting `this.sessionType`:

```javascript
        // Clear Next Up selection when switching types
        this.selectedNextUpId = null;
        this.renderNextUp();
```

**Step 4: Test selection**

```bash
# Click a task - should highlight and fill intention
# Select "Expected" - Start button should be disabled until task is selected
# Click task - Start button should enable (if priority also selected)
```

**Step 5: Commit**

```bash
git add balance/src/static/js/timer.js
git commit -m "feat(balance): add Next Up selection for Expected sessions"
```

---

## Task 8: Include next_up_id in Session Start

**Files:**
- Modify: `balance/src/static/js/timer.js`

**Step 1: Update startSession to include next_up_id**

In `startSession()`, update the body construction (around line 574):

```javascript
      const body = {
        type: this.sessionType,
        intention: this.intention || null
      };

      // Add priority_id for expected sessions
      if (this.sessionType === 'expected') {
        body.priority_id = this.selectedPriorityId;
        // Add next_up_id if a task is selected
        if (this.selectedNextUpId) {
          body.next_up_id = this.selectedNextUpId;
        }
      }

      // Add duration_minutes for YouTube sessions
      if (this.sessionType === 'youtube') {
        body.duration_minutes = this.selectedDuration;
      }
```

**Step 2: Clear selection after starting session**

After successful session start (after `await this.syncWithServer();`):

```javascript
      // Clear Next Up selection for next session
      this.selectedNextUpId = null;
```

**Step 3: Test session linking**

```bash
# Select a Next Up task, start Expected session
# Check database: SELECT * FROM sessions ORDER BY id DESC LIMIT 1;
# next_up_id should be set
```

**Step 4: Commit**

```bash
git add balance/src/static/js/timer.js
git commit -m "feat(balance): include next_up_id when starting Expected sessions"
```

---

## Task 9: Add Mini Capture to Timer Screen

**Files:**
- Modify: `balance/src/templates/_content_index.html`
- Modify: `balance/src/static/js/timer.js`

**Step 1: Add HTML for mini capture**

In `_content_index.html`, inside the active session page (after the session-counter div, around line 84):

```html
      <div class="timer-capture">
        <input type="text" id="timer-capture-input" class="input input--sm" placeholder="+ Quick capture...">
        <div class="timer-capture__hint">Thought? Capture it, stay focused.</div>
      </div>
```

**Step 2: Add CSS for mini capture**

In `balance/src/static/css/balance.css`:

```css
/* Timer Mini Capture */
.timer-capture {
  margin-top: 2rem;
  max-width: 280px;
  margin-left: auto;
  margin-right: auto;
}

.timer-capture__hint {
  font-size: var(--font-size-xs);
  color: var(--color-muted);
  margin-top: 0.25rem;
  text-align: center;
}
```

**Step 3: Cache element**

In `cacheElements()`:

```javascript
    this.el.timerCaptureInput = document.getElementById('timer-capture-input');
```

**Step 4: Bind event**

In `bindEvents()`:

```javascript
    // Timer mini capture
    this.el.timerCaptureInput?.addEventListener('keypress', async (e) => {
      if (e.key === 'Enter') {
        const text = e.target.value.trim();
        if (text) {
          try {
            const response = await fetch('/api/nextup', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ text })
            });
            if (response.ok) {
              e.target.value = '';
              e.target.placeholder = '✓ Captured';
              setTimeout(() => {
                e.target.placeholder = '+ Quick capture...';
              }, 1000);
            }
          } catch (err) {
            console.error('Failed to capture:', err);
          }
        }
      }
    });
```

**Step 5: Test mini capture**

```bash
# Start a session
# Type in mini capture input, press Enter
# Should show "✓ Captured" briefly
# After session, task should appear in Next Up list
```

**Step 6: Commit**

```bash
git add balance/src/templates/_content_index.html balance/src/static/css/balance.css balance/src/static/js/timer.js
git commit -m "feat(balance): add mini capture input to timer screen"
```

---

## Task 10: Full Manual Test

**Step 1: Test complete flow**

```bash
# 1. Add tasks via capture input (test limit at 5)
# 2. Click task to select - intention should fill
# 3. Try to start Expected without selection - should be disabled
# 4. Select task + priority, start Expected session
# 5. During session, use mini capture
# 6. After session, verify new task appears
# 7. Delete tasks via ✕ button
# 8. Personal sessions should work without selection
```

**Step 2: Verify data integrity**

```bash
sqlite3 balance/data/balance.db "SELECT id, text, session_count FROM next_up"
sqlite3 balance/data/balance.db "SELECT id, type, intention, next_up_id FROM sessions ORDER BY id DESC LIMIT 5"
```

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(balance): complete Next Up UI implementation"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Add Next Up HTML to home screen |
| 2 | Add CSS styles |
| 3 | Add state variables to timer.js |
| 4 | Load and render list |
| 5 | Capture input handler |
| 6 | Delete handler |
| 7 | Selection for Expected sessions |
| 8 | Include next_up_id in session start |
| 9 | Mini capture on timer screen |
| 10 | Full manual test |

**Not included in this plan:**
- Edit task modal (can add later if needed)
- Due date editing (API supports it, UI can come later)
