# Train UI Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild Train UI with mobile-first workout logging, plan-driven exercises, pre-filled set entry, and progression graphs.

**Architecture:** Replace current static templates with dynamic HTMX-powered UI. Add `.markdown-content` and `.chart` components to shared library. Extend API with `/api/exercises` endpoint. Templates fetch data from existing API endpoints.

**Tech Stack:** Python/FastAPI, Jinja2, HTMX, shared CSS components, vanilla JS for charts

---

## Task 1: Add `.markdown-content` Component to Shared Library

**Files:**
- Modify: `shared/css/components.css`
- Modify: `shared/styleguide.html`
- Modify: `docs/COMPONENT-LIBRARY.md`

**Step 1: Add CSS to components.css**

Add at end of `shared/css/components.css`:

```css
/* ==========================================================================
   MARKDOWN CONTENT
   Container for rendered markdown with proper typography
   ========================================================================== */

.markdown-content {
  background: var(--color-bg);
  padding: var(--space-md);
  border: 2px solid var(--color-border);
  font-size: var(--font-size-base);
  line-height: 1.6;
  overflow-y: auto;
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3 {
  margin-top: var(--space-lg);
  margin-bottom: var(--space-sm);
  font-weight: 700;
}

.markdown-content h1 { font-size: var(--font-size-xl); }
.markdown-content h2 { font-size: var(--font-size-lg); }
.markdown-content h3 { font-size: var(--font-size-base); }

.markdown-content p {
  margin: var(--space-sm) 0;
}

.markdown-content table {
  width: 100%;
  border-collapse: collapse;
  margin: var(--space-md) 0;
  font-size: var(--font-size-sm);
}

.markdown-content th,
.markdown-content td {
  border: 1px solid var(--color-border);
  padding: var(--space-sm);
  text-align: left;
}

.markdown-content th {
  font-weight: 700;
  background: var(--color-hover);
}

.markdown-content ul,
.markdown-content ol {
  padding-left: var(--space-lg);
  margin: var(--space-sm) 0;
}

.markdown-content li {
  margin: var(--space-xs) 0;
}

.markdown-content strong {
  font-weight: 700;
}

.markdown-content code {
  background: var(--color-hover);
  padding: 0.125rem 0.25rem;
  font-size: var(--font-size-sm);
}

.markdown-content hr {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: var(--space-lg) 0;
}
```

**Step 2: Add example to styleguide.html**

Add to `shared/styleguide.html` in the components section:

```html
<section>
  <h2>Markdown Content</h2>
  <div class="markdown-content">
    <h1>Heading 1</h1>
    <h2>Heading 2</h2>
    <p>Paragraph with <strong>bold</strong> and <code>code</code>.</p>
    <table>
      <tr><th>Exercise</th><th>Sets</th><th>Reps</th></tr>
      <tr><td>Bench Press</td><td>4</td><td>6-10</td></tr>
    </table>
    <ul>
      <li>List item one</li>
      <li>List item two</li>
    </ul>
  </div>
</section>
```

**Step 3: Update COMPONENT-LIBRARY.md**

Add to `docs/COMPONENT-LIBRARY.md` after the Modal section:

```markdown
### markdown_content()

Container for rendered markdown content with proper typography.

```html
<div class="markdown-content">
  {{ rendered_html }}
</div>
```

Styles headings, paragraphs, tables, lists, code, and horizontal rules.
```

**Step 4: Verify in browser**

Open: `shared/styleguide.html` in browser
Expected: Markdown content section displays with black borders, proper table styling

**Step 5: Commit**

```bash
git add shared/css/components.css shared/styleguide.html docs/COMPONENT-LIBRARY.md
git commit -m "feat(shared): add .markdown-content component"
```

---

## Task 2: Add `.chart` Component to Shared Library

**Files:**
- Modify: `shared/css/components.css`
- Modify: `shared/js/components.js`
- Modify: `shared/styleguide.html`
- Modify: `docs/COMPONENT-LIBRARY.md`

**Step 1: Add CSS to components.css**

Add at end of `shared/css/components.css`:

