# Development Environment

Local Docker Compose setup for developing the knowledge system without K3s sudo requirements.

## Quick Start

```bash
cd /home/ags/knowledge-system
docker compose -f docker-compose.dev.yml up --build
```

## Service Ports

| Service          | URL                     |
|------------------|-------------------------|
| bookmark-manager | http://localhost:8001   |
| canvas           | http://localhost:8002   |
| kasten           | http://localhost:8003   |
| balance          | http://localhost:8005   |

## Hot Reload

Source code is mounted into containers. Python file changes apply automatically via uvicorn `--reload`.

**No rebuild needed for:**
- Python code changes
- Template changes
- Static file changes

**Rebuild required for:**
- requirements.txt changes
- Dockerfile changes

## Common Tasks

```bash
# Start all services
docker compose -f docker-compose.dev.yml up --build

# Start single service
docker compose -f docker-compose.dev.yml up bookmark-manager

# Rebuild one service
docker compose -f docker-compose.dev.yml build canvas
docker compose -f docker-compose.dev.yml up canvas

# View logs
docker compose -f docker-compose.dev.yml logs -f bookmark-manager

# Shell into container
docker compose -f docker-compose.dev.yml exec canvas /bin/sh

# Fresh database
rm ./canvas/data/canvas.db
docker compose -f docker-compose.dev.yml up canvas

# Stop all
docker compose -f docker-compose.dev.yml down
```

## vs Production (K3s)

| Aspect           | Dev (Docker Compose)      | Prod (K3s)                |
|------------------|---------------------------|---------------------------|
| Image updates    | `docker compose build`    | `sudo k3s ctr import`     |
| Network policies | None (all can talk)       | Zero-trust, explicit      |
| TLS              | None (HTTP)               | Let's Encrypt             |
| Ports            | 8001/8002/8003/8005       | 443 via ingress           |

## Claude Workflow

1. Make code changes in `./service-name/src/`
2. Changes auto-reload (watch container logs for confirmation)
3. Test at `localhost:800X`
4. When ready for production: user handles K3s deployment manually

## Database Files

Each service stores SQLite in its own `data/` directory:
- `./bookmark-manager/data/bookmarks.db`
- `./canvas/data/canvas.db`
- `./kasten/data/kasten.db`
- `./balance/data/balance.db`

These are bind-mounted and persist between container restarts.

## Shared Component Library

All services use shared CSS/JS/templates from `shared/`. When creating a new service:

### Dockerfile Setup

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY ../shared ./shared/   # Copy shared to /app/shared
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Static Files in main.py

**Critical:** Use `os.path.abspath()` for StaticFiles - relative paths don't work:

```python
from fastapi.staticfiles import StaticFiles
import os

# Note: Do NOT use root_path - Traefik strips /dev prefix before reaching the app
app = FastAPI(title="MyService", lifespan=lifespan)

# MUST use absolute paths for StaticFiles
_base = os.path.dirname(os.path.abspath(__file__))
static_path = os.path.join(_base, "static")

# Shared paths: Docker mount (/app/shared) or local (../../shared)
_docker_shared = os.path.abspath(os.path.join(_base, "..", "shared"))
_local_shared = os.path.abspath(os.path.join(_base, "..", "..", "shared"))
_shared_base = _docker_shared if os.path.exists(_docker_shared) else _local_shared

# Mount order matters: more specific first
if os.path.exists(_shared_base):
    app.mount("/static/shared", StaticFiles(directory=_shared_base), name="shared")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
```

**Why no `root_path`?** Traefik's `StripPrefix` middleware removes `/dev` from requests before they reach the app. The app always receives requests at `/`, not `/dev/`. Using `root_path` would break static file serving.

### Templates (base.html)

Use **absolute paths** - Traefik handles the /dev prefix at the ingress level:

```html
<!-- CORRECT: absolute paths -->
<link rel="stylesheet" href="/static/shared/css/variables.css" />
<link rel="stylesheet" href="/static/shared/css/base.css" />
<link rel="stylesheet" href="/static/shared/css/components.css" />
<link rel="stylesheet" href="/static/css/myservice.css" />

<!-- WRONG: using base_path variable -->
<link rel="stylesheet" href="{{ base_path }}/static/shared/css/variables.css" />
```

### Routing (No Redirects)

Avoid redirects between routes - they break with path prefixes. Instead, use multiple route decorators:

```python
# CORRECT: Both / and /today render the same page
@router.get("/", response_class=HTMLResponse)
@router.get("/today", response_class=HTMLResponse)
async def today(request: Request):
    return templates.TemplateResponse("today.html", {"request": request})

# WRONG: Redirect breaks with /dev prefix (redirects to /today not /dev/today)
@router.get("/")
async def root():
    return RedirectResponse(url="/today")
```

### Template Directory Setup

Include shared templates for component macros:

```python
from fastapi.templating import Jinja2Templates

templates_dir = Path(__file__).parent.parent / "templates"
shared_templates_dir = find_shared_dir(Path(__file__)) / "templates"
templates = Jinja2Templates(directory=[str(templates_dir), str(shared_templates_dir)])
```

Then import in templates:
```jinja2
{% import "components.html" as ui %}
{{ ui.header("My Service", tabs, active=active_tab) }}
```
