# E2E Testing & Dev→Prod Workflow Design

**Date:** 2026-01-10  
**Status:** Design Complete  
**Context:** Establishes automated testing and deployment pipeline to safely ship changes through dev environment validation before production

## Problem Statement

Currently, deployments are manual and error-prone:
- Local Docker builds + manual K3s image import
- No automated testing of deployed services
- Direct production deployments without staging validation
- No CI/CD pipeline

This led to the Balance break timer bug going undetected until production (timer-complete resets break when page loads during active break).

## Goals

1. **Automated dev→prod pipeline** with smoke tests gating production deployments
2. **E2E test coverage** for critical user flows (23 scenarios across 4 services)
3. **Fast feedback loops** via change detection (only rebuild modified services)
4. **Safe deployments** with automatic rollback on failure
5. **Mobile testing capability** via publicly accessible dev environment

## Architecture Overview

### Two-Environment System

**Dev Environment:**
- Namespace: `knowledge-system-dev`
- Path prefix: `/dev` (e.g., `bookmark.gstoehl.dev/dev`)
- Image tags: `:dev`
- Purpose: Smoke test validation before production

**Prod Environment:**
- Namespace: `knowledge-system` (existing)
- Path prefix: `/` (e.g., `bookmark.gstoehl.dev`)
- Image tags: `:latest`
- Purpose: Production services

### Deployment Flow

```
Push to dev branch
    ↓
GitHub Actions: Detect changes (path-based)
    ↓
Build changed services → Push to GHCR as :dev
    ↓
Deploy to knowledge-system-dev namespace
    ↓
Wait for pods ready (5min timeout)
    ↓
Reset dev databases (clean slate)
    ↓
Run API tests (pytest + httpx, ~30s)
    ↓ (if pass)
Run UI tests (Playwright, ~5min)
    ↓ (if pass)
Auto-create PR: dev → main
    ↓ (on merge)
Deploy to prod: Re-tag :dev as :latest
    ↓
Deploy to knowledge-system namespace
    ↓
Wait for pods ready (5min timeout)
    ↓ (if fail)
K8s rolls back automatically + GitHub notifies
```

## Change Detection Strategy

**Path-based detection:**
- Changes in `{service}/` → Rebuild that service only
- Changes in `shared/` → Rebuild ALL services (CSS, templates, components shared across services)

**Rationale:** Simple GitHub Actions path filters. Trade-off: `shared/` changes trigger full rebuild (safe but slower), but this ensures consistency across all services when shared components change.

## Image Management (GHCR)

### Image Naming Convention

- Dev: `ghcr.io/USERNAME/SERVICE:dev` (e.g., `ghcr.io/USERNAME/bookmark-manager:dev`)
- Prod: `ghcr.io/USERNAME/SERVICE:latest`

### Lifecycle

1. **Dev branch push:** Build → Tag as `:dev` → Push to GHCR
2. **Merge to main:** Re-tag `:dev` as `:latest` → Push to GHCR (no rebuild needed)
3. **K3s deployment:** Pull from GHCR (change `imagePullPolicy: Never` → `Always`)

### Benefits

- Eliminates manual `docker save | k3s ctr images import` workflow
- Dev/prod isolation via image tags
- Fast prod deploys (re-tag, no rebuild)
- Centralized image storage

## Kubernetes Configuration

### Namespace Structure

```
k8s/
├── base/              (prod manifests)
│   ├── namespace.yaml (knowledge-system)
│   ├── balance.yaml
│   ├── bookmark-manager.yaml
│   ├── canvas.yaml
│   ├── kasten.yaml
│   └── ingress.yaml
└── dev/               (dev overlays)
    ├── namespace.yaml (knowledge-system-dev)
    ├── balance.yaml
    ├── bookmark-manager.yaml
    ├── canvas.yaml
    ├── kasten.yaml
    └── ingress.yaml
```

### Dev Manifest Differences

**Image tags:** `:dev` instead of `:latest`

**Environment variables:**
- All services: `BASE_PATH=/dev` (for path-based routing)
- Balance: `NEXTDNS_PROFILE_ID=c87dff` (separate dev profile, same API key)