```css
/* ==========================================================================
   CHART
   Simple SVG line chart with brutalist styling
   ========================================================================== */

.chart {
  width: 100%;
  height: 200px;
  border: 2px solid var(--color-border);
  background: var(--color-bg);
}

.chart__svg {
  width: 100%;
  height: 100%;
}

.chart__line {
  fill: none;
  stroke: var(--color-text);
  stroke-width: 2;
}

.chart__point {
  fill: var(--color-text);
}

.chart__axis {
  stroke: var(--color-border-light);
  stroke-width: 1;
}

.chart__label {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  fill: var(--color-muted);
}

.chart__grid {
  stroke: var(--color-border-light);
  stroke-width: 1;
  stroke-dasharray: 2, 4;
}
```

**Step 2: Add JS helper to components.js**

Add at end of `shared/js/components.js`:

```javascript
/* ==========================================================================
   CHART
   Simple SVG line chart renderer
   ========================================================================== */

function renderLineChart(containerId, data, options = {}) {
  const container = document.getElementById(containerId);
  if (!container || !data || data.length === 0) return;

  const padding = { top: 20, right: 20, bottom: 30, left: 40 };
  const width = container.clientWidth;
  const height = container.clientHeight || 200;
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Calculate scales
  const xValues = data.map((d, i) => i);
  const yValues = data.map(d => d.y);
  const yMin = Math.min(...yValues) * 0.95;
  const yMax = Math.max(...yValues) * 1.05;

  const xScale = (i) => padding.left + (i / (data.length - 1)) * chartWidth;
  const yScale = (v) => padding.top + chartHeight - ((v - yMin) / (yMax - yMin)) * chartHeight;

  // Build SVG
  let svg = `<svg class="chart__svg" viewBox="0 0 ${width} ${height}">`;

  // Y-axis grid lines
  const yTicks = 4;
  for (let i = 0; i <= yTicks; i++) {
    const y = padding.top + (i / yTicks) * chartHeight;
    const val = yMax - (i / yTicks) * (yMax - yMin);
    svg += `<line class="chart__grid" x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}"/>`;
    svg += `<text class="chart__label" x="${padding.left - 5}" y="${y + 4}" text-anchor="end">${val.toFixed(1)}</text>`;
  }

  // Line path
  const pathData = data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(d.y)}`).join(' ');
  svg += `<path class="chart__line" d="${pathData}"/>`;

  // Points
  data.forEach((d, i) => {
    svg += `<circle class="chart__point" cx="${xScale(i)}" cy="${yScale(d.y)}" r="4"/>`;
  });

  // X-axis labels
  data.forEach((d, i) => {
    if (d.label) {
      svg += `<text class="chart__label" x="${xScale(i)}" y="${height - 5}" text-anchor="middle">${d.label}</text>`;
    }
  });

  svg += '</svg>';
  container.innerHTML = svg;
}
```

**Step 3: Add example to styleguide.html**

Add to `shared/styleguide.html`:

```html
<section>
  <h2>Chart</h2>
  <div class="chart" id="demo-chart"></div>
  <script>
    renderLineChart('demo-chart', [
      { y: 50, label: 'W1' },
      { y: 52.5, label: 'W2' },
      { y: 52.5, label: 'W3' },
      { y: 55, label: 'W4' },
      { y: 55, label: 'W5' },
      { y: 57.5, label: 'W6' }
    ]);
  </script>
</section>
```

**Step 4: Update COMPONENT-LIBRARY.md**

Add to `docs/COMPONENT-LIBRARY.md`:

```markdown
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
```

**Step 5: Verify in browser**

Open: `shared/styleguide.html` in browser
Expected: Chart section shows line graph with points, grid lines, labels

**Step 6: Commit**

```bash
git add shared/css/components.css shared/js/components.js shared/styleguide.html docs/COMPONENT-LIBRARY.md
git commit -m "feat(shared): add .chart component with renderLineChart()"
```

---

## Task 3: Add `GET /api/exercises` Endpoint

**Files:**
- Create: `train/src/routers/exercises.py`
- Modify: `train/src/routers/__init__.py`
- Modify: `train/src/main.py`
- Test: `tests/e2e/api/test_train.py`

