# Draft to Kasten Note Creation - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create Kasten notes directly from Canvas Draft editor using `### Title ... ---` delimiters.

**Architecture:** Canvas Draft detects delimiter pattern, shows modal for parent selection, calls Kasten API to create markdown file. Kasten generates YYMMDD+letter ID and writes file with optional parent frontmatter.

**Tech Stack:** FastAPI, Jinja2, vanilla JS, HTMX for search

---

### Task 1: Update Kasten Note ID Pattern

**Files:**
- Modify: `kasten/src/scanner.py:7`

**Step 1: Update regex pattern**

Change line 7 from:
```python
NOTE_ID_PATTERN = re.compile(r'^(\d{4}[a-z]+)\.md$')
```
to:
```python
NOTE_ID_PATTERN = re.compile(r'^(\d{4,6}[a-z]+)\.md$')
```

This allows both 4-digit (1219a) and 6-digit (251219a) IDs.

**Step 2: Verify existing notes still parse**

```bash
cd /home/ags/knowledge-system/kasten
python -c "from src.scanner import NOTE_ID_PATTERN; print(NOTE_ID_PATTERN.match('1219a.md'), NOTE_ID_PATTERN.match('251219a.md'))"
```

Expected: Both return match objects (not None).

**Step 3: Commit**

```bash
git add src/scanner.py
git commit -m "feat(scanner): support 6-digit YYMMDD note IDs"
```

---

### Task 2: Add CORS to Kasten

**Files:**
- Modify: `kasten/src/main.py`

**Step 1: Add CORS middleware**

Add after line 6 (after FastAPI init):

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Step 2: Commit**

```bash
git add src/main.py
git commit -m "feat: add CORS middleware for Canvas integration"
```

---

### Task 3: Add Create Note Endpoint to Kasten

**Files:**
- Modify: `kasten/src/routers/api.py`

**Step 1: Add imports at top**

```python
from datetime import datetime
from glob import glob
from pydantic import BaseModel
```

**Step 2: Add request schema after imports**

```python
class NoteCreateRequest(BaseModel):
    title: str
    content: str
    parent: str | None = None
```

**Step 3: Add ID generation helper after get_notes_path()**

```python
def generate_note_id(notes_path: str) -> str:
    """Generate next available YYMMDD+letter ID."""
    today = datetime.now().strftime("%y%m%d")
    existing = glob(os.path.join(notes_path, f"{today}*.md"))

    if not existing:
        return f"{today}a"

    # Find highest letter used today
    letters = []
    for path in existing:
        filename = os.path.basename(path)
        # Extract letter(s) after date
        match = re.match(rf'^{today}([a-z]+)\.md$', filename)
        if match:
            letters.append(match.group(1))

    if not letters:
        return f"{today}a"

    # Get next letter
    highest = max(letters)
    next_letter = chr(ord(highest[-1]) + 1)
    return f"{today}{next_letter}"
```

**Step 4: Add create endpoint at end of file**

```python
@router.post("/notes", status_code=201)
async def create_note(data: NoteCreateRequest, session: AsyncSession = Depends(get_db)):
    """Create a new note file."""
    notes_path = get_notes_path()
    note_id = generate_note_id(notes_path)
    filename = f"{note_id}.md"
    filepath = os.path.join(notes_path, filename)

    # Build file content
    lines = []
    if data.parent:
        lines.append("---")
        lines.append(f"parent: {data.parent}")
        lines.append("---")
    lines.append(data.title)
    lines.append("")
    lines.append(data.content)

    file_content = "\n".join(lines)

    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(file_content)

    # Add to database
    note = Note(id=note_id, title=data.title, file_path=filename)
    session.add(note)
    await session.commit()

    return {"id": note_id, "title": data.title}
```

**Step 5: Test endpoint**

```bash
curl -X POST http://localhost:8001/api/notes \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Note","content":"Test content","parent":null}'
```

Expected: `{"id":"251219X","title":"Test Note"}` where X is next letter.

**Step 6: Commit**

```bash
git add src/routers/api.py
git commit -m "feat(api): add POST /api/notes endpoint to create notes"
```

---

### Task 4: Add Modal HTML to Canvas Draft

**Files:**
- Modify: `canvas/src/templates/draft.html`

**Step 1: Add modal styles in extra_styles block (after line 28)**

