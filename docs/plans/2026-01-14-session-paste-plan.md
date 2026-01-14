# Session Paste Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow users to paste WhatsApp session summaries directly into the Train app UI.

**Architecture:** Add `SessionLog` model for raw text storage, create `/api/sessions/log` endpoint, update `/api/context` to return sessions, rebuild `/log` page with textarea.

**Tech Stack:** FastAPI, SQLAlchemy (aiosqlite), Jinja2, vanilla JS

---

## Task 1: Add SessionLog Model

**Files:**
- Modify: `train/src/models.py`
- Test: `train/tests/test_database.py`

**Step 1: Write failing test for SessionLog model**

Add to `train/tests/test_database.py`:

```python
import pytest
from datetime import date
from sqlalchemy import select
from src.database import init_db, get_db
from src.models import SessionLog


@pytest.fixture
async def db_session():
    await init_db("sqlite+aiosqlite:///:memory:")
    async for session in get_db():
        yield session


@pytest.mark.asyncio
async def test_session_log_model(db_session):
    log = SessionLog(
        session_date=date(2026, 1, 12),
        raw_text="BENCH PRESS\n- Set 1: 8 reps × 70kg"
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(select(SessionLog))
    saved = result.scalars().first()

    assert saved.session_date == date(2026, 1, 12)
    assert "BENCH PRESS" in saved.raw_text
    assert saved.created_at is not None
```

**Step 2: Run test to verify it fails**

Run: `cd train && python -m pytest tests/test_database.py::test_session_log_model -v`

Expected: FAIL with `ImportError: cannot import name 'SessionLog'`

**Step 3: Add SessionLog model**

Add to `train/src/models.py` after the `SetEntry` class:

```python
class SessionLog(Base):
    __tablename__ = "session_logs"

    id = Column(Integer, primary_key=True)
    session_date = Column(Date, nullable=False)
    raw_text = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
```

