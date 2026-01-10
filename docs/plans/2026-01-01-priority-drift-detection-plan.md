# Priority Drift Detection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add priority tracking to Expected sessions so Balance can detect when actual work drifts from stated priorities.

**Architecture:** New `priorities` table stores ranked priorities. Expected sessions reference a priority via `priority_id`. Stats endpoint calculates drift by comparing priority rank to actual session distribution.

**Tech Stack:** Python/FastAPI, SQLite, Jinja2, vanilla JS. Uses existing shared component library.

---

## Task 1: Database Schema — Priorities Table

**Files:**
- Modify: `balance/src/database.py:15-50`
- Test: `balance/tests/test_database.py` (new file)

**Step 1: Write failing test for priorities table**

```python
# balance/tests/test_database.py
import pytest
from balance.src.database import init_db, get_db

@pytest.fixture(autouse=True)
async def setup_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    await init_db()

@pytest.mark.asyncio
async def test_priorities_table_exists():
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='priorities'"
        )
        result = await cursor.fetchone()
        assert result is not None
        assert result[0] == "priorities"
```

**Step 2: Run test to verify it fails**

Run: `cd balance && python -m pytest tests/test_database.py -v`
Expected: FAIL — table doesn't exist

**Step 3: Add priorities table to init_db**

In `balance/src/database.py`, add after sessions table creation:

```python
await db.execute("""
    CREATE TABLE IF NOT EXISTS priorities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        rank INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        archived_at TEXT
    )
""")
```

**Step 4: Run test to verify it passes**

Run: `cd balance && python -m pytest tests/test_database.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add balance/src/database.py balance/tests/test_database.py
git commit -m "feat(balance): add priorities table schema"
```

---

## Task 2: Database Schema — Add priority_id to Sessions

**Files:**
- Modify: `balance/src/database.py`
- Modify: `balance/tests/test_database.py`

**Step 1: Write failing test for priority_id column**

```python
# Add to balance/tests/test_database.py
@pytest.mark.asyncio
async def test_sessions_has_priority_id_column():
    async with get_db() as db:
        cursor = await db.execute("PRAGMA table_info(sessions)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        assert "priority_id" in column_names
```

**Step 2: Run test to verify it fails**

Run: `cd balance && python -m pytest tests/test_database.py::test_sessions_has_priority_id_column -v`
Expected: FAIL — column doesn't exist

**Step 3: Add priority_id column to sessions table**

In `balance/src/database.py`, modify sessions table creation:

```python
await db.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        intention TEXT,
        priority_id INTEGER,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        distractions TEXT,
        did_the_thing INTEGER,
        rabbit_hole INTEGER,
        FOREIGN KEY (priority_id) REFERENCES priorities(id)
    )
""")
```

**Step 4: Run test to verify it passes**

Run: `cd balance && python -m pytest tests/test_database.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add balance/src/database.py balance/tests/test_database.py
git commit -m "feat(balance): add priority_id to sessions table"
```

---

## Task 3: Pydantic Models for Priorities

**Files:**
- Modify: `balance/src/models.py`

**Step 1: Add Priority models**

```python
# Add to balance/src/models.py

class Priority(BaseModel):
    id: int
    name: str
    rank: int
    session_count: int = 0

class PriorityCreate(BaseModel):
    name: str

class PriorityReorder(BaseModel):
    order: list[int]  # List of priority IDs in new order
```

**Step 2: Verify imports work**

Run: `cd balance && python -c "from src.models import Priority, PriorityCreate, PriorityReorder; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add balance/src/models.py
git commit -m "feat(balance): add Priority pydantic models"
```

---

## Task 4: Priorities Router — List Endpoint

**Files:**
- Create: `balance/src/routers/priorities.py`
- Modify: `balance/src/main.py`
- Create: `balance/tests/test_priorities.py`

**Step 1: Write failing test for GET /api/priorities**

```python
# balance/tests/test_priorities.py
import pytest
from httpx import AsyncClient, ASGITransport
from balance.src.main import app
from balance.src.database import init_db, get_db
import os

@pytest.fixture(autouse=True)
async def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    await init_db()

@pytest.mark.asyncio
async def test_list_priorities_empty():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/priorities")
        assert response.status_code == 200
        assert response.json() == []
```