**Secrets:** `balance-secrets-dev` with dev NextDNS profile ID

### Path-based Routing (Traefik)

**Ingress rules:**
- `/dev/*` → `knowledge-system-dev` namespace
- `/*` → `knowledge-system` namespace (prod)

**Example:**
- `bookmark.gstoehl.dev/dev/api/bookmarks` → dev pod
- `bookmark.gstoehl.dev/api/bookmarks` → prod pod

**Implementation:** Update `k8s/base/ingress.yaml` with PathPrefix middleware. Services must handle `BASE_PATH` environment variable.

## Test Infrastructure

### Directory Structure

```
tests/
├── e2e/
│   ├── api/
│   │   ├── test_bookmark_manager.py
│   │   ├── test_canvas.py
│   │   ├── test_kasten.py
│   │   └── test_balance.py
│   ├── ui/
│   │   ├── test_bookmark_manager.py  (7 scenarios)
│   │   ├── test_canvas.py            (5 scenarios)
│   │   ├── test_kasten.py            (4 scenarios)
│   │   └── test_balance.py           (7 scenarios)
│   ├── conftest.py                   (shared fixtures)
│   └── playwright.config.ts
└── requirements-test.txt             (pytest, httpx, playwright)
```

### Test Scenarios (23 total)

**Bookmark Manager (7 scenarios):**
1. Move bookmark between categories
2. Show RSS feeds
3. Add new RSS feed subscription
4. Delete item in "all" overview
5. Dismiss item in RSS reader
6. Delete RSS subscription
7. Cite text from bookmark

**Canvas (5 scenarios):**
1. Show cited text in draft
2. Convert draft to note (make to note)
3. Add note to workspace
4. Connect two notes in workspace
5. Export draft/note

**Kasten (4 scenarios):**
1. Verify note was created from Canvas (source tracking)
2. Navigate between notes (backlinks/forward links)
3. Add note to workspace
4. Verify note appears in workspace

**Balance (7 scenarios):**
1. Break timer bug fix (timer-complete idempotency) ← **Original bug that motivated this design**
2. Log meditation session
3. Log exercise session
4. Change settings
5. View stats
6. Start Pomodoro session
7. Abandon Pomodoro session

### Test Technology Stack

**API tests:** Python pytest + httpx
- Same stack as existing unit tests
- Run against deployed dev URLs
- Fast (~30 seconds total)

**UI tests:** Playwright (Python)
- Browser automation for user flows
- Run against deployed dev URLs
- Slower (~5 minutes total)

**Execution environment:** GitHub-hosted runners (access public dev URLs)

### Test Data Strategy

**Reset dev databases before each test run:**
- GitHub Actions deletes SQLite databases in dev pods before tests
- Tests run against clean state (predictable, no accumulated garbage)
- Trade-off: Can't manually inspect dev environment between test runs

## GitHub Actions Workflows

### Workflow Files

```
.github/
└── workflows/
    ├── deploy-dev.yml       (on push to dev branch)
    └── deploy-prod.yml      (on push to main branch)
```

### Deploy-Dev Workflow

**Trigger:** Push to `dev` branch

**Steps:**

1. **Detect changes**
   - Path filters: Check `shared/`, `bookmark-manager/`, `canvas/`, `kasten/`, `balance/`
   - Output: List of services to rebuild

2. **Build & push images**
   - For each changed service: `docker build -t ghcr.io/USERNAME/SERVICE:dev`
   - Push to GHCR

3. **Deploy to dev namespace**
   - `kubectl apply -f k8s/dev/`
   - `kubectl rollout restart deploy/SERVICE -n knowledge-system-dev`

4. **Wait for pods ready**
   - `kubectl wait --for=condition=ready pod -l app=SERVICE -n knowledge-system-dev --timeout=5m`
   - If timeout → Workflow fails → GitHub notifies

5. **Reset dev databases**
   - `kubectl exec deploy/SERVICE -n knowledge-system-dev -- rm /app/data/*.db`
   - Pods restart, databases recreated from migrations

