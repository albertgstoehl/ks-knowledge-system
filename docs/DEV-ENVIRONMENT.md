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