**Step 2: Run test to verify it fails**

Run: `cd balance && python -m pytest tests/test_priorities.py -v`
Expected: FAIL — 404 Not Found

**Step 3: Create priorities router with list endpoint**

```python
# balance/src/routers/priorities.py
from fastapi import APIRouter
from ..database import get_db
from ..models import Priority

router = APIRouter(prefix="/api", tags=["priorities"])

@router.get("/priorities")
async def list_priorities() -> list[Priority]:
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT p.id, p.name, p.rank,
                   COUNT(s.id) as session_count
            FROM priorities p
            LEFT JOIN sessions s ON s.priority_id = p.id
            WHERE p.archived_at IS NULL
            GROUP BY p.id
            ORDER BY p.rank
        """)
        rows = await cursor.fetchall()
        return [
            Priority(
                id=row[0],
                name=row[1],
                rank=row[2],
                session_count=row[3]
            )
            for row in rows
        ]
```

**Step 4: Register router in main.py**

Add to `balance/src/main.py`:

```python
from .routers import sessions, logging, settings, priorities

# After other router includes:
app.include_router(priorities.router)
```

**Step 5: Run test to verify it passes**

Run: `cd balance && python -m pytest tests/test_priorities.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add balance/src/routers/priorities.py balance/src/main.py balance/tests/test_priorities.py
git commit -m "feat(balance): add GET /api/priorities endpoint"
```

---

## Task 5: Priorities Router — Create Endpoint

**Files:**
- Modify: `balance/src/routers/priorities.py`
- Modify: `balance/tests/test_priorities.py`

**Step 1: Write failing test for POST /api/priorities**

```python
# Add to balance/tests/test_priorities.py
@pytest.mark.asyncio
async def test_create_priority():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/priorities", json={"name": "Thesis"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Thesis"
        assert data["rank"] == 1
        assert data["id"] is not None

@pytest.mark.asyncio
async def test_create_priority_auto_ranks():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/priorities", json={"name": "First"})
        response = await client.post("/api/priorities", json={"name": "Second"})
        assert response.json()["rank"] == 2
```

**Step 2: Run test to verify it fails**

Run: `cd balance && python -m pytest tests/test_priorities.py::test_create_priority -v`
Expected: FAIL — 405 Method Not Allowed

**Step 3: Add create endpoint**

```python
# Add to balance/src/routers/priorities.py
from datetime import datetime
from ..models import Priority, PriorityCreate

@router.post("/priorities")
async def create_priority(data: PriorityCreate) -> Priority:
    async with get_db() as db:
        # Get next rank
        cursor = await db.execute(
            "SELECT MAX(rank) FROM priorities WHERE archived_at IS NULL"
        )
        row = await cursor.fetchone()
        next_rank = (row[0] or 0) + 1

        # Insert priority
        cursor = await db.execute(
            """INSERT INTO priorities (name, rank, created_at)
               VALUES (?, ?, ?)""",
            (data.name, next_rank, datetime.now().isoformat())
        )
        await db.commit()
        priority_id = cursor.lastrowid

        return Priority(
            id=priority_id,
            name=data.name,
            rank=next_rank,
            session_count=0
        )
```

**Step 4: Run tests to verify they pass**

Run: `cd balance && python -m pytest tests/test_priorities.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add balance/src/routers/priorities.py balance/tests/test_priorities.py
git commit -m "feat(balance): add POST /api/priorities endpoint"
```

---

## Task 6: Priorities Router — Reorder Endpoint

**Files:**
- Modify: `balance/src/routers/priorities.py`
- Modify: `balance/tests/test_priorities.py`

**Step 1: Write failing test for PUT /api/priorities/reorder**