**Step 1: Write the failing test**

Add to `tests/e2e/api/test_train.py`:

```python
@pytest.mark.asyncio
async def test_list_exercises(train_url):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{train_url}/api/exercises")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_exercises_include_last_set(train_url):
    async with httpx.AsyncClient() as client:
        # First log a set
        session_resp = await client.post(
            f"{train_url}/api/sessions/start",
            json={"template_key": "Test"},
        )
        session_id = session_resp.json()["id"]
        
        await client.post(
            f"{train_url}/api/sets",
            json={"session_id": session_id, "exercise_name": "Test Exercise", "weight": 50, "reps": 10, "rir": 2},
        )
        
        # Check exercises endpoint
        resp = await client.get(f"{train_url}/api/exercises")
        assert resp.status_code == 200
        data = resp.json()
        
        exercise = next((e for e in data if e["name"] == "Test Exercise"), None)
        assert exercise is not None
        assert exercise["last_set"]["weight"] == 50
        assert exercise["last_set"]["reps"] == 10
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/e2e/api/test_train.py::test_list_exercises -v`
Expected: FAIL with 404

**Step 3: Create exercises router**

Create `train/src/routers/exercises.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models import Exercise, SetEntry, Session

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@router.get("")
async def list_exercises(db: AsyncSession = Depends(get_db)):
    # Get all exercises with their most recent set
    exercises_result = await db.execute(
        select(Exercise).order_by(Exercise.name)
    )
    exercises = exercises_result.scalars().all()
    
    result = []
    for exercise in exercises:
        # Get last set for this exercise
        last_set_result = await db.execute(
            select(SetEntry, Session)
            .join(Session, Session.id == SetEntry.session_id)
            .where(SetEntry.exercise_id == exercise.id)
            .order_by(desc(SetEntry.id))
            .limit(1)
        )
        last_set_row = last_set_result.first()
        
        # Get total sets count
        count_result = await db.execute(
            select(func.count(SetEntry.id)).where(SetEntry.exercise_id == exercise.id)
        )
        total_sets = count_result.scalar() or 0
        
        exercise_data = {
            "id": exercise.id,
            "name": exercise.name,
            "muscle_groups": exercise.muscle_groups,
            "total_sets": total_sets,
            "last_set": None,
        }
        
        if last_set_row:
            set_entry, session = last_set_row
            exercise_data["last_set"] = {
                "weight": set_entry.weight,
                "reps": set_entry.reps,
                "rir": set_entry.rir,
                "date": str(session.started_at.date()) if session.started_at else None,
            }
        
        result.append(exercise_data)
    
    return result
```

**Step 4: Register router**

Edit `train/src/routers/__init__.py`:

```python
from . import plans, sessions, sets, ui, context, exercises

__all__ = ["ui", "plans", "sessions", "sets", "context", "exercises"]
```

Edit `train/src/main.py`, add import and include:

```python
from src.routers import ui, plans, sessions, sets, context, exercises
```

```python
app.include_router(exercises.router)
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/e2e/api/test_train.py::test_list_exercises tests/e2e/api/test_train.py::test_exercises_include_last_set -v`
Expected: PASS

**Step 6: Commit**

```bash
git add train/src/routers/exercises.py train/src/routers/__init__.py train/src/main.py tests/e2e/api/test_train.py
git commit -m "feat(train): add GET /api/exercises endpoint with last_set"
```

---

## Task 4: Update Base Template for 3 Tabs

**Files:**
- Modify: `train/src/templates/base.html`

**Step 1: Update tabs to Today/History/Plan**

Edit `train/src/templates/base.html`, change line 18:

```html
{% set tabs = [("Today", base_path ~ "/"), ("History", base_path ~ "/history"), ("Plan", base_path ~ "/plan")] %}
```

**Step 2: Hide header on mobile**

Add class to header (line 20):

```html
<header class="header hidden-mobile">
```

**Step 3: Verify locally**

Run: `cd train && uvicorn src.main:app --reload --port 8001`
Open: `http://localhost:8001`
Expected: Bottom nav shows Today/History/Plan, header hidden on mobile viewport

