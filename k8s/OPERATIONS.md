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

## Updating Images

```bash
# Rebuild and reimport image (example: bookmark-manager)
cd /home/ags/knowledge-system/bookmark-manager
docker build -t bookmark-manager:latest .
docker save bookmark-manager:latest | sudo k3s ctr images import -
kubectl rollout restart deploy/bookmark-manager -n knowledge-system

# Same pattern for other services:
# canvas, kasten, balance, telegram-bot
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

## File Locations

- Manifests: `/home/ags/knowledge-system/k8s/base/`
- Kubeconfig: `~/.kube/config`
- Backups: `/home/ags/backups/k3s-migration-2025-12-21/`

## Manifest Overview

| File | Resources |
|------|-----------|
| `namespace.yaml` | Namespace: knowledge-system |
| `clusterissuer.yaml` | Let's Encrypt cert-manager issuer |
| `pvcs.yaml` | PVCs for all services |
| `ingress.yaml` | Ingress for all domains (split: balance vs others) |
| `middleware-balance-check.yaml` | Traefik ForwardAuth for break enforcement |
| `bookmark-manager.yaml` | Deployment + Service |
| `canvas.yaml` | Deployment + Service |
| `kasten.yaml` | Deployment + Service |
| `balance.yaml` | Deployment + Service |
| `telegram-bot.yaml` | Deployment (no service, outbound only) |
| `networkpolicy-*.yaml` | Zero-trust egress rules per service |