```python
# Add to balance/tests/test_priorities.py
@pytest.mark.asyncio
async def test_reorder_priorities():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create three priorities
        r1 = await client.post("/api/priorities", json={"name": "First"})
        r2 = await client.post("/api/priorities", json={"name": "Second"})
        r3 = await client.post("/api/priorities", json={"name": "Third"})

        id1, id2, id3 = r1.json()["id"], r2.json()["id"], r3.json()["id"]

        # Reorder: Third, First, Second
        response = await client.put(
            "/api/priorities/reorder",
            json={"order": [id3, id1, id2]}
        )
        assert response.status_code == 200

        # Verify new order
        list_response = await client.get("/api/priorities")
        priorities = list_response.json()
        assert priorities[0]["name"] == "Third"
        assert priorities[0]["rank"] == 1
        assert priorities[1]["name"] == "First"
        assert priorities[2]["name"] == "Second"
```

**Step 2: Run test to verify it fails**

Run: `cd balance && python -m pytest tests/test_priorities.py::test_reorder_priorities -v`
Expected: FAIL — 405 Method Not Allowed

**Step 3: Add reorder endpoint**

```python
# Add to balance/src/routers/priorities.py
from ..models import Priority, PriorityCreate, PriorityReorder

@router.put("/priorities/reorder")
async def reorder_priorities(data: PriorityReorder):
    async with get_db() as db:
        for rank, priority_id in enumerate(data.order, start=1):
            await db.execute(
                "UPDATE priorities SET rank = ? WHERE id = ?",
                (rank, priority_id)
            )
        await db.commit()
    return {"status": "ok"}
```

**Step 4: Run test to verify it passes**

Run: `cd balance && python -m pytest tests/test_priorities.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add balance/src/routers/priorities.py balance/tests/test_priorities.py
git commit -m "feat(balance): add PUT /api/priorities/reorder endpoint"
```

---

## Task 7: Priorities Router — Delete Endpoint

**Files:**
- Modify: `balance/src/routers/priorities.py`
- Modify: `balance/tests/test_priorities.py`

**Step 1: Write failing test for DELETE /api/priorities/:id**

```python
# Add to balance/tests/test_priorities.py
@pytest.mark.asyncio
async def test_delete_priority():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create priority
        create_resp = await client.post("/api/priorities", json={"name": "ToDelete"})
        priority_id = create_resp.json()["id"]

        # Delete it
        response = await client.delete(f"/api/priorities/{priority_id}")
        assert response.status_code == 200

        # Verify it's gone
        list_resp = await client.get("/api/priorities")
        assert len(list_resp.json()) == 0
```

**Step 2: Run test to verify it fails**

Run: `cd balance && python -m pytest tests/test_priorities.py::test_delete_priority -v`
Expected: FAIL — 405 Method Not Allowed

**Step 3: Add delete endpoint**

```python
# Add to balance/src/routers/priorities.py
from fastapi import APIRouter, HTTPException

@router.delete("/priorities/{priority_id}")
async def delete_priority(priority_id: int):
    async with get_db() as db:
        # Check if priority has sessions
        cursor = await db.execute(
            "SELECT COUNT(*) FROM sessions WHERE priority_id = ?",
            (priority_id,)
        )
        count = (await cursor.fetchone())[0]

        if count > 0:
            # Archive instead of delete
            await db.execute(
                "UPDATE priorities SET archived_at = ? WHERE id = ?",
                (datetime.now().isoformat(), priority_id)
            )
        else:
            # Actually delete
            await db.execute("DELETE FROM priorities WHERE id = ?", (priority_id,))

        await db.commit()
    return {"status": "ok"}
```

**Step 4: Run test to verify it passes**

Run: `cd balance && python -m pytest tests/test_priorities.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add balance/src/routers/priorities.py balance/tests/test_priorities.py
git commit -m "feat(balance): add DELETE /api/priorities/:id endpoint"
```

---

## Task 8: Session Start — Accept priority_id

**Files:**
- Modify: `balance/src/models.py`
- Modify: `balance/src/routers/sessions.py`
- Modify: `balance/tests/test_sessions.py`

**Step 1: Write failing test for session with priority**

```python
# Add to balance/tests/test_sessions.py
@pytest.mark.asyncio
async def test_start_session_with_priority():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a priority first
        priority_resp = await client.post("/api/priorities", json={"name": "Thesis"})
        priority_id = priority_resp.json()["id"]

        # Start session with priority
        response = await client.post("/api/sessions/start", json={
            "type": "expected",
            "intention": "Write chapter 1",
            "priority_id": priority_id
        })
        assert response.status_code == 200
        assert response.json()["priority_id"] == priority_id
```