**Step 4: Commit**

```bash
git add train/src/templates/base.html
git commit -m "refactor(train): update nav to Today/History/Plan, hide header on mobile"
```

---

## Task 5: Add History Route to UI Router

**Files:**
- Modify: `train/src/routers/ui.py`
- Create: `train/src/templates/history.html`

**Step 1: Add route handler**

Add to `train/src/routers/ui.py` after the `log` route:

```python
@router.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    return _render(request, "history.html", {"active_tab": "History"})
```

**Step 2: Create history template**

Create `train/src/templates/history.html`:

```html
{% extends "base.html" %}
{% import "components.html" as ui %}

{% block content %}
<div class="p-md">
  <div class="mb-md">
    <select id="exercise-select" class="input" onchange="loadExerciseHistory()">
      <option value="">Select exercise...</option>
    </select>
  </div>

  <div id="chart-container" class="chart mb-md" style="display: none;"></div>

  <div id="stats-container" style="display: none;">
    {% call ui.card() %}
      <div class="flex justify-between mb-sm">
        <span class="text-muted">Best</span>
        <span id="stat-best">-</span>
      </div>
      <div class="flex justify-between mb-sm">
        <span class="text-muted">Trend</span>
        <span id="stat-trend">-</span>
      </div>
      <div class="flex justify-between">
        <span class="text-muted">Total sets</span>
        <span id="stat-total">-</span>
      </div>
    {% endcall %}
  </div>

  <div id="recent-sets" class="mt-md" style="display: none;">
    <div class="text-sm text-muted mb-sm">RECENT SETS</div>
    <div id="recent-sets-list"></div>
  </div>

  <div id="empty-state" class="empty-state">
    <div class="empty-state__title">No exercise selected</div>
    <div class="empty-state__message">Choose an exercise to see progression</div>
  </div>
</div>
{% endblock %}

{% block scripts %}
<script>
const basePath = '{{ base_path }}';

async function loadExercises() {
  const resp = await fetch(`${basePath}/api/exercises`);
  const exercises = await resp.json();
  const select = document.getElementById('exercise-select');
  exercises.forEach(ex => {
    const opt = document.createElement('option');
    opt.value = ex.name;
    opt.textContent = ex.name;
    select.appendChild(opt);
  });
}

async function loadExerciseHistory() {
  const name = document.getElementById('exercise-select').value;
  if (!name) {
    document.getElementById('empty-state').style.display = 'block';
    document.getElementById('chart-container').style.display = 'none';
    document.getElementById('stats-container').style.display = 'none';
    document.getElementById('recent-sets').style.display = 'none';
    return;
  }

  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('chart-container').style.display = 'block';
  document.getElementById('stats-container').style.display = 'block';
  document.getElementById('recent-sets').style.display = 'block';

  const resp = await fetch(`${basePath}/api/sets?exercise_name=${encodeURIComponent(name)}`);
  const sets = await resp.json();

  if (sets.length === 0) {
    document.getElementById('chart-container').innerHTML = '<div class="p-md text-muted">No data yet</div>';
    return;
  }

  // Group by week and get max weight per week
  const weeklyMax = {};
  sets.forEach(s => {
    const week = s.session_id; // Simplified: use session as proxy for time
    if (!weeklyMax[week] || s.weight > weeklyMax[week]) {
      weeklyMax[week] = s.weight;
    }
  });

  const chartData = Object.entries(weeklyMax).slice(-8).map(([week, weight], i) => ({
    y: weight,
    label: `S${i + 1}`
  }));

  renderLineChart('chart-container', chartData);

  // Stats
  const weights = sets.map(s => s.weight);
  const maxWeight = Math.max(...weights);
  const maxSet = sets.find(s => s.weight === maxWeight);
  document.getElementById('stat-best').textContent = `${maxWeight}kg × ${maxSet.reps}`;
  document.getElementById('stat-total').textContent = sets.length;

  // Trend (first vs last)
  if (chartData.length >= 2) {
    const diff = chartData[chartData.length - 1].y - chartData[0].y;
    document.getElementById('stat-trend').textContent = diff >= 0 ? `+${diff}kg` : `${diff}kg`;
  } else {
    document.getElementById('stat-trend').textContent = '-';
  }

  // Recent sets list
  const recentHtml = sets.slice(0, 10).map(s =>
    `<div class="flex justify-between py-xs border-b">${s.weight}kg × ${s.reps}${s.rir !== null ? ` @${s.rir}` : ''}</div>`
  ).join('');
  document.getElementById('recent-sets-list').innerHTML = recentHtml;
}

loadExercises();
</script>
{% endblock %}
```