Also add `Date` to the imports at the top:

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text, Date
```

**Step 4: Run test to verify it passes**

Run: `cd train && python -m pytest tests/test_database.py::test_session_log_model -v`

Expected: PASS

**Step 5: Commit**

```bash
git add train/src/models.py train/tests/test_database.py
git commit -m "feat(train): add SessionLog model for raw text storage"
```

---

## Task 2: Add Log Session API Endpoint

**Files:**
- Modify: `train/src/routers/sessions.py`
- Modify: `train/src/schemas.py`
- Test: `train/tests/test_sessions_api.py`

**Step 1: Write failing test for log endpoint**

Add to `train/tests/test_sessions_api.py`:

```python
def test_log_session_with_date_in_text():
    with TestClient(app) as client:
        response = client.post("/api/sessions/log", json={
            "text": "BENCH PRESS (2026-01-12)\n- Set 1: 8 reps × 70kg"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["session_date"] == "2026-01-12"
        assert data["id"] is not None


def test_log_session_with_date_override():
    with TestClient(app) as client:
        response = client.post("/api/sessions/log", json={
            "text": "BENCH PRESS (2026-01-12)\n- Set 1: 8 reps × 70kg",
            "date": "2026-01-10"
        })
        assert response.status_code == 200
        assert response.json()["session_date"] == "2026-01-10"


def test_log_session_no_date_uses_today():
    from datetime import date
    with TestClient(app) as client:
        response = client.post("/api/sessions/log", json={
            "text": "BENCH PRESS\n- Set 1: 8 reps × 70kg"
        })
        assert response.status_code == 200
        assert response.json()["session_date"] == str(date.today())
```

**Step 2: Run tests to verify they fail**

Run: `cd train && python -m pytest tests/test_sessions_api.py::test_log_session_with_date_in_text -v`

Expected: FAIL with `404 Not Found`

**Step 3: Add schema**

Add to `train/src/schemas.py`:

```python
from datetime import date as date_type


class SessionLogCreate(BaseModel):
    text: str
    date: date_type | None = None


class SessionLogResponse(BaseModel):
    id: int
    session_date: str
    created_at: str
```

**Step 4: Add endpoint**

Add to `train/src/routers/sessions.py`:

```python
import re
from datetime import date
from src.models import Session, SessionLog
from src.schemas import SessionLogCreate, SessionLogResponse


def parse_session_date(text: str) -> date:
    """Extract date from first (YYYY-MM-DD) pattern in text."""
    match = re.search(r'\((\d{4}-\d{2}-\d{2})\)', text)
    if match:
        try:
            return date.fromisoformat(match.group(1))
        except ValueError:
            pass
    return date.today()


@router.post("/log", response_model=SessionLogResponse)
async def log_session(payload: SessionLogCreate, session: AsyncSession = Depends(get_db)):
    session_date = payload.date if payload.date else parse_session_date(payload.text)

    log = SessionLog(
        session_date=session_date,
        raw_text=payload.text
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)

    return SessionLogResponse(
        id=log.id,
        session_date=str(log.session_date),
        created_at=str(log.created_at)
    )
```

Also update imports at top of file:

```python
from src.models import Session, SessionLog
```

**Step 5: Run tests to verify they pass**

Run: `cd train && python -m pytest tests/test_sessions_api.py -v`

Expected: All PASS

**Step 6: Commit**

```bash
git add train/src/routers/sessions.py train/src/schemas.py train/tests/test_sessions_api.py
git commit -m "feat(train): add POST /api/sessions/log endpoint"
```

---

## Task 3: Add Context API Endpoint

**Files:**
- Create: `train/src/routers/context.py`
- Modify: `train/src/main.py`
- Create: `train/tests/test_context_api.py`

**Step 1: Write failing test for context endpoint**

Create `train/tests/test_context_api.py`:

```python
from datetime import date
from fastapi.testclient import TestClient
from src.main import app


def test_context_returns_plan_and_sessions():
    with TestClient(app) as client:
        # Create a plan first
        client.post("/api/plan/register", json={
            "title": "Test Plan",
            "markdown": "# Test"
        })

        # Log a session
        client.post("/api/sessions/log", json={
            "text": "BENCH PRESS (2026-01-12)\n- Set 1: 8 reps",
            "date": "2026-01-12"
        })

        # Get context
        response = client.get("/api/context")
        assert response.status_code == 200

        data = response.json()
        assert "plan" in data
        assert data["plan"]["title"] == "Test Plan"
        assert "sessions" in data
        assert len(data["sessions"]) >= 1
        assert data["sessions"][0]["date"] == "2026-01-12"


def test_context_sessions_sorted_newest_first():
    with TestClient(app) as client:
        client.post("/api/sessions/log", json={"text": "OLD", "date": "2026-01-01"})
        client.post("/api/sessions/log", json={"text": "NEW", "date": "2026-01-15"})

        response = client.get("/api/context")
        sessions = response.json()["sessions"]

        dates = [s["date"] for s in sessions]
        assert dates == sorted(dates, reverse=True)
```

**Step 2: Run test to verify it fails**

Run: `cd train && python -m pytest tests/test_context_api.py::test_context_returns_plan_and_sessions -v`

Expected: FAIL with `404 Not Found`

**Step 3: Create context router**

Create `train/src/routers/context.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models import Plan, SessionLog

router = APIRouter(prefix="/api", tags=["context"])


@router.get("/context")
async def get_context(session: AsyncSession = Depends(get_db)):
    # Get current plan
    plan_result = await session.execute(
        select(Plan).order_by(desc(Plan.created_at))
    )
    plan = plan_result.scalars().first()

    plan_data = None
    if plan:
        try:
            with open(plan.markdown_path, "r", encoding="utf-8") as f:
                markdown = f.read()
        except FileNotFoundError:
            markdown = ""
        plan_data = {
            "id": plan.id,
            "title": plan.title,
            "markdown": markdown
        }

    # Get all session logs
    sessions_result = await session.execute(
        select(SessionLog).order_by(desc(SessionLog.session_date))
    )
    sessions = sessions_result.scalars().all()

    sessions_data = [
        {
            "id": s.id,
            "date": str(s.session_date),
            "text": s.raw_text
        }
        for s in sessions
    ]

    return {
        "plan": plan_data,
        "sessions": sessions_data
    }
```

**Step 4: Register router in main.py**

Add to `train/src/main.py` imports:

```python
from src.routers import ui, plans, sessions, sets, context
```

Add at end of file:

```python
app.include_router(context.router)
```

**Step 5: Run tests to verify they pass**

Run: `cd train && python -m pytest tests/test_context_api.py -v`

Expected: All PASS

**Step 6: Commit**

```bash
git add train/src/routers/context.py train/src/main.py train/tests/test_context_api.py
git commit -m "feat(train): add GET /api/context endpoint"
```

---

## Task 4: Update Log Page UI

**Files:**
- Modify: `train/src/templates/log.html`
- Modify: `train/src/static/js/log.js`
- Modify: `train/src/routers/ui.py`

**Step 1: Update log.html template**

Replace `train/src/templates/log.html` with:

```html
{% extends "base.html" %}
{% import "components.html" as ui %}
{% block content %}
{% call ui.card() %}
  <h2>Log Session</h2>
  <form id="log-form">
    {% call ui.form_group("Paste workout summary", "session-text") %}
      {{ ui.textarea("session-text", placeholder="BENCH PRESS (2026-01-12)\n- Set 1: 8 reps × 70kg\n...", rows=10) }}
    {% endcall %}
    {% call ui.form_group("Date", "session-date", help="Auto-detected from text, edit if needed") %}
      {{ ui.input("session-date", type="date") }}
    {% endcall %}
    {{ ui.button("Save Session", primary=true, type="submit") }}
  </form>
{% endcall %}

{% call ui.card() %}
  <h2>Recent Sessions</h2>
  <div id="recent-sessions" class="list">
    <p class="text-muted">Loading...</p>
  </div>
{% endcall %}
{% endblock %}

{% block scripts %}
<script src="{{ base_path }}/static/js/log.js"></script>
{% endblock %}
```

**Step 2: Update log.js**

Replace `train/src/static/js/log.js` with:

```javascript
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('log-form');
  const textarea = document.getElementById('session-text');
  const dateInput = document.getElementById('session-date');
  const recentDiv = document.getElementById('recent-sessions');

  // Set default date to today
  dateInput.value = new Date().toISOString().split('T')[0];

  // Auto-detect date from pasted text
  textarea.addEventListener('input', () => {
    const match = textarea.value.match(/\((\d{4}-\d{2}-\d{2})\)/);
    if (match) {
      dateInput.value = match[1];
    }
  });

  // Handle form submission
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const text = textarea.value.trim();
    if (!text) {
      alert('Please paste a workout summary');
      return;
    }

    try {
      const response = await fetch('/api/sessions/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          date: dateInput.value
        })
      });

      if (!response.ok) throw new Error('Failed to save');

      textarea.value = '';
      dateInput.value = new Date().toISOString().split('T')[0];
      loadRecentSessions();
    } catch (err) {
      alert('Error saving session: ' + err.message);
    }
  });

  // Load recent sessions
  async function loadRecentSessions() {
    try {
      const response = await fetch('/api/context');
      const data = await response.json();

      if (!data.sessions || data.sessions.length === 0) {
        recentDiv.innerHTML = '<p class="text-muted">No sessions logged yet</p>';
        return;
      }

      recentDiv.innerHTML = data.sessions.map(s => {
        const exercises = extractExercises(s.text);
        return `
          <div class="list-item">
            <strong>${s.date}</strong>
            <span class="text-muted">${exercises}</span>
          </div>
        `;
      }).join('');
    } catch (err) {
      recentDiv.innerHTML = '<p class="text-muted">Error loading sessions</p>';
    }
  }

  function extractExercises(text) {
    const lines = text.split('\n');
    const exercises = lines
      .filter(line => line.match(/^[A-Z]/))
      .map(line => line.replace(/\s*\(.*\)/, '').trim())
      .slice(0, 3);
    return exercises.join(', ') || 'Session';
  }

  loadRecentSessions();
});
```

**Step 3: Run dev server and test manually**

Run: `cd train && uvicorn src.main:app --reload --port 8006`

Test in browser at `http://localhost:8006/log`