**Step 2: Run test to verify it fails**

Run: `cd balance && python -m pytest tests/test_sessions.py::test_start_session_with_priority -v`
Expected: FAIL — priority_id not in response or validation error

**Step 3: Update SessionStart model**

```python
# Modify in balance/src/models.py
class SessionStart(BaseModel):
    type: Literal["expected", "personal"]
    intention: Optional[str] = None
    priority_id: Optional[int] = None
```

**Step 4: Update start_session endpoint**

In `balance/src/routers/sessions.py`, modify the INSERT statement:

```python
@router.post("/sessions/start")
async def start_session(data: SessionStart):
    # ... existing validation ...

    async with get_db() as db:
        now = datetime.now().isoformat()
        cursor = await db.execute(
            """INSERT INTO sessions (type, intention, priority_id, started_at)
               VALUES (?, ?, ?, ?)""",
            (data.type, data.intention, data.priority_id, now)
        )
        await db.commit()
        session_id = cursor.lastrowid

        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        return dict(row)
```

**Step 5: Run test to verify it passes**

Run: `cd balance && python -m pytest tests/test_sessions.py::test_start_session_with_priority -v`
Expected: PASS

**Step 6: Commit**

```bash
git add balance/src/models.py balance/src/routers/sessions.py balance/tests/test_sessions.py
git commit -m "feat(balance): accept priority_id in session start"
```

---

## Task 9: Settings UI — Priority List

**Files:**
- Modify: `balance/src/templates/_content_settings.html`

**Step 1: Add priorities section to settings template**

Add at the top of the settings container in `_content_settings.html`:

```html
<div class="settings-section">
  <h3 class="settings-section__title">Priorities</h3>
  <p class="text-muted text-sm mb-md">Use arrows to reorder. Expected sessions must be tagged to a priority.</p>

  <div class="priority-list" id="priority-list">
    <!-- Populated by JS -->
  </div>

  <div class="mt-md" id="add-priority-form" style="display: none;">
    <input type="text" class="input" id="new-priority-name" placeholder="Priority name" maxlength="30">
    <div class="button-group mt-sm">
      <button class="btn btn--primary" onclick="savePriority()">Add</button>
      <button class="btn" onclick="hideAddForm()">Cancel</button>
    </div>
  </div>

  <button class="btn btn--full mt-md" id="add-priority-btn" onclick="showAddForm()">+ Add Priority</button>
  <p class="text-muted text-xs mt-sm" id="priority-limit-msg">Max 4 priorities</p>
</div>
```

**Step 2: Verify template renders**

Run: `cd balance && python -m uvicorn src.main:app --reload`
Visit: http://localhost:8005/settings
Expected: See empty priority list section

**Step 3: Commit**

```bash
git add balance/src/templates/_content_settings.html
git commit -m "feat(balance): add priorities section to settings UI"
```

---

## Task 10: Settings UI — Priority JavaScript

**Files:**
- Create: `balance/src/static/js/settings.js`
- Modify: `balance/src/templates/_content_settings.html`

**Step 1: Create settings.js with priority management**