**Step 3: Verify locally**

Run: `cd train && uvicorn src.main:app --reload --port 8001`
Open: `http://localhost:8001/history`
Expected: Dropdown with exercises, chart renders on selection

**Step 4: Commit**

```bash
git add train/src/routers/ui.py train/src/templates/history.html
git commit -m "feat(train): add History tab with exercise progression chart"
```

---

## Task 6: Extend Sets API with exercise_name Filter

**Files:**
- Modify: `train/src/routers/sets.py`
- Test: `tests/e2e/api/test_train.py`

**Step 1: Write the failing test**

Add to `tests/e2e/api/test_train.py`:

```python
@pytest.mark.asyncio
async def test_list_sets_with_exercise_filter(train_url):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{train_url}/api/sets",
            params={"exercise_name": "Bench Press"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/e2e/api/test_train.py::test_list_sets_with_exercise_filter -v`
Expected: FAIL (no filter applied or 422)

**Step 3: Add exercise_name filter**

Edit `train/src/routers/sets.py`, update `list_sets` function signature:

```python
@router.get("")
async def list_sets(
    session_id: Optional[int] = None,
    since: Optional[date] = None,
    exercise_name: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
):
```

Add filter after existing filters:

```python
    if exercise_name:
        query = query.where(Exercise.name == exercise_name)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/e2e/api/test_train.py::test_list_sets_with_exercise_filter -v`
Expected: PASS

**Step 5: Commit**

```bash
git add train/src/routers/sets.py tests/e2e/api/test_train.py
git commit -m "feat(train): add exercise_name filter to GET /api/sets"
```

---

## Task 7: Rebuild Today Tab - Idle State

**Files:**
- Modify: `train/src/routers/ui.py`
- Modify: `train/src/templates/today.html`

**Step 1: Update today route to fetch data**

Edit `train/src/routers/ui.py`:

```python
from src.database import get_db
from src.models import Session
from sqlalchemy import select, desc

@router.get("/", response_class=HTMLResponse)
@router.get("/today", response_class=HTMLResponse)
async def today(request: Request):
    # Check for active session
    from src.database import async_session_maker
    async with async_session_maker() as db:
        result = await db.execute(
            select(Session).where(Session.ended_at.is_(None)).order_by(desc(Session.started_at)).limit(1)
        )
        active_session = result.scalars().first()
    
    return _render(request, "today.html", {
        "active_tab": "Today",
        "active_session": active_session,
    })
```

**Step 2: Rebuild today.html for idle state**

Replace `train/src/templates/today.html`:

```html
{% extends "base.html" %}
{% import "components.html" as ui %}

{% block content %}
<div id="today-content">
  {% if active_session %}
    {% include "partials/active_workout.html" %}
  {% else %}
    {% include "partials/idle_workout.html" %}
  {% endif %}
</div>
{% endblock %}

{% block scripts %}
<script src="{{ base_path }}/static/js/today.js"></script>
{% endblock %}
```

**Step 3: Create idle workout partial**

Create `train/src/templates/partials/idle_workout.html`:

