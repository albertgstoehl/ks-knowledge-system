# Template-Aware Workouts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Parse YAML frontmatter from training plans to enable template-aware workout logging.

**Architecture:** YAML frontmatter in plan markdown defines templates and exercises. API parses frontmatter, returns templates dict, strips frontmatter from displayed markdown. UI shows template picker modal, active workout filters to template exercises only.

**Tech Stack:** Python (PyYAML), FastAPI, Jinja2, vanilla JS

---

### Task 1: Add YAML frontmatter to training plan

**Files:**
- Modify: `train/plan/2026-01-14-plan.md`

**Step 1: Add frontmatter to plan**

Add YAML block at the very top of the file:

```yaml
---
templates:
  Push:
    - Barbell Bench Press
    - Incline Dumbbell Press
    - Cable Flyes
    - Lateral Raises
    - Tricep Pushdowns
  Pull:
    - Barbell Rows
    - Lat Pulldowns
    - Face Pulls
    - Dumbbell Rows
    - Bicep Curls
  Upper Mix + Legs:
    - Overhead Press
    - Chest-supported Rows
    - Pec Deck
    - Barbell Squats
    - Romanian Deadlifts
---
# Upper-Body Hypertrophy + Running Maintenance
```

The rest of the file stays unchanged.

**Step 2: Commit**

```bash
git add train/plan/2026-01-14-plan.md
git commit -m "feat(train): add YAML frontmatter with templates to plan"
```

---

### Task 2: Update workflow documentation

**Files:**
- Modify: `train/plan/workflow.md`

**Step 1: Add frontmatter documentation**

Replace entire file with:

```markdown
# Plan Iteration Workflow

## Plan Format

All plans must include YAML frontmatter defining workout templates:

\`\`\`yaml
---
templates:
  Push:
    - Barbell Bench Press
    - Incline Dumbbell Press
  Pull:
    - Barbell Rows
    - Lat Pulldowns
---
# Plan Title

...rest of markdown...
\`\`\`

- Template keys become workout options (e.g., "Push", "Pull")
- Exercise names must match exactly when logging sets
- Keep sets/reps/RIR info in markdown tables for human reading

## Iteration Steps

1. Review current plan markdown in this folder.
2. Summarize last 4 sessions (volume, PRs, skipped lifts).
3. Capture notes: pain, lagging muscles, motivation.
4. Propose changes and rationale.
5. Save as new markdown file with updated frontmatter.
```

**Step 2: Commit**

```bash
git add train/plan/workflow.md
git commit -m "docs(train): document YAML frontmatter requirement in workflow"
```

---

### Task 3: Update PlanResponse schema

**Files:**
- Modify: `train/src/schemas.py`

**Step 1: Add templates field**

```python
from pydantic import BaseModel
from typing import Optional


class PlanCreate(BaseModel):
    title: str
    markdown: str
    carry_over_notes: Optional[str] = None


class PlanResponse(BaseModel):
    id: int
    title: str
    markdown: str
    templates: dict[str, list[str]] | None = None
    created_at: str
    previous_plan_id: Optional[int]
    carry_over_notes: Optional[str]
```

**Step 2: Commit**

```bash
git add train/src/schemas.py
git commit -m "feat(train): add templates field to PlanResponse schema"
```

---

### Task 4: Parse frontmatter in plans router

**Files:**
- Modify: `train/src/routers/plans.py`

**Step 1: Add yaml import and parse function**

At top of file, add:

```python
import yaml
```

Add helper function after imports:

```python
def parse_frontmatter(content: str) -> tuple[dict | None, str]:
    """Parse YAML frontmatter from markdown content.
    
    Returns (frontmatter_dict, markdown_without_frontmatter).
    If no frontmatter, returns (None, original_content).
    """
    if not content.startswith('---'):
        return None, content
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return None, content
    
    try:
        frontmatter = yaml.safe_load(parts[1])
        markdown = parts[2].lstrip('\n')
        return frontmatter, markdown
    except yaml.YAMLError:
        return None, content
```

**Step 2: Update get_current_plan endpoint**

Replace the `get_current_plan` function:

```python
@router.get("/current", response_model=PlanResponse)
async def get_current_plan(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Plan).order_by(Plan.created_at.desc()))
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="No plan found")
    with open(plan.markdown_path, "r", encoding="utf-8") as file:
        content = file.read()
    
    frontmatter, markdown = parse_frontmatter(content)
    templates = frontmatter.get('templates') if frontmatter else None
    
    return PlanResponse(
        id=plan.id,
        title=plan.title,
        markdown=markdown,
        templates=templates,
        created_at=str(plan.created_at),
        previous_plan_id=plan.previous_plan_id,
        carry_over_notes=plan.carry_over_notes,
    )
```

**Step 3: Commit**

```bash
git add train/src/routers/plans.py
git commit -m "feat(train): parse YAML frontmatter and return templates"
```

---

