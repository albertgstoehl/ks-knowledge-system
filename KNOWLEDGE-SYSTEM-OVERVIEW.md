# Knowledge System Overview

A personal knowledge management ecosystem running on K3s, consisting of interconnected microservices that facilitate the flow from content discovery to persistent knowledge storage.

## Architecture Diagram

```
┌───────────────────┐
│   TELEGRAM BOT    │ ─────────────────────────────┐
│  (Quick Capture)  │                              │
└───────────────────┘                              │
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER BROWSER                                   │
│                          (HTTPS via Let's Encrypt)                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRAEFIK INGRESS (K3s)                               │
│ ┌───────────────┬───────────────┬───────────────┬───────────────┬─────────┐ │
│ │bookmark.gstoehl│canvas.gstoehl│kasten.gstoehl │train.gstoehl  │balance  │ │
│ │ [ForwardAuth] │ [ForwardAuth] │ [ForwardAuth] │ [ForwardAuth] │(no auth)│ │
│ └───────┬───────┴───────┬───────┴───────┬───────┴───────┬───────┴─────────┘ │
│         └───────────────┼───────────────┼───────────────┘                   │
│                         ▼               │                                   │
│              ┌─────────────────────┐    │                                   │
│              │  balance-check MW   │◀───┘ /api/auth-check (200 or 302)      │
│              └─────────────────────┘                                        │
└─────────────────────────────────────────────────────────────────────────────┘
     │              │              │              │              │
     ▼              ▼              ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ BOOKMARK │  │  CANVAS  │  │  KASTEN  │  │  TRAIN   │  │ BALANCE  │
│ MANAGER  │─▶│(Synthesis│◀▶│(Browsing)│  │(Workouts)│  │(Rhythms) │
│(Collect) │  │    )     │  │          │  │          │  │          │
│Port 8000 │  │Port 8000 │  │Port 8000 │  │Port 8000 │  │Port 8000 │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
     │              │              │              │              │
     ▼              ▼              ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ SQLite   │  │ SQLite   │  │ SQLite   │  │ SQLite   │  │ SQLite   │
│ (5Gi)    │  │ (1Gi)    │  │ + Notes  │  │ + Plans  │  │ (1Gi)    │
└──────────┘  └──────────┘  │ (1Gi)    │  │ (1Gi)    │  └──────────┘
                            └──────────┘  └──────────┘
```

## Knowledge Flow

```
READ                    THINK                   BROWSE
─────────────────────────────────────────────────────────────
    ┌─────────┐         ┌─────────┐         ┌─────────┐
    │Bookmark │ quotes  │ Canvas  │ notes   │ Kasten  │
    │Manager  │────────▶│ Draft + │────────▶│ Browse  │
    │         │         │Workspace│         │ Notes   │
    └─────────┘         └─────────┘         └─────────┘
         │                   │                   │
         │    RSS Feeds      │  Arrange Ideas    │  Follow Links
         │    AI Summaries   │  Extract Notes    │  Discover
         │    Web Archive    │  Visual Graph     │  No Search
         │    7-day Expiry   │  Source Linking   │  Entry Points
```

---

## Components

### 1. Bookmark Manager

**Purpose:** Capture and organize web content with AI-powered summarization and automatic expiry

**Domain:** `bookmark.gstoehl.dev`

**Tech Stack:**
- Python 3.11 / FastAPI 0.115
- SQLite with aiosqlite (async)
- Claude Code OAuth (LLM summaries)
- Jina AI (content extraction)

**Source Structure:** `bookmark-manager/src/`

**Key Features:**
- **Smart Expiry:** Bookmarks expire after 7 days unless pinned or marked as thesis
- **Academic Paper Detection:** 60+ domain patterns (arxiv, springer, nature, IEEE, etc.)
- **Content Pipeline:** Jina extraction → YouTube transcripts → LLM summary → Web Archive
- **RSS Feeds:** Subscribe to feeds, 24-hour item window, promote to bookmarks
- **Zotero Sync:** Optional academic paper management with DOI extraction
- **Telegram Bot:** Quick URL capture via `/paper`, `/pin` commands

