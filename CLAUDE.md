# Knowledge System - Agent Guide

Read this file first. Based on your task, read only the relevant documentation files listed below to save tokens.

## System Overview

**Start here for any task:**
- `KNOWLEDGE-SYSTEM-OVERVIEW.md` - Architecture, service communication, data flow, design philosophy

## Development & Operations

| Task | Read |
|------|------|
| Local development setup | `docs/DEV-ENVIRONMENT.md` |
| K8s deployment, logs, debugging | `k8s/OPERATIONS.md` |
| UI styling (brutalist, monospace) | `bookmark-manager/docs/style.md` |
| Terminal output styling | `docs/TERMINAL-STYLE-GUIDE.md` |

## Service-Specific Documentation

### Bookmark Manager (`bookmark-manager/`)

| Task | Read |
|------|------|
| API endpoints, data model | `bookmark-manager/docs/plans/2025-10-19-bookmark-manager-api.md` |
| UI design (conveyor belt inbox) | `bookmark-manager/docs/plans/2025-12-22-ui-redesign.md` |
| RSS feeds feature | `bookmark-manager/docs/plans/2025-12-18-rss-feeds-design.md` |
| YouTube video handling | `bookmark-manager/docs/plans/2025-12-18-youtube-videos-design.md` |
| Canvas integration (quotes) | `bookmark-manager/docs/plans/2025-12-19-canvas-integration.md` |
| Retry scrape feature | `docs/plans/2025-12-25-retry-scrape-design.md` |
| Backup system | `bookmark-manager/docs/backup-info.md` |

### Canvas (`canvas/`)

| Task | Read |
|------|------|
| Canvas design (draft + workspace) | `canvas/docs/plans/2025-12-19-canvas-design.md` |
| Draft to Kasten flow | `canvas/docs/plans/2024-12-19-draft-to-kasten-design.md` |
| Source linking to bookmarks | `docs/plans/2025-12-25-canvas-source-linking-design.md` |

### Kasten (`kasten/`)

| Task | Read |
|------|------|
| Kasten design (Zettelkasten browser) | `kasten/docs/plans/2025-12-19-kasten-design.md` |
| Sources feature | `docs/plans/2025-12-24-kasten-sources-redesign.md` |
| Navigation graph | `kasten/docs/plans/2025-12-19-navigation-graph-redesign.md` |

### KM CLI (`km/`)

| Task | Read |
|------|------|
| CLI tool overview | `km/README.md` |
| CI/CD setup | `km/docs/ci-cd.md` |

### Balance (`balance/`)

| Task | Read |
|------|------|
| Balance design (rhythm tracker) | `docs/plans/2025-12-27-balance-app-design.md` |
| Implementation plan | `docs/plans/2025-12-27-balance-implementation-plan.md` |

## Cross-Service Documentation

| Task | Read |
|------|------|
| Knowledge flow (read → think → browse) | `docs/plans/2025-12-23-knowledge-flow-redesign.md` |
| Bookmark categorization (thesis/pins) | `bookmark-manager/docs/plans/2025-12-22-bookmark-categorization-design.md` |

## Quick Reference

**Tech Stack:** Python 3.11, FastAPI, SQLite (aiosqlite), Jinja2, vanilla JS

**Ports (dev):**
- bookmark-manager: 8001
- canvas: 8002
- kasten: 8003
- balance: 8005

**Domains (prod):**
- bookmark.gstoehl.dev
- canvas.gstoehl.dev
- kasten.gstoehl.dev
- balance.gstoehl.dev

**Key Patterns:**
- All services use brutalist UI (monospace, black borders)
- SQLite databases in `./data/` directories
- Hot reload in dev via uvicorn `--reload`
- K8s uses local images (`imagePullPolicy: Never`)

**Important:** When implementing changes to architecture, services, or infrastructure, update `KNOWLEDGE-SYSTEM-OVERVIEW.md` to keep it in sync with the actual system state.