### Task 5: Add template picker modal to idle workout

**Files:**
- Modify: `train/src/templates/partials/idle_workout.html`

**Step 1: Replace entire file**

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
    <button class="btn btn--primary btn--full btn--lg" onclick="openTemplatePicker()">
      Start Workout
    </button>
  </div>
</div>

<!-- Template Picker Modal -->
<div id="template-modal" class="modal" style="display: none;">
  <div class="modal__backdrop" onclick="closeTemplatePicker()"></div>
  <div class="modal__content">
    <div class="modal__header">
      <h3>Select Workout</h3>
    </div>
    <div class="modal__body" id="template-options">
      <!-- Populated by JS -->
    </div>
    <div class="modal__footer">
      <button class="btn btn--ghost" onclick="closeTemplatePicker()">Cancel</button>
    </div>
  </div>
</div>

<script>
let planTemplates = null;

async function loadTodayData() {
  try {
    const planResp = await fetch(`${basePath}/api/plan/current`);
    if (planResp.ok) {
      const plan = await planResp.json();
      document.getElementById('template-name').textContent = plan.title;
      document.getElementById('template-meta').textContent = 'Current plan';
      planTemplates = plan.templates;
    } else {
      document.getElementById('template-name').textContent = 'No Plan';
      document.getElementById('template-meta').textContent = 'Register a plan to get started';
    }
  } catch (e) {
    document.getElementById('template-name').textContent = 'Ready to Train';
    document.getElementById('template-meta').textContent = '';
  }

  const exResp = await fetch(`${basePath}/api/exercises`);
  const exercises = await exResp.json();

  if (exercises.length === 0) {
    document.getElementById('exercises-list').innerHTML = '<div class="text-muted">No exercises yet. Start a workout to log your first set!</div>';
    return;
  }

  const html = exercises.map(ex => `
    <div class="card mb-sm">
      <div class="p-sm">
        <div class="font-bold">${ex.name}</div>
        <div class="text-muted text-sm">
          ${ex.last_set 
            ? `Last: ${ex.last_set.weight}kg x ${ex.last_set.reps}${ex.last_set.rir !== null ? ` @ RIR ${ex.last_set.rir}` : ''}`
            : 'No sets logged'}
        </div>
      </div>
    </div>
  `).join('');

  document.getElementById('exercises-list').innerHTML = html;
}

function openTemplatePicker() {
  if (!planTemplates || Object.keys(planTemplates).length === 0) {
    // Fallback to prompt if no templates
    const templateKey = prompt('Workout template (e.g., Push, Pull, Legs):', 'Push');
    if (templateKey) startWorkoutWithTemplate(templateKey);
    return;
  }

  const optionsHtml = Object.keys(planTemplates).map(key => `
    <button class="btn btn--full mb-sm" onclick="startWorkoutWithTemplate('${key}')">${key}</button>
  `).join('');
  
  document.getElementById('template-options').innerHTML = optionsHtml;
  document.getElementById('template-modal').style.display = 'flex';
}

function closeTemplatePicker() {
  document.getElementById('template-modal').style.display = 'none';
}

