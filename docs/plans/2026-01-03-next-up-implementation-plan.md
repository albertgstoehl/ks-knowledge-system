# Next Up Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a max-5 task capture list to Balance for quick todo collection during focus sessions.

**Architecture:** CRUD API for `next_up` table (already exists in schema). Pydantic models for validation. Home screen shows list + capture input. Sessions link to tasks via `next_up_id` column.

**Tech Stack:** Python/FastAPI, aiosqlite, Pydantic, pytest/httpx

**Design Doc:** `docs/plans/2026-01-03-next-up-design.md`

---

## Task 1: NextUp Pydantic Models

**Files:**
- Modify: `balance/src/models.py`

**Step 1: Add NextUp models to models.py**

Add at the end of `balance/src/models.py`:

```python
# NextUp models
class NextUp(BaseModel):
    id: int
    text: str
    due_date: Optional[str] = None
    priority_id: Optional[int] = None
    priority_name: Optional[str] = None
    created_at: str
    session_count: int = 0


class NextUpCreate(BaseModel):
    text: str
    due_date: Optional[str] = None
    priority_id: Optional[int] = None


class NextUpUpdate(BaseModel):
    text: Optional[str] = None
    due_date: Optional[str] = None
    priority_id: Optional[int] = None
    clear_due_date: bool = False
    clear_priority: bool = False


class NextUpList(BaseModel):
    items: list[NextUp]
    count: int
    max: int = 5
```

**Step 2: Commit**

```bash
git add balance/src/models.py
git commit -m "feat(balance): add NextUp pydantic models"
```

---

## Task 2: List NextUp Endpoint - Test First

**Files:**
- Create: `balance/tests/test_nextup.py`

**Step 1: Write the failing test**

Create `balance/tests/test_nextup.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
import os

assert "DATABASE_URL" in os.environ, "Run tests with DATABASE_URL=./data/test.db"

from src.database import init_db, get_db
from src.main import app

_db_initialized = False


@pytest.fixture(autouse=True)
async def setup_test():
    """Initialize database and cleanup between tests."""
    global _db_initialized
    if not _db_initialized:
        await init_db()
        _db_initialized = True

    async with get_db() as db:
        await db.execute("DELETE FROM next_up")
        await db.execute("DELETE FROM sessions")
        await db.execute("DELETE FROM priorities")
        await db.commit()
    yield


async def test_list_nextup_empty():
    """Test listing next_up when empty."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/nextup")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["count"] == 0
        assert data["max"] == 5
```

**Step 2: Run test to verify it fails**

```bash
cd balance && DATABASE_URL=./data/test.db pytest tests/test_nextup.py::test_list_nextup_empty -v
```