```javascript
// balance/src/static/js/settings.js
const PriorityManager = {
  priorities: [],

  async init() {
    await this.load();
    this.render();
  },

  async load() {
    const response = await fetch('/api/priorities');
    this.priorities = await response.json();
  },

  render() {
    const list = document.getElementById('priority-list');
    const addBtn = document.getElementById('add-priority-btn');
    const limitMsg = document.getElementById('priority-limit-msg');

    if (this.priorities.length === 0) {
      list.innerHTML = '<div class="empty-state"><div class="empty-state__message">No priorities yet</div></div>';
    } else {
      list.innerHTML = this.priorities.map((p, i) => `
        <div class="priority-list__item" data-id="${p.id}">
          <span class="priority-list__rank">${p.rank}</span>
          <span class="priority-list__name">${p.name}</span>
          <span class="priority-list__meta">${p.session_count} sessions</span>
          <span class="priority-list__arrows">
            <button class="priority-list__arrow" data-dir="up" onclick="PriorityManager.move(${p.id}, 'up')" ${i === 0 ? 'disabled' : ''}>&#9650;</button>
            <button class="priority-list__arrow" data-dir="down" onclick="PriorityManager.move(${p.id}, 'down')" ${i === this.priorities.length - 1 ? 'disabled' : ''}>&#9660;</button>
          </span>
        </div>
      `).join('');
    }

    // Hide add button if at max
    if (this.priorities.length >= 4) {
      addBtn.style.display = 'none';
      limitMsg.style.display = 'block';
    } else {
      addBtn.style.display = 'block';
      limitMsg.style.display = this.priorities.length >= 3 ? 'block' : 'none';
    }
  },

  async move(id, direction) {
    const index = this.priorities.findIndex(p => p.id === id);
    const newIndex = direction === 'up' ? index - 1 : index + 1;

    if (newIndex < 0 || newIndex >= this.priorities.length) return;

    // Swap in local array
    [this.priorities[index], this.priorities[newIndex]] =
    [this.priorities[newIndex], this.priorities[index]];

    // Update ranks
    const order = this.priorities.map(p => p.id);
    await fetch('/api/priorities/reorder', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order })
    });

    await this.load();
    this.render();
  },

  async add(name) {
    await fetch('/api/priorities', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    await this.load();
    this.render();
  }
};

function showAddForm() {
  document.getElementById('add-priority-form').style.display = 'block';
  document.getElementById('add-priority-btn').style.display = 'none';
  document.getElementById('new-priority-name').focus();
}

function hideAddForm() {
  document.getElementById('add-priority-form').style.display = 'none';
  document.getElementById('add-priority-btn').style.display = 'block';
  document.getElementById('new-priority-name').value = '';
}

async function savePriority() {
  const name = document.getElementById('new-priority-name').value.trim();
  if (name) {
    await PriorityManager.add(name);
    hideAddForm();
  }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => PriorityManager.init());
```

**Step 2: Include script in settings template**

Add at bottom of `_content_settings.html`:

```html
<script src="/static/js/settings.js"></script>
```

**Step 3: Manual test**

Run: `cd balance && python -m uvicorn src.main:app --reload`
Visit: http://localhost:8005/settings
Test: Add priorities, reorder with arrows
Expected: Priorities persist and reorder correctly

**Step 4: Commit**

```bash
git add balance/src/static/js/settings.js balance/src/templates/_content_settings.html
git commit -m "feat(balance): add priority management JS to settings"
```

---

## Task 11: Timer UI — Priority Dropdown

**Files:**
- Modify: `balance/src/templates/_content_index.html`
- Modify: `balance/src/static/js/timer.js`

**Step 1: Add priority dropdown to timer template**

In `_content_index.html`, after the type selection buttons, add:

```html
<div id="priority-section" style="display: none;">
  <label class="form-group__label">Priority</label>
  <div class="dropdown dropdown--full">
    <button class="btn" id="priority-trigger" onclick="toggleDropdown('priority')">
      <span id="priority-label">Select priority...</span>
      <span>▾</span>
    </button>
    <div class="dropdown__menu" id="dropdown-priority">
      <!-- Populated by JS -->
    </div>
    <div class="dropdown__backdrop" id="backdrop-priority" onclick="closeDropdown('priority')"></div>
  </div>
</div>
```

**Step 2: Add priority handling to timer.js**

Add to the Balance object in `timer.js`:

```javascript
// Add to Balance object properties
priorities: [],
selectedPriorityId: null,

// Add method to load priorities
async loadPriorities() {
  const response = await fetch('/api/priorities');
  this.priorities = await response.json();
  this.renderPriorityDropdown();
},

renderPriorityDropdown() {
  const dropdown = document.getElementById('dropdown-priority');
  if (!dropdown) return;

  dropdown.innerHTML = this.priorities.map(p => `
    <button class="dropdown__item dropdown__item--with-meta" onclick="Balance.selectPriority(${p.id}, '${p.name}')">
      <span>${p.name}</span>
      <span class="dropdown__item-meta">#${p.rank}</span>
    </button>
  `).join('');
},

selectPriority(id, name) {
  this.selectedPriorityId = id;
  document.getElementById('priority-label').textContent = name;
  document.getElementById('priority-trigger').classList.add('selected');
  closeDropdown('priority');
  this.updateStartButton();
},

updateStartButton() {
  const startBtn = document.getElementById('start-btn');
  if (this.sessionType === 'expected') {
    startBtn.disabled = !this.selectedPriorityId;
  } else {
    startBtn.disabled = false;
  }
}
```

**Step 3: Modify type selection to show/hide priority dropdown**

Update the type button click handlers:

```javascript
// When Expected is selected
document.getElementById('priority-section').style.display = 'block';
this.selectedPriorityId = null;
document.getElementById('priority-label').textContent = 'Select priority...';
document.getElementById('priority-trigger').classList.remove('selected');
this.updateStartButton();

// When Personal is selected
document.getElementById('priority-section').style.display = 'none';
this.selectedPriorityId = null;
this.updateStartButton();
```

**Step 4: Include priority_id in session start**

Modify startSession to include priority:

```javascript
body: JSON.stringify({
  type: this.sessionType,
  intention: this.intention || null,
  priority_id: this.sessionType === 'expected' ? this.selectedPriorityId : null
})
```

**Step 5: Call loadPriorities in init**

Add to `init()`:

```javascript
await this.loadPriorities();
```

**Step 6: Manual test**

Run: `cd balance && python -m uvicorn src.main:app --reload`
Test: Select Expected → priority dropdown appears → select priority → start session
Expected: Session starts with priority_id set

**Step 7: Commit**

```bash
git add balance/src/templates/_content_index.html balance/src/static/js/timer.js
git commit -m "feat(balance): add priority dropdown to timer UI"
```

---

## Task 12: Stats API — Drift Calculation

**Files:**
- Modify: `balance/src/routers/sessions.py`
- Modify: `balance/tests/test_sessions.py`

**Step 1: Write failing test for drift endpoint**

```python
# Add to balance/tests/test_sessions.py
@pytest.mark.asyncio
async def test_stats_drift():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/stats/drift")
        assert response.status_code == 200
        data = response.json()
        assert "biggest_drift" in data
        assert "breakdown" in data
```

**Step 2: Run test to verify it fails**

Run: `cd balance && python -m pytest tests/test_sessions.py::test_stats_drift -v`
Expected: FAIL — 404 Not Found

**Step 3: Add drift endpoint**

```python
# Add to balance/src/routers/sessions.py
@router.get("/stats/drift")
async def get_drift_stats():
    async with get_db() as db:
        # Get priorities
        cursor = await db.execute("""
            SELECT id, name, rank FROM priorities
            WHERE archived_at IS NULL ORDER BY rank
        """)
        priorities = await cursor.fetchall()

        if len(priorities) < 2:
            return {"biggest_drift": None, "breakdown": [], "weeks_drifting": 0}

        # Get session counts per priority (this week)
        week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        cursor = await db.execute("""
            SELECT priority_id, COUNT(*) as count
            FROM sessions
            WHERE type = 'expected'
              AND priority_id IS NOT NULL
              AND started_at >= ?
            GROUP BY priority_id
        """, (week_start,))
        counts = {row[0]: row[1] for row in await cursor.fetchall()}

        total = sum(counts.values()) or 1

        # Build breakdown
        breakdown = []
        for p_id, p_name, p_rank in priorities:
            count = counts.get(p_id, 0)
            pct = round(count / total * 100) if total > 0 else 0
            breakdown.append({
                "id": p_id,
                "name": p_name,
                "rank": p_rank,
                "session_count": count,
                "pct": pct
            })

        # Find biggest drift (highest rank priority with lowest %)
        # #1 priority should have most sessions, if not = drift
        biggest_drift = None
        if breakdown:
            # Sort by rank to find #1
            by_rank = sorted(breakdown, key=lambda x: x["rank"])
            by_pct = sorted(breakdown, key=lambda x: x["pct"], reverse=True)

            if by_rank[0]["id"] != by_pct[0]["id"]:
                biggest_drift = {
                    "priority": by_rank[0]["name"],
                    "rank": by_rank[0]["rank"],
                    "pct": by_rank[0]["pct"],
                    "instead": by_pct[0]["name"],
                    "instead_rank": by_pct[0]["rank"],
                    "instead_pct": by_pct[0]["pct"]
                }

        return {
            "biggest_drift": biggest_drift,
            "breakdown": breakdown,
            "weeks_drifting": 0  # TODO: track consecutive weeks
        }
```