6. **Run API tests**
   - `pytest tests/e2e/api/ --base-url=https://bookmark.gstoehl.dev/dev`
   - If fail → Workflow fails → GitHub notifies

7. **Run UI tests**
   - `playwright test tests/e2e/ui/`
   - If fail → Workflow fails → GitHub notifies

8. **Auto-create PR**
   - If all tests pass: `gh pr create --base main --head dev --title "Deploy to prod" --body "All smoke tests passed"`

### Deploy-Prod Workflow

**Trigger:** Push to `main` branch (after PR merge)

**Steps:**

1. **Re-tag images** (no rebuild)
   - Pull `:dev` images from GHCR
   - Re-tag as `:latest`
   - Push to GHCR

2. **Deploy to prod namespace**
   - `kubectl apply -f k8s/base/`
   - `kubectl rollout restart deploy/SERVICE -n knowledge-system`

3. **Wait for pods ready**
   - `kubectl wait --for=condition=ready pod -l app=SERVICE -n knowledge-system --timeout=5m`
   - If timeout → K8s automatically rolls back → GitHub notifies

### Branch Protection

**Main branch rules:**
- Require PR before merging
- Block direct pushes
- All changes must flow through `dev` → PR → `main`

**Rationale:** No escape hatches. Even hotfixes go through dev testing for safety.

## Monitoring & Notifications

### Deployment Failure Handling

**Strategy:** Kubernetes automatic rollback + GitHub notifications

**How it works:**
1. New deployment fails health checks
2. K8s `rollingUpdate` strategy keeps old pods running
3. New pods never become ready
4. GitHub Actions workflow times out (5 minutes)
5. Workflow fails → GitHub sends notification (email/mobile app)

**No manual intervention needed** for rollback. K8s handles it automatically.

## Environment-Specific Configuration

### Balance NextDNS Integration

**Prod:** Uses existing `NEXTDNS_PROFILE_ID` (from `balance-secrets`)  
**Dev:** Uses separate profile `NEXTDNS_PROFILE_ID=c87dff` (from `balance-secrets-dev`)  
**Shared:** Same `NEXTDNS_API_KEY` in both environments

**Rationale:** Dev break enforcement doesn't affect prod YouTube access during testing.

## Components to Implement

### Infrastructure
- [ ] `k8s/dev/` manifests (namespace, deployments with `:dev` tags)
- [ ] Updated `k8s/base/ingress.yaml` for path-based routing
- [ ] `BASE_PATH` environment variable handling in all services
- [ ] `balance-secrets-dev` secret with `NEXTDNS_PROFILE_ID=c87dff`
- [ ] GHCR imagePullSecrets configuration in K3s

### GitHub Actions
- [ ] `.github/workflows/deploy-dev.yml` (build, deploy, test, PR)
- [ ] `.github/workflows/deploy-prod.yml` (re-tag, deploy)
- [ ] Branch protection rules on `main`

### Test Infrastructure
- [ ] `tests/e2e/api/` - pytest + httpx tests (4 files)
- [ ] `tests/e2e/ui/` - Playwright tests (4 files, 23 scenarios)
- [ ] `playwright.config.ts`
- [ ] `conftest.py` with shared fixtures
- [ ] `requirements-test.txt`

### Service Changes
- [ ] All services handle `BASE_PATH` env var for routing

## Success Criteria

1. **Dev deployment succeeds:** Push to `dev` → builds → deploys → tests run
2. **Tests gate prod:** Failed smoke tests block PR creation
3. **Prod deployment succeeds:** Merge PR → prod deploys with re-tagged images
4. **Rollback works:** Broken deployment keeps old pods running
5. **Balance bug validated:** Timer-complete idempotency test catches regression

## Next Steps

Use `writing-plans` skill to create detailed implementation plan with task sequencing and dependencies.

## References

- Original dev→prod workflow discussion: `~/.claude/projects/-home-ags-knowledge-system/27685d46-bf4d-4165-ae65-85533ed06723.jsonl` (Jan 7-9, 2026)
- Balance break timer bug fix: `balance/src/routers/sessions.py:249` (idempotency guard)
- Existing K8s operations: `k8s/OPERATIONS.md`