**API Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `POST /bookmarks` | Create with auto-processing |
| `GET /bookmarks` | List with filters (inbox/thesis/pins) |
| `GET /bookmarks/{id}/content` | Full content for note creation |
| `POST /feeds` | Subscribe to RSS |
| `POST /canvas/quotes` | Push quote to Canvas |
| `POST /backup/create` | Database backup |

**Data Model:**
- `Bookmarks` - URL, metadata, content, state, expires_at, is_thesis, pinned
- `Feeds` - RSS subscriptions with error tracking
- `FeedItems` - Discovered entries (auto-cleanup after 7 days)

**Environment Variables:**
```
DATABASE_URL          # SQLite path
CANVAS_URL            # Canvas API (internal)
CLAUDE_CODE_OAUTH_TOKEN  # LLM summaries (optional)
JINA_API_KEY          # Content extraction (optional)
ZOTERO_API_KEY        # Paper sync (optional)
ZOTERO_USER_ID        # Zotero account
```

---

### 2. Telegram Bot

**Purpose:** Quick bookmark capture from mobile via Telegram

**Tech Stack:**
- Python 3.11
- python-telegram-bot 21.7
- httpx (async HTTP)

**Source:** `bookmark-manager/bot/main.py`

**Commands:**
| Command | Action |
|---------|--------|
| `<url>` | Save to inbox |
| `/paper <url>` | Save as thesis material (no expiry) |
| `/pin <url>` | Save and pin (no expiry) |

**Environment Variables:**
```
TELEGRAM_BOT_TOKEN       # Bot authentication
API_URL                  # Bookmark Manager endpoint
ALLOWED_TELEGRAM_USERS   # Comma-separated user IDs (optional)
```

---

### 3. Canvas

**Purpose:** Thinking workspace for drafting notes and connecting ideas visually

**Domain:** `canvas.gstoehl.dev`

**Tech Stack:**
- Python 3.11 / FastAPI 0.115
- SQLite with aiosqlite
- Vis.js (graph visualization)
- Vanilla JS + Jinja2 templates

**Source Structure:** `canvas/src/`

**Key Features:**
- **Draft Mode:** Free-form textarea with 300ms autosave, offline localStorage fallback
- **Quote Ingestion:** Receives highlights from Bookmark Manager, appends with source metadata
- **Note Extraction:** Parse `### Title\n\ncontent\n---` blocks into Kasten notes
- **Parent Selection:** Modal to search and select parent note from Kasten
- **Workspace Mode:** Vis.js graph with manual node positioning, labeled connections
- **Source Creation:** Auto-creates sources in Kasten from quote metadata

**API Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `GET /api/canvas` | Fetch draft content |
| `PUT /api/canvas` | Update draft |
| `POST /api/quotes` | Receive quote from Bookmark Manager |
| `GET /api/workspace` | Get notes with positions and connections |
| `POST /api/workspace/notes` | Add note to workspace |
| `POST /api/workspace/connections` | Create labeled edge |

**Data Model:**
- `CanvasState` - Single-row draft content
- `WorkspaceNote` - km_note_id + x/y position
- `WorkspaceConnection` - Labeled directed edges

**Environment Variables:**
```
DATABASE_URL    # SQLite path
KASTEN_URL      # Kasten API endpoint
```

---

### 4. Kasten

**Purpose:** Minimal Zettelkasten browser - navigate notes by following links, no search

**Domain:** `kasten.gstoehl.dev`

**Tech Stack:**
- Python 3.11 / FastAPI 0.115
- SQLite with aiosqlite
- httpx (HTTP client)
- Jinja2 templates

**Source Structure:** `kasten/src/`

**Key Features:**
- **No Search by Design:** Explore through link-following only
- **Entry Points:** Notes with outgoing links but no backlinks
- **Parent-Child Structure:** Hierarchical note organization
- **Source Linking:** Connect notes to archived bookmarks
- **Wiki Links:** `[[note_id]]` syntax converted to clickable links
- **Random Navigation:** "Feeling Lucky" for serendipitous discovery