Expected: FAIL with 404 (endpoint doesn't exist)

**Step 3: Commit failing test**

```bash
git add balance/tests/test_nextup.py
git commit -m "test(balance): add failing test for list nextup endpoint"
```

---

## Task 3: List NextUp Endpoint - Implementation

**Files:**
- Create: `balance/src/routers/nextup.py`
- Modify: `balance/src/main.py`

**Step 1: Create router with list endpoint**

Create `balance/src/routers/nextup.py`:

```python
from fastapi import APIRouter

from ..database import get_db
from ..models import NextUp, NextUpList

router = APIRouter(prefix="/api/nextup", tags=["nextup"])

MAX_ITEMS = 5


@router.get("", response_model=NextUpList)
async def list_nextup() -> NextUpList:
    """List all Next Up items, sorted by due_date (nulls last), then created_at."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT n.id, n.text, n.due_date, n.priority_id, n.created_at,
                   p.name as priority_name,
                   COUNT(s.id) as session_count
            FROM next_up n
            LEFT JOIN priorities p ON p.id = n.priority_id
            LEFT JOIN sessions s ON s.next_up_id = n.id
            GROUP BY n.id
            ORDER BY
                n.due_date IS NULL,
                n.due_date,
                n.created_at
        """)
        rows = await cursor.fetchall()
        items = [
            NextUp(
                id=row[0],
                text=row[1],
                due_date=row[2],
                priority_id=row[3],
                created_at=row[4],
                priority_name=row[5],
                session_count=row[6]
            )
            for row in rows
        ]
        return NextUpList(items=items, count=len(items), max=MAX_ITEMS)
```

**Step 2: Register router in main.py**

In `balance/src/main.py`, add import with other router imports:

```python
from .routers import nextup
```

And register after other routers:

```python
app.include_router(nextup.router)
```

**Step 3: Run test to verify it passes**

```bash
cd balance && DATABASE_URL=./data/test.db pytest tests/test_nextup.py::test_list_nextup_empty -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add balance/src/routers/nextup.py balance/src/main.py
git commit -m "feat(balance): add list nextup endpoint"
```

---

## Task 4: Create NextUp - Test First

**Files:**
- Modify: `balance/tests/test_nextup.py`

**Step 1: Write the failing test**

Add to `test_nextup.py`:

```python
async def test_create_nextup():
    """Test creating a next_up item."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/nextup", json={"text": "Do taxes"})
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Do taxes"
        assert data["id"] is not None


async def test_create_nextup_max_limit():
    """Test that creating beyond max fails."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create 5 items
        for i in range(5):
            response = await client.post("/api/nextup", json={"text": f"Task {i}"})
            assert response.status_code == 200

        # 6th should fail
        response = await client.post("/api/nextup", json={"text": "Task 6"})
        assert response.status_code == 400
        assert "Maximum" in response.json()["detail"]
```

**Step 2: Run test to verify it fails**

```bash
cd balance && DATABASE_URL=./data/test.db pytest tests/test_nextup.py::test_create_nextup -v
```

Expected: FAIL (endpoint doesn't accept POST)

**Step 3: Commit failing test**

```bash
git add balance/tests/test_nextup.py
git commit -m "test(balance): add failing tests for create nextup"
```

---

## Task 5: Create NextUp - Implementation

**Files:**
- Modify: `balance/src/routers/nextup.py`

**Step 1: Add create endpoint**

Add to `nextup.py`:

```python
from fastapi import HTTPException
from ..models import NextUp, NextUpList, NextUpCreate


@router.post("", response_model=NextUp)
async def create_nextup(data: NextUpCreate) -> NextUp:
    """Create a new Next Up item. Fails if already at max capacity."""
    async with get_db() as db:
        # Check count
        cursor = await db.execute("SELECT COUNT(*) FROM next_up")
        count = (await cursor.fetchone())[0]
        if count >= MAX_ITEMS:
            raise HTTPException(status_code=400, detail=f"Maximum {MAX_ITEMS} items allowed")

        # Validate priority if provided
        priority_name = None
        if data.priority_id:
            cursor = await db.execute(
                "SELECT name FROM priorities WHERE id = ? AND archived_at IS NULL",
                (data.priority_id,)
            )
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="Priority not found")
            priority_name = row[0]

        # Insert
        cursor = await db.execute(
            "INSERT INTO next_up (text, due_date, priority_id) VALUES (?, ?, ?)",
            (data.text, data.due_date, data.priority_id)
        )
        await db.commit()
        item_id = cursor.lastrowid

        # Fetch created item
        cursor = await db.execute(
            "SELECT id, text, due_date, priority_id, created_at FROM next_up WHERE id = ?",
            (item_id,)
        )
        row = await cursor.fetchone()

        return NextUp(
            id=row[0],
            text=row[1],
            due_date=row[2],
            priority_id=row[3],
            created_at=row[4],
            priority_name=priority_name,
            session_count=0
        )
```

**Step 2: Run tests to verify they pass**

```bash
cd balance && DATABASE_URL=./data/test.db pytest tests/test_nextup.py -v
```

Expected: All PASS

**Step 3: Commit**

```bash
git add balance/src/routers/nextup.py
git commit -m "feat(balance): add create nextup endpoint with max limit"
```

---

## Task 6: Delete NextUp - Test and Implementation

**Files:**
- Modify: `balance/tests/test_nextup.py`
- Modify: `balance/src/routers/nextup.py`

**Step 1: Write the failing test**

Add to `test_nextup.py`:

```python
async def test_delete_nextup():
    """Test deleting a next_up item."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create item
        create_resp = await client.post("/api/nextup", json={"text": "To delete"})
        item_id = create_resp.json()["id"]

        # Delete it
        response = await client.delete(f"/api/nextup/{item_id}")
        assert response.status_code == 200

        # Verify it's gone
        list_resp = await client.get("/api/nextup")
        assert list_resp.json()["count"] == 0
```

**Step 2: Run test to verify it fails**

```bash
cd balance && DATABASE_URL=./data/test.db pytest tests/test_nextup.py::test_delete_nextup -v
```

Expected: FAIL (endpoint doesn't exist)

**Step 3: Add delete endpoint**

Add to `nextup.py`:

```python
@router.delete("/{item_id}")
async def delete_nextup(item_id: int):
    """Delete a Next Up item."""
    async with get_db() as db:
        cursor = await db.execute("SELECT id FROM next_up WHERE id = ?", (item_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Item not found")

        await db.execute("DELETE FROM next_up WHERE id = ?", (item_id,))
        await db.commit()
    return {"deleted": True}
```

**Step 4: Run test to verify it passes**

```bash
cd balance && DATABASE_URL=./data/test.db pytest tests/test_nextup.py::test_delete_nextup -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add balance/tests/test_nextup.py balance/src/routers/nextup.py
git commit -m "feat(balance): add delete nextup endpoint"
```

---

## Task 7: Update NextUp - Test and Implementation

**Files:**
- Modify: `balance/tests/test_nextup.py`
- Modify: `balance/src/routers/nextup.py`

**Step 1: Write the failing test**

Add to `test_nextup.py`:

```python
async def test_update_nextup():
    """Test updating a next_up item."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create item
        create_resp = await client.post("/api/nextup", json={"text": "Original"})
        item_id = create_resp.json()["id"]

        # Update it
        response = await client.put(
            f"/api/nextup/{item_id}",
            json={"text": "Updated", "due_date": "2026-01-15"}
        )
        assert response.status_code == 200
        assert response.json()["text"] == "Updated"

        # Verify in list
        list_resp = await client.get("/api/nextup")
        items = list_resp.json()["items"]
        assert items[0]["text"] == "Updated"
        assert items[0]["due_date"] == "2026-01-15"
```

**Step 2: Run test to verify it fails**

```bash
cd balance && DATABASE_URL=./data/test.db pytest tests/test_nextup.py::test_update_nextup -v
```

Expected: FAIL

**Step 3: Add update endpoint**

Add to `nextup.py`:

```python
from ..models import NextUp, NextUpList, NextUpCreate, NextUpUpdate


@router.put("/{item_id}", response_model=NextUp)
async def update_nextup(item_id: int, data: NextUpUpdate) -> NextUp:
    """Update a Next Up item."""
    async with get_db() as db:
        cursor = await db.execute("SELECT id FROM next_up WHERE id = ?", (item_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Item not found")

        updates = []
        params = []

        if data.text is not None:
            updates.append("text = ?")
            params.append(data.text)

        if data.due_date is not None:
            updates.append("due_date = ?")
            params.append(data.due_date)
        elif data.clear_due_date:
            updates.append("due_date = NULL")

        if data.priority_id is not None:
            # Validate priority
            cursor = await db.execute(
                "SELECT id FROM priorities WHERE id = ? AND archived_at IS NULL",
                (data.priority_id,)
            )
            if not await cursor.fetchone():
                raise HTTPException(status_code=400, detail="Priority not found")
            updates.append("priority_id = ?")
            params.append(data.priority_id)
        elif data.clear_priority:
            updates.append("priority_id = NULL")

        if updates:
            params.append(item_id)
            await db.execute(
                f"UPDATE next_up SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await db.commit()

        # Fetch updated item
        cursor = await db.execute("""
            SELECT n.id, n.text, n.due_date, n.priority_id, n.created_at,
                   p.name as priority_name,
                   COUNT(s.id) as session_count
            FROM next_up n
            LEFT JOIN priorities p ON p.id = n.priority_id
            LEFT JOIN sessions s ON s.next_up_id = n.id
            WHERE n.id = ?
            GROUP BY n.id
        """, (item_id,))
        row = await cursor.fetchone()

        return NextUp(
            id=row[0],
            text=row[1],
            due_date=row[2],
            priority_id=row[3],
            created_at=row[4],
            priority_name=row[5],
            session_count=row[6]
        )
```

**Step 4: Run test to verify it passes**

```bash
cd balance && DATABASE_URL=./data/test.db pytest tests/test_nextup.py::test_update_nextup -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add balance/tests/test_nextup.py balance/src/routers/nextup.py
git commit -m "feat(balance): add update nextup endpoint"
```

---

## Task 8: Session Integration - Add next_up_id Column

**Files:**
- Modify: `balance/src/database.py`

**Step 1: Add migration for next_up_id column**

In `balance/src/database.py`, add migration after other migrations (around line 170):

```python
        # Migration: add next_up_id if missing (for existing DBs)
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN next_up_id INTEGER REFERENCES next_up(id)")
        except Exception:
            pass  # Column already exists
```

**Step 2: Run app to apply migration**

```bash
cd balance && python -c "import asyncio; from src.database import init_db; asyncio.run(init_db())"
```

**Step 3: Commit**

```bash
git add balance/src/database.py
git commit -m "feat(balance): add next_up_id column to sessions"
```

---

## Task 9: Session Start with next_up_id - Test and Implementation

**Files:**
- Modify: `balance/tests/test_nextup.py`
- Modify: `balance/src/routers/sessions.py`

**Step 1: Write the failing test**

Add to `test_nextup.py`:

```python
async def test_start_session_with_nextup():
    """Test starting a session linked to a next_up item."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create next_up item
        create_resp = await client.post("/api/nextup", json={"text": "Work on feature"})
        item_id = create_resp.json()["id"]

        # Start session with next_up_id
        response = await client.post("/api/sessions/start", json={
            "type": "expected",
            "intention": "Work on feature",
            "next_up_id": item_id
        })
        assert response.status_code == 200

        # Verify session count on next_up item
        list_resp = await client.get("/api/nextup")
        items = list_resp.json()["items"]
        assert items[0]["session_count"] == 1
```

**Step 2: Run test to verify it fails**

```bash
cd balance && DATABASE_URL=./data/test.db pytest tests/test_nextup.py::test_start_session_with_nextup -v
```

Expected: FAIL (next_up_id not accepted)

**Step 3: Update SessionStart model**

In `balance/src/models.py`, update `SessionStart`:

```python
class SessionStart(BaseModel):
    type: Literal["expected", "personal"]
    intention: Optional[str] = None
    priority_id: Optional[int] = None
    next_up_id: Optional[int] = None
```

**Step 4: Update sessions router**

In `balance/src/routers/sessions.py`, in the `start_session` function, update the INSERT statement to include `next_up_id`:

Find the INSERT statement and update to:

```python
        cursor = await db.execute(
            """INSERT INTO sessions (type, intention, priority_id, next_up_id, started_at)
               VALUES (?, ?, ?, ?, ?)""",
            (data.type, data.intention, data.priority_id, data.next_up_id, datetime.now().isoformat())
        )
```

**Step 5: Run test to verify it passes**

```bash
cd balance && DATABASE_URL=./data/test.db pytest tests/test_nextup.py::test_start_session_with_nextup -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add balance/src/models.py balance/src/routers/sessions.py balance/tests/test_nextup.py
git commit -m "feat(balance): link sessions to next_up items"
```

---

## Task 10: Run All Tests

**Step 1: Run full test suite**

```bash
cd balance && DATABASE_URL=./data/test.db pytest tests/ -v
```

Expected: All PASS

**Step 2: Commit if any fixes needed**

```bash
git add -A
git commit -m "fix(balance): test fixes"
```

---

## Summary

| Task | What |
|------|------|
| 1 | Pydantic models |
| 2 | List endpoint test |
| 3 | List endpoint impl |
| 4 | Create endpoint test |
| 5 | Create endpoint impl |
| 6 | Delete endpoint |
| 7 | Update endpoint |
| 8 | DB migration for next_up_id |
| 9 | Session integration |
| 10 | Full test run |

**UI tasks not included** - implement after API is solid. See mockup at `/mockup` (with `DEV_MODE=true`).