async function startWorkoutWithTemplate(templateKey) {
  closeTemplatePicker();
  await fetch(`${basePath}/api/sessions/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ template_key: templateKey })
  });
  window.location.reload();
}

loadTodayData();
</script>
```

**Step 2: Commit**

```bash
git add train/src/templates/partials/idle_workout.html
git commit -m "feat(train): add template picker modal to idle workout"
```

---

### Task 6: Update today.js (remove old startWorkout)

**Files:**
- Modify: `train/src/static/js/today.js`

**Step 1: Replace entire file**

```javascript
// today.js - shared utilities for Today tab
// Template picker and workout start logic is now in idle_workout.html
```

**Step 2: Commit**

```bash
git add train/src/static/js/today.js
git commit -m "refactor(train): move workout start logic to idle_workout partial"
```

---

### Task 7: Filter active workout to template exercises

**Files:**
- Modify: `train/src/templates/partials/active_workout.html`

**Step 1: Replace entire file**

```html
<div class="p-md">
  <div class="flex justify-between items-center mb-md border-b pb-sm">
    <div>
      <span class="font-bold">{{ active_session.template_key }}</span>
      <span class="text-muted text-sm" id="sets-count">- 0 sets</span>
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
const templateKey = '{{ active_session.template_key }}';

async function loadActiveWorkout() {
  // Load plan to get template exercises
  let templateExercises = null;
  try {
    const planResp = await fetch(`${basePath}/api/plan/current`);
    if (planResp.ok) {
      const plan = await planResp.json();
      if (plan.templates && plan.templates[templateKey]) {
        templateExercises = plan.templates[templateKey];
      }
    }
  } catch (e) {
    console.error('Failed to load plan:', e);
  }

  // Load all exercises with last sets
  const exResp = await fetch(`${basePath}/api/exercises`);
  const allExercises = await exResp.json();
  
  // Create lookup by name
  const exercisesByName = {};
  allExercises.forEach(ex => {
    exercisesByName[ex.name] = ex;
  });

  // Load sets for this session
  const setsResp = await fetch(`${basePath}/api/sets?session_id=${sessionId}`);
  const sessionSets = await setsResp.json();

  // Group sets by exercise
  const setsByExercise = {};
  sessionSets.forEach(s => {
    if (!setsByExercise[s.exercise_name]) setsByExercise[s.exercise_name] = [];
    setsByExercise[s.exercise_name].push(s);
  });

  document.getElementById('sets-count').textContent = `- ${sessionSets.length} sets`;

  // Build exercise list - template exercises first, or all if no template
  let exerciseNames = templateExercises || allExercises.map(ex => ex.name);

  const html = exerciseNames.map((name, idx) => {
    const ex = exercisesByName[name] || { id: `new-${idx}`, name: name, last_set: null };
    const exSets = setsByExercise[name] || [];
    const lastSet = ex.last_set || { weight: '', reps: '', rir: '' };
    const exId = ex.id || `new-${idx}`;

    return `
    <div class="card mb-sm" id="exercise-${exId}">
      <div class="p-sm cursor-pointer" onclick="toggleExercise('${exId}')">
        <div class="flex justify-between items-center">
          <div>
            <span class="font-bold">${name}</span>
            <span class="text-muted text-sm">(${exSets.length} sets)</span>
          </div>
          <span class="text-muted">${ex.last_set ? ex.last_set.weight + 'kg' : '-'}</span>
        </div>
      </div>
      <div id="exercise-detail-${exId}" class="border-t p-sm" style="display: none;">
        <div class="text-sm text-muted mb-sm">
          Last: ${ex.last_set ? `${ex.last_set.weight}kg x ${ex.last_set.reps}` : 'None'}
        </div>
        <div class="flex gap-sm mb-sm">
          <input type="number" id="weight-${exId}" class="input" style="width: 80px" 
                 value="${lastSet.weight || ''}" step="0.5" placeholder="kg">
          <input type="number" id="reps-${exId}" class="input" style="width: 60px" 
                 value="${lastSet.reps || ''}" placeholder="reps">
          <input type="number" id="rir-${exId}" class="input" style="width: 50px" 
                 value="${lastSet.rir !== null && lastSet.rir !== undefined ? lastSet.rir : ''}" min="0" max="5" placeholder="RIR">
        </div>
        <button class="btn btn--primary btn--full mb-sm" onclick="logSet('${exId}', '${name.replace(/'/g, "\\'")}')">
          Log Set
        </button>
        <div class="text-sm mb-sm" id="session-sets-${exId}">
          ${exSets.map(s => `${s.weight}x${s.reps}`).join(', ') || 'No sets this session'}
        </div>
      </div>
    </div>
    `;
  }).join('');

  document.getElementById('exercises-list').innerHTML = html || '<div class="text-muted p-md">No exercises in template.</div>';
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

**Step 2: Commit**

```bash
git add train/src/templates/partials/active_workout.html
git commit -m "feat(train): filter active workout to template exercises"
```

---

### Task 8: Add API test for templates in plan response

**Files:**
- Modify: `tests/e2e/api/test_train.py`

**Step 1: Add test**

Add at end of file:

```python
@pytest.mark.asyncio
async def test_plan_current_includes_templates(train_url):
    """Test that plan response includes parsed templates."""
    async with httpx.AsyncClient() as client:
        # First register a plan with frontmatter
        plan_md = """---
templates:
  Push:
    - Bench Press
    - Tricep Dips
  Pull:
    - Rows
---
# Test Plan
"""
        await client.post(
            f"{train_url}/api/plan/register",
            json={"title": "Test Templates", "markdown": plan_md},
        )

        resp = await client.get(f"{train_url}/api/plan/current")
        assert resp.status_code == 200
        data = resp.json()
        
        assert "templates" in data
        assert data["templates"] is not None
        assert "Push" in data["templates"]
        assert "Bench Press" in data["templates"]["Push"]
        assert "# Test Plan" in data["markdown"]
        assert "---" not in data["markdown"]  # Frontmatter stripped
```

**Step 2: Commit**

```bash
git add tests/e2e/api/test_train.py
git commit -m "test(train): add test for templates in plan response"
```

---

### Task 9: Final verification and push

**Step 1: Run local test (if possible)**

```bash
cd train && python -c "from src.routers.plans import parse_frontmatter; print(parse_frontmatter('---\ntemplates:\n  A: [x]\n---\n# Hi'))"
```

Expected: `({'templates': {'A': ['x']}}, '# Hi')`

**Step 2: Push to dev**

```bash
git push origin train-templates:dev
```

**Step 3: Monitor CI**

```bash
gh run list --limit 1
gh run view <run-id>
```

Wait for all checks to pass.