```html
<div class="p-md">
  <div class="mb-lg">
    <div class="text-xl font-bold" id="template-name">Loading...</div>
    <div class="text-muted text-sm" id="template-meta"></div>
  </div>

  <div id="exercises-list" class="mb-lg">
    <!-- Populated by JS -->
  </div>

  <div class="action-panel">
    <button class="btn btn--primary btn--full btn--lg" onclick="startWorkout()">
      Start Workout
    </button>
  </div>
</div>

<script>
async function loadTodayData() {
  const resp = await fetch(`${basePath}/api/context`);
  const data = await resp.json();

  if (!data.plan) {
    document.getElementById('template-name').textContent = 'No Plan';
    document.getElementById('template-meta').textContent = 'Register a plan to get started';
    return;
  }

  // Parse plan to get template (simplified: just show plan title)
  document.getElementById('template-name').textContent = data.plan.title;
  document.getElementById('template-meta').textContent = `Week ${data.summary.weeks_on_plan}`;

  // Load exercises with last sets
  const exResp = await fetch(`${basePath}/api/exercises`);
  const exercises = await exResp.json();

  const html = exercises.map(ex => `
    <div class="card mb-sm">
      <div class="p-sm">
        <div class="font-bold">${ex.name}</div>
        <div class="text-muted text-sm">
          ${ex.last_set 
            ? `Last: ${ex.last_set.weight}kg × ${ex.last_set.reps}${ex.last_set.rir !== null ? ` @ RIR ${ex.last_set.rir}` : ''}`
            : 'No sets logged'}
        </div>
      </div>
    </div>
  `).join('');

  document.getElementById('exercises-list').innerHTML = html || '<div class="text-muted">No exercises yet</div>';
}

loadTodayData();
</script>
```

**Step 4: Create partials directory**

Run: `mkdir -p train/src/templates/partials`

**Step 5: Verify locally**

Run: `cd train && uvicorn src.main:app --reload --port 8001`
Open: `http://localhost:8001/`
Expected: Shows plan title, exercise list with last sets, Start Workout button

**Step 6: Commit**

```bash
git add train/src/routers/ui.py train/src/templates/today.html train/src/templates/partials/
git commit -m "feat(train): rebuild Today tab idle state with exercises list"
```

---

## Task 8: Add Active Workout Partial

**Files:**
- Create: `train/src/templates/partials/active_workout.html`
- Create: `train/src/static/js/today.js`

**Step 1: Create active workout partial**

Create `train/src/templates/partials/active_workout.html`:

```html
<div class="p-md">
  <div class="flex justify-between items-center mb-md border-b pb-sm">
    <div>
      <span class="font-bold">{{ active_session.template_key }}</span>
      <span class="text-muted text-sm" id="sets-count">· 0 sets</span>
    </div>
  </div>

  <div id="exercises-list" class="mb-lg">
    <!-- Populated by JS -->
  </div>

  <div class="action-panel">
    <button class="btn btn--danger btn--full" onclick="endWorkout()">
      End Workout
    </button>
  </div>
</div>

<script>
const sessionId = {{ active_session.id }};

async function loadActiveWorkout() {
  // Load exercises
  const exResp = await fetch(`${basePath}/api/exercises`);
  const exercises = await exResp.json();

  // Load sets for this session
  const setsResp = await fetch(`${basePath}/api/sets?session_id=${sessionId}`);
  const sessionSets = await setsResp.json();

  // Group sets by exercise
  const setsByExercise = {};
  sessionSets.forEach(s => {
    if (!setsByExercise[s.exercise_name]) setsByExercise[s.exercise_name] = [];
    setsByExercise[s.exercise_name].push(s);
  });

  document.getElementById('sets-count').textContent = `· ${sessionSets.length} sets`;

  const html = exercises.map(ex => {
    const exSets = setsByExercise[ex.name] || [];
    const isExpanded = false;
    const lastSet = ex.last_set || { weight: '', reps: '', rir: 2 };

    return `
    <div class="card mb-sm" id="exercise-${ex.id}">
      <div class="p-sm cursor-pointer" onclick="toggleExercise(${ex.id})">
        <div class="flex justify-between items-center">
          <div>
            <span class="font-bold">${ex.name}</span>
            <span class="text-muted text-sm">(${exSets.length} sets)</span>
          </div>
          <span class="text-muted">${exSets.length > 0 ? '✓' : '○'}</span>
        </div>
      </div>
      <div id="exercise-detail-${ex.id}" class="border-t p-sm" style="display: none;">
        <div class="text-sm text-muted mb-sm">
          Last: ${ex.last_set ? `${ex.last_set.weight}kg × ${ex.last_set.reps}` : 'None'}
        </div>
        <div class="flex gap-sm mb-sm">
          <input type="number" id="weight-${ex.id}" class="input" style="width: 80px" 
                 value="${lastSet.weight}" step="0.5" placeholder="kg">
          <input type="number" id="reps-${ex.id}" class="input" style="width: 60px" 
                 value="${lastSet.reps}" placeholder="reps">
          <input type="number" id="rir-${ex.id}" class="input" style="width: 50px" 
                 value="${lastSet.rir !== null ? lastSet.rir : ''}" min="0" max="5" placeholder="RIR">
        </div>
        <button class="btn btn--primary btn--full mb-sm" onclick="logSet(${ex.id}, '${ex.name}')">
          Log Set
        </button>
        <div class="text-sm mb-sm" id="session-sets-${ex.id}">
          ${exSets.map(s => `${s.weight}×${s.reps}`).join(', ') || 'No sets this session'}
        </div>
        <textarea id="notes-${ex.id}" class="textarea" rows="2" 
                  placeholder="Notes for ${ex.name}..."></textarea>
      </div>
    </div>
    `;
  }).join('');

  document.getElementById('exercises-list').innerHTML = html || '<div class="text-muted">No exercises</div>';
}

function toggleExercise(id) {
  const detail = document.getElementById(`exercise-detail-${id}`);
  detail.style.display = detail.style.display === 'none' ? 'block' : 'none';
}

async function logSet(exerciseId, exerciseName) {
  const weight = parseFloat(document.getElementById(`weight-${exerciseId}`).value);
  const reps = parseInt(document.getElementById(`reps-${exerciseId}`).value);
  const rirVal = document.getElementById(`rir-${exerciseId}`).value;
  const rir = rirVal !== '' ? parseInt(rirVal) : null;

  if (!weight || !reps) {
    alert('Enter weight and reps');
    return;
  }

  await fetch(`${basePath}/api/sets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      exercise_name: exerciseName,
      weight: weight,
      reps: reps,
      rir: rir
    })
  });

  loadActiveWorkout();
}