**Step 4: Commit**

```bash
git add train/src/templates/log.html train/src/static/js/log.js
git commit -m "feat(train): update log page with paste-and-save UI"
```

---

## Task 5: Add E2E UI Test

**Files:**
- Modify: `tests/e2e/ui/test_train.py` (create if needed)

**Step 1: Create UI test**

Create `tests/e2e/ui/test_train.py`:

```python
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://train.gstoehl.dev/dev"


def test_log_page_paste_session(page: Page):
    """Test pasting a session summary and saving it."""
    page.goto(f"{BASE_URL}/log")

    # Should have textarea and date input
    textarea = page.locator("#session-text")
    date_input = page.locator("#session-date")
    expect(textarea).to_be_visible()
    expect(date_input).to_be_visible()

    # Paste session text
    session_text = """BENCH PRESS (2026-01-12)
- Set 1: 8 reps × 70kg
- Set 2: 6 reps × 75kg

PULLUPS
- Set 1: 8 reps × bodyweight"""

    textarea.fill(session_text)

    # Date should auto-detect
    expect(date_input).to_have_value("2026-01-12")

    # Submit form
    page.click("button[type=submit]")

    # Textarea should clear
    expect(textarea).to_have_value("")

    # Session should appear in recent list
    expect(page.locator("#recent-sessions")).to_contain_text("2026-01-12")
    expect(page.locator("#recent-sessions")).to_contain_text("BENCH PRESS")
```

**Step 2: Run test**

Run: `pytest tests/e2e/ui/test_train.py -v`

Expected: PASS (after deploying to dev)

**Step 3: Commit**

```bash
git add tests/e2e/ui/test_train.py
git commit -m "test(train): add E2E test for session paste feature"
```

---

## Task 6: Final Integration Test

**Step 1: Deploy to dev**

```bash
git push origin dev
```

Wait for CI to complete.

**Step 2: Test via browser**

1. Navigate to `https://train.gstoehl.dev/dev/log`
2. Paste a WhatsApp session summary
3. Verify date auto-detects
4. Click Save Session
5. Verify session appears in recent list

**Step 3: Test context API**

```bash
curl https://train.gstoehl.dev/dev/api/context | jq
```

Should return plan + all sessions.

**Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix(train): address integration test issues"
git push origin dev
```

---

## Summary

| Task | Files | Tests |
|------|-------|-------|
| 1. SessionLog model | models.py | test_database.py |
| 2. Log session endpoint | sessions.py, schemas.py | test_sessions_api.py |
| 3. Context endpoint | context.py, main.py | test_context_api.py |
| 4. Log page UI | log.html, log.js | manual |
| 5. E2E test | test_train.py | automated |
| 6. Integration | deploy | manual + curl |
