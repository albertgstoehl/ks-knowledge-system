# K3s Operations Cheatsheet

## Common Commands

```bash
# Set KUBECONFIG (add to ~/.bashrc)
export KUBECONFIG=~/.kube/config

# View all resources
kubectl get all -n knowledge-system

# View logs
kubectl logs -f deploy/bookmark-manager -n knowledge-system
kubectl logs -f deploy/canvas -n knowledge-system
kubectl logs -f deploy/kasten -n knowledge-system
kubectl logs -f deploy/balance -n knowledge-system
kubectl logs -f deploy/train -n knowledge-system

# Restart a deployment
kubectl rollout restart deploy/bookmark-manager -n knowledge-system

# Shell into a pod
kubectl exec -it deploy/bookmark-manager -n knowledge-system -- /bin/sh

# View network policies
kubectl get networkpolicy -n knowledge-system

# View middlewares
kubectl get middleware -n knowledge-system

# Describe a pod (for debugging)
kubectl describe pod -l app=bookmark-manager -n knowledge-system

# Check certificate status
kubectl get certificate -n knowledge-system
```

## GHCR (GitHub Container Registry) Setup

### One-Time Setup: Create GHCR Pull Secrets

**Prerequisites:**
- GitHub Personal Access Token with `write:packages` scope
- NextDNS API key (for Balance dev environment)

**Create GHCR pull secrets (prod and dev):**

```bash
# Production namespace
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=albertgstoehl \
  --docker-password=YOUR_GITHUB_PAT \
  -n knowledge-system

# Dev namespace (create dev namespace first)
kubectl apply -f k8s/dev/namespace.yaml

kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=albertgstoehl \
  --docker-password=YOUR_GITHUB_PAT \
  -n knowledge-system-dev
```

**Create Balance secrets for dev:**

```bash
# Dev uses separate secrets from prod
kubectl create secret generic balance-secrets-dev \
  --from-literal=nextdns-api-key=YOUR_NEXTDNS_API_KEY \
  --from-literal=nextdns-profile-id=c87dff \
  -n knowledge-system-dev

# Optional: Create bookmark-manager secrets for dev (if needed)
kubectl create secret generic bookmark-manager-secrets-dev \
  --from-literal=JINA_API_KEY=YOUR_JINA_KEY \
  --from-literal=CLAUDE_CODE_OAUTH_TOKEN=YOUR_TOKEN \
  -n knowledge-system-dev
```

**Verify secrets:**

```bash
kubectl get secrets -n knowledge-system
kubectl get secrets -n knowledge-system-dev
```

### CI/CD Pipeline

**Workflow Files:**
- `.github/workflows/deploy-dev.yml` - Dev deployment + E2E tests
- `.github/workflows/deploy-prod.yml` - Production deployment

**Dev Workflow** (triggered on push to `dev` branch):

1. **Detect Changes** - Determines which services changed
2. **Build & Push** - Builds Docker images for changed services → `ghcr.io/albertgstoehl/{service}:dev`
3. **Deploy to Dev** - Applies manifests to `knowledge-system-dev` namespace
4. **Reset Databases** - Wipes dev databases for clean test state
5. **Run Tests**:
   - 15 API tests (pytest + httpx)
   - 8 UI smoke tests (Playwright)
6. **Create PR** - Auto-creates PR to `master` if all tests pass

**Production Workflow** (triggered on push to `master` branch):

1. **Re-tag Images** - Tags `:dev` images as `:latest` (no rebuild)
2. **Push to GHCR** - Pushes `:latest` tags
3. **Deploy to Prod** - Applies to `knowledge-system` namespace
4. **Wait for Ready** - Waits for all pods to be ready (5min timeout)

**GitHub Actions Runner:**
- Self-hosted runner at `~/actions-runner/` on K3s server
- Must be running for workflows to execute
- Start: `cd ~/actions-runner && ./run.sh`
- Check status: `cd ~/actions-runner && ./run.sh status`

**Image Tags:**
- Dev environment: `ghcr.io/albertgstoehl/{service}:dev`
- Prod environment: `ghcr.io/albertgstoehl/{service}:latest`