**Note Format:**
```markdown
---
parent: 1218a
---
# Note Title

Content with [[1219b]] wiki-style links.
```

**Note IDs:** `YYMMDD[a-z]+` format (e.g., `1219a`, `1219b`)

**API Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `GET /api/notes` | List all notes |
| `GET /api/notes/entry-points` | Get root notes |
| `GET /api/notes/{id}` | Get note with content |
| `POST /api/notes` | Create new note |
| `POST /api/sources` | Archive bookmark as source |
| `GET /api/sources/{id}` | Get source with linked notes |
| `POST /api/reindex` | Rebuild index from files |

**Data Model:**
- `Notes` - id, title, parent_id, source_id, file_path
- `Sources` - Archived bookmarks (url, title, content, video_id)
- `Links` - Forward/backward link index

**Environment Variables:**
```
DATABASE_URL    # SQLite path
NOTES_PATH      # Markdown notes directory
CANVAS_URL      # Canvas endpoint
```

---

### 5. Balance

**Purpose:** Personal rhythm tracker with Pomodoro timing, break enforcement, and life-compass analytics

**Domain:** `balance.gstoehl.dev`

**Tech Stack:**
- Python 3.11 / FastAPI 0.115
- SQLite with aiosqlite
- Jinja2 templates + vanilla JS

**Source Structure:** `balance/src/`

**Key Features:**
- **Focus Sessions:** 25-min Pomodoro with expected/personal types and 3-word intentions
- **Priority Tracking:** Tag expected sessions with ranked priorities (Thesis, Work, etc.)
- **Drift Detection:** Stats alert when actual work doesn't match stated priorities
- **Break Enforcement:** Hard lockout during breaks, no skip button
- **Activity Logging:** Track meditation, exercise, and daily mood (heavy/okay/light)
- **Life Compass:** Six-dimension alignment view oriented around user's north star
- **Spiral Protection:** Auto-shifts to check-in mode after 3+ days absence
- **Session Effectiveness:** Transcript analysis detects scope creep and intention drift

**API Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `POST /api/sessions/start` | Start Pomodoro session (with priority_id) |
| `POST /api/sessions/end` | End session with feedback |
| `GET /api/check` | Break status (JSON response) |
| `GET /api/auth-check` | ForwardAuth endpoint (200 or 302 redirect) |
| `GET /api/priorities` | List ranked priorities |
| `POST /api/priorities` | Create priority |
| `PUT /api/priorities/reorder` | Reorder priorities |
| `GET /api/stats/drift` | Get drift detection data |
| `POST /api/meditation` | Log meditation |
| `POST /api/exercise` | Log exercise |
| `POST /api/pulse` | Log daily mood + connection |
| `GET /api/settings` | Get/update limits |

**Data Model:**
- `Sessions` - Pomodoro tracking with type, intention, priority_id, distractions
- `Priorities` - Ranked priorities for expected sessions (name, rank)
- `SessionAnalyses` - Transcript analysis results (alignment, scope, red flags)
- `Meditation` - Duration, time of day
- `Exercise` - Type, duration, intensity
- `DailyPulse` - Mood (heavy/okay/light), connection logged
- `Settings` - Daily cap, hard max, evening cutoff
- `AppState` - Break status, check-in mode, north star

**Environment Variables:**
```
DATABASE_URL    # SQLite path
```

---

### 6. Train

**Purpose:** Workout logging and training plan management with session tracking and set entry

**Domain:** `train.gstoehl.dev`

**Tech Stack:**
- Python 3.11 / FastAPI 0.115
- SQLite with aiosqlite
- Jinja2 templates + vanilla JS

**Source Structure:** `train/src/`

**Key Features:**
- **Session Logging:** Start/end workout sessions with template keys (A/B splits)
- **Set Entry:** Quick logging of exercise, weight, reps, RIR (reps in reserve)
- **Plan Management:** Markdown-based training plans with version history
- **Exercise Library:** Auto-created exercises with muscle group tracking