async function endWorkout() {
  if (!confirm('End this workout?')) return;

  await fetch(`${basePath}/api/sessions/end`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId })
  });

  window.location.reload();
}

loadActiveWorkout();
</script>
```

**Step 2: Create today.js**

Create `train/src/static/js/today.js`:

```javascript
async function startWorkout() {
  // Get current plan
  const ctxResp = await fetch(`${basePath}/api/context`);
  const ctx = await ctxResp.json();

  const templateKey = prompt('Workout template (e.g., Push, Pull, Legs):', 'Push');
  if (!templateKey) return;

  const planId = ctx.plan ? ctx.plan.id : null;

  await fetch(`${basePath}/api/sessions/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      template_key: templateKey,
      plan_id: planId
    })
  });

  window.location.reload();
}
```

**Step 3: Create static/js directory**

Run: `mkdir -p train/src/static/js`

**Step 4: Verify locally**

Run: `cd train && uvicorn src.main:app --reload --port 8001`
Test: Click Start Workout → Enter template → See active workout view → Log sets → End

**Step 5: Commit**

```bash
git add train/src/templates/partials/active_workout.html train/src/static/js/today.js
git commit -m "feat(train): add active workout view with set logging"
```

---

## Task 9: Rebuild Plan Tab with Markdown Rendering

**Files:**
- Modify: `train/src/templates/plan.html`

**Step 1: Update plan.html to use markdown-content**

Replace `train/src/templates/plan.html`:

```html
{% extends "base.html" %}
{% import "components.html" as ui %}

{% block content %}
<div class="p-md">
  <div id="plan-container" class="markdown-content">
    Loading plan...
  </div>
</div>
{% endblock %}

{% block scripts %}
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
async function loadPlan() {
  try {
    const resp = await fetch(`${basePath}/api/context`);
    const data = await resp.json();

    if (!data.plan || !data.plan.markdown) {
      document.getElementById('plan-container').innerHTML = 
        '<p class="text-muted">No plan registered yet.</p>';
      return;
    }

    const html = marked.parse(data.plan.markdown);
    document.getElementById('plan-container').innerHTML = html;
  } catch (e) {
    document.getElementById('plan-container').innerHTML = 
      '<p class="text-danger">Error loading plan</p>';
  }
}

loadPlan();
</script>
{% endblock %}
```

**Step 2: Verify locally**

Run: `cd train && uvicorn src.main:app --reload --port 8001`
Open: `http://localhost:8001/plan`
Expected: Plan markdown rendered with proper typography, tables styled

**Step 3: Commit**

```bash
git add train/src/templates/plan.html
git commit -m "feat(train): render plan markdown with .markdown-content component"
```

---

## Task 10: Remove Old Log Tab and Clean Up

**Files:**
- Delete: `train/src/templates/log.html`
- Modify: `train/src/routers/ui.py`
- Delete: `train/src/static/js/log.js` (if exists)

**Step 1: Remove log route**

Edit `train/src/routers/ui.py`, remove the `log` function entirely.

**Step 2: Delete log.html**

Run: `rm train/src/templates/log.html`

**Step 3: Delete log.js if exists**

Run: `rm -f train/src/static/js/log.js`

**Step 4: Verify no broken links**

Open app, click all tabs, verify no 404s.

**Step 5: Commit**

```bash
git add -A
git commit -m "chore(train): remove deprecated Log tab"
```

---

## Task 11: Add E2E UI Tests

**Files:**
- Create: `tests/e2e/ui/test_train.py`

**Step 1: Create UI test file**

Create `tests/e2e/ui/test_train.py`:

```python
import pytest
from playwright.sync_api import Page, expect


def test_today_page_loads(page: Page, train_url: str):
    """Verify Today page shows Start Workout button."""
    page.goto(f"{train_url}/")
    expect(page.locator("text=Start Workout")).to_be_visible()


def test_history_page_loads(page: Page, train_url: str):
    """Verify History page shows exercise dropdown."""
    page.goto(f"{train_url}/history")
    expect(page.locator("#exercise-select")).to_be_visible()


def test_plan_page_loads(page: Page, train_url: str):
    """Verify Plan page shows markdown content."""
    page.goto(f"{train_url}/plan")
    expect(page.locator(".markdown-content")).to_be_visible()


def test_bottom_nav_works(page: Page, train_url: str):
    """Verify bottom nav navigates between tabs."""
    page.goto(f"{train_url}/")
    
    # Click History
    page.click("text=History")
    expect(page.locator("#exercise-select")).to_be_visible()
    
    # Click Plan
    page.click("text=Plan")
    expect(page.locator(".markdown-content")).to_be_visible()
    
    # Click Today
    page.click("text=Today")
    expect(page.locator("text=Start Workout")).to_be_visible()
```

**Step 2: Add train_url fixture if missing**

Already added in `tests/conftest.py` from previous work.

**Step 3: Run tests locally**

Run: `pytest tests/e2e/ui/test_train.py -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add tests/e2e/ui/test_train.py
git commit -m "test(train): add E2E UI tests for Today/History/Plan tabs"
```

---

## Task 12: Final Verification and Push

**Step 1: Run all train tests**

Run: `pytest tests/e2e/api/test_train.py tests/e2e/ui/test_train.py -v`
Expected: All pass

**Step 2: Push to dev**

```bash
git push origin train-ui-redesign:dev
```

**Step 3: Monitor CI**

Run: `gh run list --limit 1`
Wait for success.

**Step 4: Test on dev**

Open: `https://train.gstoehl.dev/dev/`
Verify: All three tabs work, can start/log/end workout

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Add `.markdown-content` to shared |
| 2 | Add `.chart` to shared |
| 3 | Add `GET /api/exercises` endpoint |
| 4 | Update base template for 3 tabs |
| 5 | Add History route and template |
| 6 | Add exercise_name filter to sets API |
| 7 | Rebuild Today tab idle state |
| 8 | Add active workout partial |
| 9 | Rebuild Plan tab with markdown |
| 10 | Remove deprecated Log tab |
| 11 | Add E2E UI tests |
| 12 | Push and verify |
