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

### CI/CD Image Workflow

**Dev branch push → GitHub Actions:**
1. Builds images: `ghcr.io/albertgstoehl/{service}:dev`
2. Pushes to GHCR
3. Deploys to `knowledge-system-dev` namespace
4. Runs E2E tests
5. Auto-creates PR to main if tests pass

**Main branch merge → GitHub Actions:**
1. Re-tags `:dev` images as `:latest` (no rebuild)
2. Pushes `:latest` to GHCR
3. Deploys to `knowledge-system` namespace (prod)

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
| telegram-bot | DNS + bookmark-manager + Telegram API |

## Ingress Configuration

| Ingress | Hosts | Middleware |
|---------|-------|------------|
| balance-ingress | balance.gstoehl.dev | None |
| knowledge-system-ingress | bookmark, canvas, kasten | balance-check (ForwardAuth) |

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

## Manifest Overview

| File | Resources |
|------|-----------|
| `base/namespace.yaml` | Namespace: knowledge-system |
| `base/clusterissuer.yaml` | Let's Encrypt cert-manager issuer |
| `base/pvcs.yaml` | PVCs for all services |
| `base/ingress.yaml` | Ingress for all domains (split: balance vs others) |
| `base/middleware-balance-check.yaml` | Traefik ForwardAuth for break enforcement |
| `base/bookmark-manager.yaml` | Deployment + Service |
| `base/canvas.yaml` | Deployment + Service |
| `base/kasten.yaml` | Deployment + Service |
| `base/balance.yaml` | Deployment + Service |
| `base/telegram-bot.yaml` | Deployment (no service, outbound only) |
| `base/networkpolicy-*.yaml` | Zero-trust egress rules per service |
| `canvas-daily-wipe.yaml` | CronJob for nightly draft wipe (midnight Zurich) |