**API Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `POST /api/sessions/start` | Start workout session |
| `POST /api/sessions/end` | End session with notes |
| `POST /api/sets` | Log a set |
| `GET /api/sets/recent` | Recent sets (last 20) |
| `POST /api/plan/register` | Register new plan (markdown) |
| `GET /api/plan/current` | Get current plan |

**Data Model:**
- `Sessions` - Workout sessions with start/end time and notes
- `SetEntry` - Individual sets (weight, reps, RIR, order)
- `Exercise` - Exercise library with muscle groups
- `Plan` - Training plans with markdown path and version history

**Environment Variables:**
```
DATABASE_URL    # SQLite path
PLAN_DIR        # Markdown plans directory (default: ./plan)
```

---

## Kubernetes Infrastructure

### Namespace: `knowledge-system`

### Deployments

| Service | Replicas | Memory | CPU | Image Pull |
|---------|----------|--------|-----|------------|
| bookmark-manager | 1 | 1-4Gi | 100m-1000m | Never (local) |
| telegram-bot | 1 | 64-128Mi | 25-100m | Never (local) |
| canvas | 1 | 128-256Mi | 50-200m | Never (local) |
| kasten | 1 | 128-256Mi | 50-200m | Never (local) |
| balance | 1 | 128-256Mi | 50-200m | Never (local) |
| train | 1 | 128-256Mi | 50-200m | Never (local) |

### Persistent Storage

| PVC | Service | Size | Purpose |
|-----|---------|------|---------|
| bookmark-manager-pvc | bookmark-manager | 5Gi | SQLite database |
| canvas-pvc | canvas | 1Gi | SQLite database |
| kasten-pvc | kasten | 1Gi | SQLite index |
| balance-pvc | balance | 1Gi | SQLite database |
| train-pvc | train | 1Gi | SQLite + plans |

### Network Policies (Zero-Trust)

```
Default: Deny all egress (except DNS)

bookmark-manager:
  → Canvas (internal port 8000)
  → Internet (HTTPS/HTTP, excluding private IPs)

telegram-bot:
  → Bookmark Manager (internal port 8000)
  → Telegram API (HTTPS)

canvas:
  → All pods in namespace (port 8000)

kasten:
  → DNS only (most restricted)

balance:
  → DNS only (standalone service)

train:
  → DNS only (standalone service)
```

---

## Service Communication Matrix

| From → To | Bookmark Manager | Canvas | Kasten | Balance | Train | External |
|-----------|-----------------|--------|--------|---------|-------|----------|
| **Telegram Bot** | ✓ (bookmarks) | ✗ | ✗ | ✗ | ✗ | ✓ (Telegram API) |
| **Bookmark Manager** | - | ✓ (quotes) | ✗ | ✗ | ✗ | ✓ (Jina, Claude, Archive.org) |
| **Canvas** | ✗ | - | ✓ (notes, sources) | ✗ | ✗ | ✗ |
| **Kasten** | ✗ | ✗ | - | ✗ | ✗ | ✗ |
| **Balance** | ✗ | ✗ | ✗ | - | ✗ | ✗ |
| **Train** | ✗ | ✗ | ✗ | ✗ | - | ✗ |

---

## Security Model

1. **Zero-trust network policies** - Explicit egress rules per service
2. **Private IP blocking** - External traffic cannot reach internal networks
3. **Local images only** - `imagePullPolicy: Never` prevents supply chain attacks
4. **Read-only mounts** - Kasten's notes directory is read-only
5. **TLS everywhere** - Let's Encrypt certificates for all domains
6. **Auto-expiry** - Bookmarks expire after 7 days unless protected

---

## Design Philosophy

- **Brutalist UI** - Monospace fonts, black borders, minimal styling
- **Offline-first** - localStorage fallbacks where possible
- **Atomic notes** - Small, focused pieces linked together
- **No search in Kasten** - Structure emerges from exploration
- **Expiry-driven cleanup** - Only keep what matters
- **Reference-based** - Workspace stores references, not copies