```css
.modal {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 100;
}
.modal.active { display: flex; align-items: center; justify-content: center; }
.modal-content {
    background: #fff;
    border: 2px solid #000;
    padding: 1.5rem;
    min-width: 400px;
    max-width: 500px;
}
.modal-content h3 { margin-bottom: 1rem; }
.note-preview {
    background: #f5f5f5;
    padding: 0.75rem;
    margin-bottom: 1rem;
    font-size: 0.875rem;
    max-height: 120px;
    overflow: auto;
    white-space: pre-wrap;
}
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; margin-bottom: 0.25rem; }
.form-group input, .form-group select {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #000;
    font-family: inherit;
}
.modal-actions { display: flex; gap: 0.5rem; justify-content: flex-end; }
.hint { color: #666; font-size: 0.75rem; margin-left: 1rem; }
```

**Step 2: Update status bar (line 34-36)**

Replace:
```html
<div class="status-bar">
    <span class="save-status" id="save-status">Saved</span>
</div>
```

With:
```html
<div class="status-bar">
    <span class="save-status" id="save-status">Saved</span>
    <span class="hint">### Title ... --- to create note</span>
</div>
```

**Step 3: Add modal after draft-container div (after line 42)**

```html
<!-- Note Creation Modal -->
<div class="modal" id="note-modal">
    <div class="modal-content">
        <h3>Create Note</h3>
        <div class="note-preview" id="note-preview"></div>
        <div class="form-group">
            <label for="parent-search">Parent note (search by ID):</label>
            <input type="text" id="parent-search" placeholder="Type to search..." autocomplete="off">
            <select id="parent-select" size="5" style="margin-top:0.5rem;display:none;">
            </select>
        </div>
        <div class="modal-actions">
            <button class="btn" onclick="closeNoteModal()">Cancel</button>
            <button class="btn btn-primary" onclick="createNote()">Create Note</button>
        </div>
    </div>
</div>
```

**Step 4: Commit**

```bash
git add src/templates/draft.html
git commit -m "feat(draft): add note creation modal HTML"
```

---

### Task 5: Add Delimiter Detection JavaScript

**Files:**
- Modify: `canvas/src/templates/draft.html` (scripts block)

**Step 1: Add detection and modal logic after existing script (before closing `})();`)**

Insert before line 100:

```javascript
    // Note creation
    const kastenUrl = "{{ kasten_url }}";
    let pendingNote = null;

    function detectNoteBlock(text, cursorPos) {
        // Find --- ending at or before cursor
        const beforeCursor = text.substring(0, cursorPos);
        const lastDashes = beforeCursor.lastIndexOf('\n---');
        if (lastDashes === -1) return null;

        // Check if --- is on its own line
        const afterDashes = beforeCursor.substring(lastDashes + 4);
        if (afterDashes.trim() !== '' && afterDashes !== '\n') return null;

        // Find ### before the ---
        const blockText = beforeCursor.substring(0, lastDashes);
        const hashMatch = blockText.match(/\n### ([^\n]+)\n([\s\S]*)$/);
        if (!hashMatch) {
            // Try at start of text
            const startMatch = blockText.match(/^### ([^\n]+)\n([\s\S]*)$/);
            if (!startMatch) return null;

            // Check not inside quote
            if (startMatch[2].split('\n').some(l => l.startsWith('>'))) return null;

            return {
                title: startMatch[1].trim(),
                content: startMatch[2].trim(),
                start: 0,
                end: cursorPos
            };
        }

        // Check not inside quote
        if (hashMatch[2].split('\n').some(l => l.startsWith('>'))) return null;

        const startPos = blockText.lastIndexOf('\n### ');
        return {
            title: hashMatch[1].trim(),
            content: hashMatch[2].trim(),
            start: startPos === -1 ? 0 : startPos + 1,
            end: cursorPos
        };
    }

    function showNoteModal(note) {
        pendingNote = note;
        document.getElementById('note-preview').textContent =
            `### ${note.title}\n\n${note.content.substring(0, 200)}${note.content.length > 200 ? '...' : ''}`;
        document.getElementById('parent-search').value = '';
        document.getElementById('parent-select').innerHTML = '';
        document.getElementById('parent-select').style.display = 'none';
        document.getElementById('note-modal').classList.add('active');
        document.getElementById('parent-search').focus();
        loadNotes();
    }

    window.closeNoteModal = function() {
        document.getElementById('note-modal').classList.remove('active');
        pendingNote = null;
    };

    let allNotes = [];
    async function loadNotes() {
        try {
            const resp = await fetch(kastenUrl + '/api/notes');
            allNotes = await resp.json();
        } catch (e) {
            console.error('Failed to load notes:', e);
            allNotes = [];
        }
    }

    document.getElementById('parent-search').addEventListener('input', function(e) {
        const query = e.target.value.toLowerCase();
        const select = document.getElementById('parent-select');

        if (!query) {
            select.style.display = 'none';
            return;
        }

        const matches = allNotes.filter(n => n.id.toLowerCase().includes(query));
        select.innerHTML = '<option value="">No parent (new starting point)</option>' +
            matches.map(n => `<option value="${n.id}">${n.id}: ${n.title}</option>`).join('');
        select.style.display = matches.length > 0 ? 'block' : 'none';
    });

    window.createNote = async function() {
        if (!pendingNote) return;

        const parentSelect = document.getElementById('parent-select');
        const parent = parentSelect.value || null;

        try {
            const resp = await fetch(kastenUrl + '/api/notes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: pendingNote.title,
                    content: pendingNote.content,
                    parent: parent
                })
            });

            if (resp.ok) {
                const result = await resp.json();
                // Remove the block from editor
                const text = editor.value;
                editor.value = text.substring(0, pendingNote.start) + text.substring(pendingNote.end);
                lastSaved = ''; // Force save
                save();
                closeNoteModal();
                alert(`Note created: ${result.id}`);
            } else {
                alert('Failed to create note');
            }
        } catch (e) {
            alert('Error: ' + e.message);
        }
    };

    // Detect --- on Enter key
    editor.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            setTimeout(() => {
                const note = detectNoteBlock(editor.value, editor.selectionStart);
                if (note && note.title && note.content) {
                    showNoteModal(note);
                }
            }, 0);
        }
    });