**GHCR Package Visibility:**
- All packages must be **public** for K8s to pull without authentication
- Check: https://github.com/albertgstoehl?tab=packages
- If private, pods will get `ImagePullBackOff` errors

### Manual Image Update (Legacy)

For local testing without CI/CD:

```bash
# Build and push to GHCR manually
cd /home/ags/knowledge-system/balance
docker build -t ghcr.io/albertgstoehl/balance:dev .
docker push ghcr.io/albertgstoehl/balance:dev

# Update deployment
kubectl rollout restart deploy/balance -n knowledge-system-dev
```

## Backup

```bash
# Backup PVC data
kubectl cp knowledge-system/$(kubectl get pod -n knowledge-system -l app=bookmark-manager -o jsonpath='{.items[0].metadata.name}'):/app/data/bookmarks.db ./backup-bookmarks.db

kubectl cp knowledge-system/$(kubectl get pod -n knowledge-system -l app=canvas -o jsonpath='{.items[0].metadata.name}'):/app/data/canvas.db ./backup-canvas.db

kubectl cp knowledge-system/$(kubectl get pod -n knowledge-system -l app=kasten -o jsonpath='{.items[0].metadata.name}'):/app/data/kasten.db ./backup-kasten.db

kubectl cp knowledge-system/$(kubectl get pod -n knowledge-system -l app=balance -o jsonpath='{.items[0].metadata.name}'):/app/data/balance.db ./backup-balance.db

kubectl cp knowledge-system/$(kubectl get pod -n knowledge-system -l app=train -o jsonpath='{.items[0].metadata.name}'):/app/data/train.db ./backup-train.db
```

## Apply All Manifests

```bash
kubectl apply -f /home/ags/knowledge-system/k8s/base/
```

## Break Enforcement (Balance → Knowledge System)

Balance enforces breaks by blocking access to bookmark/canvas/kasten during breaks via Traefik ForwardAuth middleware.

### How it works

```
User Request → Traefik → ForwardAuth (balance/api/auth-check)
                              ↓
                    On break? ──→ 302 redirect to balance.gstoehl.dev
                    Not on break? ──→ 200, pass through to service
```

### Components

| File | Purpose |
|------|---------|
| `middleware-balance-check.yaml` | Traefik Middleware CRD (uses FQDN: balance.knowledge-system.svc.cluster.local) |
| `ingress.yaml` | Split ingress: balance (no middleware) + others (with middleware) |
| `balance/src/routers/sessions.py` | `/api/auth-check` endpoint returns 200 or 302 |

### Debugging break enforcement

```bash
# Check middleware exists
kubectl get middleware balance-check -n knowledge-system

# Check if balance is responding
kubectl exec -it deploy/balance -n knowledge-system -- curl -s localhost:8000/api/check

# Test auth-check endpoint directly
kubectl exec -it deploy/balance -n knowledge-system -- curl -s -o /dev/null -w "%{http_code}" localhost:8000/api/auth-check

# View Traefik logs for middleware issues
kubectl logs -f -n kube-system -l app.kubernetes.io/name=traefik
```

## CI/CD Troubleshooting

### Workflow Debugging

**Check workflow status:**
```bash
gh run list --workflow deploy-dev.yml --limit 5
gh run list --workflow deploy-prod.yml --limit 5
```

**View failed workflow:**
```bash
gh run view <RUN_ID> --log-failed
```

**Watch workflow in real-time:**
```bash
gh run watch <RUN_ID>
```

### Common CI/CD Issues

**Issue: Workflow not triggered**
- **Check**: Is the GitHub Actions runner running?
  ```bash
  ssh user@server
  cd ~/actions-runner && ./run.sh status
  ```
- **Fix**: Start runner: `./run.sh`

**Issue: Image build fails**
- **Check**: Build logs in GitHub Actions
- **Common cause**: Missing dependencies in Dockerfile
- **Fix**: Test build locally first:
  ```bash
  docker build -t test-image:latest ./balance
  ```