**Step 4: Add import**

```python
from datetime import datetime, timedelta
```

**Step 5: Run test to verify it passes**

Run: `cd balance && python -m pytest tests/test_sessions.py::test_stats_drift -v`
Expected: PASS

**Step 6: Commit**

```bash
git add balance/src/routers/sessions.py balance/tests/test_sessions.py
git commit -m "feat(balance): add GET /api/stats/drift endpoint"
```

---

## Task 13: Stats UI — Drift Alert Display

**Files:**
- Modify: `balance/src/templates/_content_stats.html`

**Step 1: Add drift alert section**

Add at the top of `_content_stats.html`, before the stats grid:

```html
<div id="drift-alert" class="drift-alert" style="display: none;">
  <div class="drift-alert__header">Biggest drift</div>
  <div class="drift-alert__main" id="drift-main"></div>
  <div class="drift-alert__context" id="drift-context"></div>
</div>
```

**Step 2: Add drift alert styles (inline for now)**

Add to the `<style>` section or create inline:

```html
<style>
.drift-alert {
  border: 2px solid var(--color-border);
  padding: 1.5rem;
  margin-bottom: 2rem;
}
.drift-alert__header {
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-muted);
  margin-bottom: 0.5rem;
}
.drift-alert__main {
  font-size: var(--font-size-lg);
  line-height: 1.5;
}
.drift-alert__context {
  font-size: var(--font-size-sm);
  color: var(--color-muted);
  padding-top: 1rem;
  margin-top: 1rem;
  border-top: 1px solid var(--color-border-light);
}
.drift-alert__stat {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--color-border);
  margin: 0 0.25rem;
  font-variant-numeric: tabular-nums;
}
</style>
```

**Step 3: Add drift loading to stats JS**

Add to the Stats object in the inline script:

