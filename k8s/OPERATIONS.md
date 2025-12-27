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

# Describe a pod (for debugging)
kubectl describe pod -l app=bookmark-manager -n knowledge-system

# Check certificate status
kubectl get certificate -n knowledge-system
```

## Updating Images

```bash
# Rebuild and reimport image
cd /home/ags/knowledge-system/bookmark-manager
docker build -t bookmark-manager:latest .
docker save bookmark-manager:latest | sudo k3s ctr images import -
kubectl rollout restart deploy/bookmark-manager -n knowledge-system
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

## File Locations

- Manifests: `/home/ags/knowledge-system/k8s/base/`
- Kubeconfig: `~/.kube/config`
- Backups: `/home/ags/backups/k3s-migration-2025-12-21/`