**Issue: Pods stuck in ImagePullBackOff**
- **Cause**: GHCR images are private or pull secret is invalid
- **Check**: 
  ```bash
  kubectl describe pod -l app=balance -n knowledge-system-dev
  kubectl get secret ghcr-pull-secret -n knowledge-system-dev
  ```
- **Fix Option 1** (Recommended): Make GHCR packages public
  - Go to https://github.com/albertgstoehl?tab=packages
  - Set visibility to "Public" for each package
- **Fix Option 2**: Recreate pull secret with fresh GitHub PAT:
  ```bash
  kubectl delete secret ghcr-pull-secret -n knowledge-system-dev
  kubectl create secret docker-registry ghcr-pull-secret \
    --docker-server=ghcr.io \
    --docker-username=albertgstoehl \
    --docker-password=$(cat ~/.config/gh/hosts.yml | grep oauth_token | awk '{print $2}') \
    -n knowledge-system-dev
  ```

**Issue: E2E tests fail with "Connection refused"**
- **Cause**: Pods not ready when tests run
- **Check**: Workflow logs for "Wait for rollout to complete" step
- **Fix**: Increase timeout in deploy-dev.yml (default: 3min)

**Issue: E2E tests fail during production break**
- **Cause**: Tests hitting production URLs instead of dev
- **Check**: Test fixture URLs in `tests/conftest.py`
- **Verify**: Dev routes have priority 100, should not be blocked
  ```bash
  kubectl get ingress knowledge-system-dev-ingress -n knowledge-system-dev -o yaml | grep priority
  ```

**Issue: PR not auto-created after tests pass**
- **Cause**: PR already exists or GitHub CLI authentication failed
- **Check**: 
  ```bash
  gh pr list --state open
  ```
- **Manual creation**:
  ```bash
  gh pr create --base master --head dev --title "Deploy to prod (tests passed)"
  ```

**Issue: Production deployment fails with "pods not ready"**
- **Cause**: New pods can't pull `:latest` images OR application error
- **Check pod logs**:
  ```bash
  kubectl logs -l app=balance -n knowledge-system --tail=50
  ```
- **Check pod events**:
  ```bash
  kubectl describe pod -l app=balance -n knowledge-system
  ```

### Workflow File Modifications

**Skip database reset in dev (for debugging):**

Edit `.github/workflows/deploy-dev.yml`, comment out:
```yaml
# - name: Reset databases
#   run: |
#     kubectl exec -n knowledge-system-dev deployment/balance -- sh -c "rm -f /app/data/*.db || true"
```

**Run tests against production (dangerous!):**

Edit `tests/conftest.py`:
```python
def base_url():
    return os.getenv("BASE_URL", "https://bookmark.gstoehl.dev")  # Remove /dev
```

**Disable auto-PR creation:**

Edit `.github/workflows/deploy-dev.yml`, comment out the `create-pr` job.

## Rollback to Docker Compose

If K3s fails, revert:

```bash
# Stop K3s
sudo systemctl stop k3s

# Restore UFW routed deny (optional - K3s NetworkPolicy no longer needed)
sudo ufw default deny routed
sudo ufw reload

# Re-add Docker egress block (optional)
sudo iptables -I DOCKER-USER 3 -m comment --comment "codex-hardening" -j DROP

# Start Docker Compose
cd /home/ags/knowledge-system && docker compose up -d

# Verify services
curl http://bookmark.gstoehl.dev/health
```

## Network Policy Summary

| Pod | Egress Allowed |
|-----|----------------|
| bookmark-manager | DNS + internal canvas + external HTTP/HTTPS |
| canvas | DNS + internal pods only |
| kasten | DNS only |
| balance | DNS only |
| train | DNS only |
| telegram-bot | DNS + bookmark-manager + Telegram API |

## Environment Isolation (Dev vs Prod)

The system has two completely isolated environments:

| Environment | Namespace | URL Pattern | Database | Image Tag |
|-------------|-----------|-------------|----------|-----------|
| **Development** | `knowledge-system-dev` | `https://{service}.gstoehl.dev/dev/` | Separate PVCs (1Gi each) | `:dev` |
| **Production** | `knowledge-system` | `https://{service}.gstoehl.dev/` | Production PVCs (1-5Gi) | `:latest` |

### Key Isolation Features

**1. Separate Databases**
- Each environment has its own PersistentVolumeClaims
- Dev databases persist across pod restarts (no longer using emptyDir)
- Dev database reset happens before E2E tests for clean state

**2. Path-Based Routing with Priority**
```
https://bookmark.gstoehl.dev/dev/
  ↓
Traefik routes by priority:
  Priority 100 (DEV)  → /dev path → knowledge-system-dev/bookmark-manager
  Priority 10  (PROD) → /    path → knowledge-system/bookmark-manager
```

**3. Middleware Isolation**
- **Dev Ingress**: Uses `strip-dev-prefix` middleware ONLY
- **Prod Ingress**: Uses `balance-check` (break enforcement) middleware ONLY
- Production breaks do NOT affect dev environment

**4. Router Priority Configuration**
```bash
# Dev routes match FIRST (higher priority)
kubectl -n knowledge-system-dev annotate ingress knowledge-system-dev-ingress \
  traefik.ingress.kubernetes.io/router.priority="100"

# Prod routes match SECOND (lower priority)
kubectl -n knowledge-system annotate ingress knowledge-system-ingress \
  traefik.ingress.kubernetes.io/router.priority="10"
```

### Common Issues

**Issue: Dev environment blocked during production break**
- **Cause**: Production `balance-check` middleware was applying to `/dev` routes
- **Fix**: Router priority ensures dev routes match before prod routes
- **Verify**: `curl -I https://bookmark.gstoehl.dev/dev/` should return 200 even during prod break

**Issue: Dev database wiped on pod restart**
- **Cause**: Old manifests used `emptyDir` instead of PVC
- **Fix**: Dev now uses persistent volumes (see `k8s/dev/pvcs.yaml`)
- **Verify**: `kubectl get pvc -n knowledge-system-dev`

**Issue: ImagePullBackOff in dev**
- **Cause**: GHCR packages are private OR `ghcr-pull-secret` is missing/expired
- **Fix**: Make packages public OR recreate pull secret with fresh GitHub PAT

## Ingress Configuration

| Ingress | Namespace | Hosts | Path | Middleware | Priority |
|---------|-----------|-------|------|------------|----------|
| balance-ingress | knowledge-system | balance.gstoehl.dev | / | None | (default) |
| knowledge-system-ingress | knowledge-system | bookmark, canvas, kasten, train | / | balance-check | 10 |
| knowledge-system-dev-ingress | knowledge-system-dev | all services | /dev | strip-dev-prefix | 100 |

## CronJobs

### Canvas Daily Wipe

Clears the canvas draft at midnight (Europe/Zurich) to enforce intentional note-taking.

```bash
# Check CronJob status
kubectl get cronjob -n knowledge-system

# View recent job history
kubectl get jobs -n knowledge-system | grep canvas-daily-wipe

# Manual trigger (for testing)
kubectl create job --from=cronjob/canvas-daily-wipe manual-wipe -n knowledge-system
```

### Balance Session Analysis

Runs daily at 22:00 to analyze Claude Code usage during Balance sessions. This is a **host-level cron job** (not K8s CronJob) because it needs access to `~/.claude/projects/` JSONL files.

**Location:** Server crontab (`crontab -e`)
**Script:** `scripts/balance-analysis/analyze_sessions.py`
**Log:** `/var/log/balance-analysis.log`

**Setup (one-time):**
```bash
# Add to crontab
crontab -e

# Add this line:
0 22 * * * cd /home/ags/knowledge-system && /usr/bin/python3 scripts/balance-analysis/analyze_sessions.py >> /var/log/balance-analysis.log 2>&1

# Create log file
sudo touch /var/log/balance-analysis.log
sudo chown ags:ags /var/log/balance-analysis.log
```

**Manual run:**
```bash
cd ~/knowledge-system && python3 scripts/balance-analysis/analyze_sessions.py
```