```javascript
async loadDrift() {
  try {
    const data = await fetch('/api/stats/drift').then(r => r.json());

    const alert = document.getElementById('drift-alert');
    if (data.biggest_drift) {
      const d = data.biggest_drift;
      document.getElementById('drift-main').innerHTML = `
        <strong>${d.priority}</strong> is priority #${d.rank} but got
        <span class="drift-alert__stat">${d.pct}%</span> of sessions.
        <strong>${d.instead}</strong> (#${d.instead_rank}) got
        <span class="drift-alert__stat">${d.instead_pct}%</span>.
      `;
      document.getElementById('drift-context').textContent =
        data.weeks_drifting > 1
          ? `This is week ${data.weeks_drifting} of ${d.priority} being deprioritized.`
          : '';
      alert.style.display = 'block';
    } else {
      alert.style.display = 'none';
    }
  } catch (err) {
    console.error('Failed to load drift:', err);
  }
}
```

**Step 4: Call loadDrift in init**

```javascript
init() {
  this.bindEvents();
  this.loadStats();
  this.loadNorthStar();
  this.loadDrift();  // Add this
}
```

**Step 5: Manual test**

Run: `cd balance && python -m uvicorn src.main:app --reload`
Create priorities, run some sessions with different priorities
Visit: http://localhost:8005/stats
Expected: Drift alert shows if #1 priority isn't getting most sessions

**Step 6: Commit**

```bash
git add balance/src/templates/_content_stats.html
git commit -m "feat(balance): add drift alert to stats UI"
```

---

## Task 14: Move Drift Alert to Shared Components

**Files:**
- Modify: `shared/css/components.css`
- Modify: `shared/templates/components.html`
- Modify: `docs/COMPONENT-LIBRARY.md`
- Modify: `balance/src/templates/_content_stats.html`

**Step 1: Add drift-alert CSS to shared components**

Add to `shared/css/components.css`:

```css
/* ==========================================================================
   DRIFT ALERT
   Insight card showing priority misalignment
   ========================================================================== */

.drift-alert {
  border: 2px solid var(--color-border);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
}

.drift-alert__header {
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-muted);
  margin-bottom: var(--space-sm);
}

.drift-alert__main {
  font-size: var(--font-size-lg);
  line-height: 1.5;
}

.drift-alert__context {
  font-size: var(--font-size-sm);
  color: var(--color-muted);
  padding-top: var(--space-md);
  margin-top: var(--space-md);
  border-top: 1px solid var(--color-border-light);
}

.drift-alert__stat {
  display: inline-block;
  padding: var(--space-xs) var(--space-sm);
  border: 1px solid var(--color-border);
  margin: 0 var(--space-xs);
  font-variant-numeric: tabular-nums;
}
```

**Step 2: Add Jinja macro**

Add to `shared/templates/components.html`:

```jinja2
{# ==========================================================================
   DRIFT ALERT
   Insight card showing priority misalignment

   {{ ui.drift_alert(priority="Thesis", rank=1, pct=18, instead="Work", instead_rank=3, instead_pct=73, weeks=3) }}
   ========================================================================== #}
{% macro drift_alert(priority, rank, pct, instead, instead_rank, instead_pct, weeks=0) %}
<div class="drift-alert">
  <div class="drift-alert__header">Biggest drift</div>
  <div class="drift-alert__main">
    <strong>{{ priority }}</strong> is priority #{{ rank }} but got
    <span class="drift-alert__stat">{{ pct }}%</span> of sessions.
    <strong>{{ instead }}</strong> (#{{ instead_rank }}) got
    <span class="drift-alert__stat">{{ instead_pct }}%</span>.
  </div>
  {% if weeks > 1 %}
  <div class="drift-alert__context">
    This is week {{ weeks }} of {{ priority }} being deprioritized.
  </div>
  {% endif %}
</div>
{% endmacro %}
```

**Step 3: Update component library docs**

Add to CSS Classes table in `docs/COMPONENT-LIBRARY.md`:

```markdown
| Drift Alert | `.drift-alert`, `.drift-alert__header`, `.drift-alert__main`, `.drift-alert__context`, `.drift-alert__stat` |
```

**Step 4: Remove inline styles from stats template**

Remove the `<style>` block with drift-alert styles from `_content_stats.html` (now in shared).

**Step 5: Commit**

```bash
git add shared/css/components.css shared/templates/components.html docs/COMPONENT-LIBRARY.md balance/src/templates/_content_stats.html
git commit -m "feat(shared): add drift-alert component to shared library"
```

---

## Task 15: Clean Up Mockup Route

**Files:**
- Modify: `balance/src/main.py`

**Step 1: Make mockup route dev-only**

```python
import os

# After other routes, add:
if os.getenv("DEV_MODE") == "true":
    @app.get("/mockup", response_class=HTMLResponse)
    async def mockup_page(request: Request):
        """UI mockup for design iteration (dev only)."""
        return templates.TemplateResponse("mockup.html", {"request": request})
```

**Step 2: Test in dev mode**

Run: `DEV_MODE=true python -m uvicorn src.main:app --reload`
Visit: http://localhost:8005/mockup
Expected: Mockup page loads

**Step 3: Test in prod mode**

Run: `python -m uvicorn src.main:app --reload`
Visit: http://localhost:8005/mockup
Expected: 404 Not Found

**Step 4: Commit**

```bash
git add balance/src/main.py
git commit -m "feat(balance): make /mockup route dev-only"
```

---

Plan complete and saved to `docs/plans/2026-01-01-priority-drift-detection-plan.md`.

**Two execution options:**

1. **Subagent-Driven (this session)** — I dispatch fresh subagent per task, review between tasks, fast iteration

2. **Parallel Session (separate)** — Open new session with executing-plans, batch execution with checkpoints

Which approach?