```

**Step 2: Commit**

```bash
git add src/templates/draft.html
git commit -m "feat(draft): add delimiter detection and note creation logic"
```

---

### Task 6: Pass Kasten URL to Draft Template

**Files:**
- Modify: `canvas/src/routers/ui.py`

**Step 1: Add import and get URL**

Add at top:
```python
import os
```

**Step 2: Update draft_page function**

Change:
```python
return templates.TemplateResponse("draft.html", {
    "request": request,
    "active_tab": "draft",
    "content": canvas.content
})
```

To:
```python
return templates.TemplateResponse("draft.html", {
    "request": request,
    "active_tab": "draft",
    "content": canvas.content,
    "kasten_url": os.getenv("KASTEN_URL", "http://localhost:8001")
})
```

**Step 3: Commit**

```bash
git add src/routers/ui.py
git commit -m "feat(ui): pass kasten_url to draft template"
```

---

### Task 7: Update Docker Compose with Kasten URL

**Files:**
- Modify: `/home/ags/knowledge-system/docker-compose.yml`

**Step 1: Add KASTEN_URL to canvas service**

In the canvas service environment section, add:
```yaml
- KASTEN_URL=http://kasten:8000
```

**Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(docker): add KASTEN_URL env var for canvas"
```

---

### Task 8: Rebuild and Test

**Step 1: Rebuild containers**

```bash
cd /home/ags/knowledge-system
docker compose build --no-cache kasten canvas
docker compose up -d kasten canvas
```

**Step 2: Wait for services**

```bash
sleep 5
curl http://localhost:8001/health
curl http://localhost:8000/health
```

**Step 3: Test via browser**

1. Go to https://canvas.gstoehl.dev/draft
2. Type:
   ```
   ### Test Note Title
   This is the content of my test note.
   ---
   ```
3. Press Enter after ---
4. Modal should appear
5. Select parent or leave empty
6. Click Create Note
7. Verify file created in ~/notes/

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete draft-to-kasten note creation feature"
```

---

## File Summary

| File | Action |
|------|--------|
| `kasten/src/scanner.py` | Update ID pattern for 6-digit dates |
| `kasten/src/main.py` | Add CORS middleware |
| `kasten/src/routers/api.py` | Add POST /api/notes endpoint |
| `canvas/src/templates/draft.html` | Add modal + detection JS |
| `canvas/src/routers/ui.py` | Pass kasten_url to template |
| `docker-compose.yml` | Add KASTEN_URL env var |