**Check logs:**
```bash
tail -f /var/log/balance-analysis.log
```

## APScheduler Considerations (Balance & Bookmark-Manager)

Balance and Bookmark-Manager use APScheduler for background jobs. Keep in mind:

| Service | Jobs | Interval |
|---------|------|----------|
| Balance | Session expiry, evening cutoff | 30s, 1m |
| Bookmark-Manager | Bookmark expiry, feed item cleanup | 5m |

| Concern | Mitigation |
|---------|------------|
| Pod restarts | Jobs run on startup after DB init |
| Multiple replicas | Don't scale beyond 1 replica (scheduler would run on each) |
| Slow external APIs | Use async jobs with timeouts to prevent blocking |
| Memory usage | Negligible with few interval jobs |

If scaling becomes necessary, switch to a distributed task queue (e.g., Celery + Redis) or leader election for scheduler.

## File Locations

- Manifests: `/home/ags/knowledge-system/k8s/base/`
- Kubeconfig: `~/.kube/config`
- Backups: `/home/ags/backups/k3s-migration-2025-12-21/`

## Testing

### E2E Test Structure

```
tests/
├── conftest.py              # Shared fixtures (URLs, Playwright browser)
├── e2e/
│   ├── api/                 # API tests (httpx)
│   │   ├── test_balance.py      # 5 tests: health, sessions, priorities
│   │   ├── test_bookmarks.py    # 5 tests: create, list, move, delete
│   │   ├── test_canvas.py       # 3 tests: draft operations
│   │   └── test_kasten.py       # 2 tests: list notes, get note
│   └── ui/                  # UI smoke tests (Playwright)
│       └── test_smoke.py        # 8 tests: page load + no console errors
└── requirements-test.txt    # pytest, httpx, playwright
```

### Running Tests Locally

```bash
# Install test dependencies
pip install -r tests/requirements-test.txt
playwright install chromium

# Run API tests
pytest tests/e2e/api/ -v

# Run UI tests
pytest tests/e2e/ui/ -v

# Run all tests
pytest tests/e2e/ -v
```

### Test URLs

Tests use environment variable `BASE_URL` (defaults to dev):

```bash
# Test against dev (default)
pytest tests/e2e/api/ -v

# Test against prod (use with caution!)
BASE_URL=https://bookmark.gstoehl.dev pytest tests/e2e/api/ -v
```

## Manifest Overview

| Directory/File | Resources |
|----------------|-----------|
| **Production** (`k8s/base/`) | |
| `namespace.yaml` | Namespace: knowledge-system |
| `clusterissuer.yaml` | Let's Encrypt cert-manager issuer |
| `pvcs.yaml` | PVCs for all services (1-5Gi) |
| `ingress.yaml` | Ingress for all domains (split: balance vs others) |
| `middleware-balance-check.yaml` | Traefik ForwardAuth for break enforcement |
| `bookmark-manager.yaml` | Deployment + Service |
| `canvas.yaml` | Deployment + Service |
| `kasten.yaml` | Deployment + Service |
| `balance.yaml` | Deployment + Service |
| `train.yaml` | Deployment + Service |
| `telegram-bot.yaml` | Deployment (no service, outbound only) |
| `networkpolicy-*.yaml` | Zero-trust egress rules per service |
| `canvas-daily-wipe.yaml` | CronJob for nightly draft wipe (midnight Zurich) |
| **Development** (`k8s/dev/`) | |
| `namespace.yaml` | Namespace: knowledge-system-dev |
| `pvcs.yaml` | Dev PVCs (1Gi each, isolated from prod) |
| `ingress.yaml` | Dev ingress (path `/dev`, priority 100) |
| `middleware-strip-dev-prefix.yaml` | Removes /dev prefix before routing |
| `balance.yaml` | Dev deployment (image: `:dev`, BASE_PATH=/dev) |
| `bookmark-manager.yaml` | Dev deployment |
| `canvas.yaml` | Dev deployment |
| `kasten.yaml` | Dev deployment |
