#!/bin/bash
# Rebuild and deploy services to K3s
# Usage: ./scripts/rebuild-k3s.sh

set -e

cd /home/ags/knowledge-system

SERVICES=("bookmark-manager" "canvas" "kasten" "balance")

echo "=== K3s Rebuild & Deploy ==="
echo ""
echo "Select services to rebuild:"
echo "  1) bookmark-manager"
echo "  2) canvas"
echo "  3) kasten"
echo "  4) balance"
echo "  a) all"
echo ""
echo "Enter selection (e.g., '1', '14', '234', 'a'): "
read -r selection

# Parse selection
selected=()
if [[ "$selection" == "a" || "$selection" == "all" ]]; then
    selected=("bookmark-manager" "canvas" "kasten" "balance")
else
    [[ "$selection" == *"1"* ]] && selected+=("bookmark-manager")
    [[ "$selection" == *"2"* ]] && selected+=("canvas")
    [[ "$selection" == *"3"* ]] && selected+=("kasten")
    [[ "$selection" == *"4"* ]] && selected+=("balance")
fi

if [ ${#selected[@]} -eq 0 ]; then
    echo "No services selected. Exiting."
    exit 1
fi

echo ""
echo "Will rebuild: ${selected[*]}"
echo ""

# Build, save, import, restart each service
for svc in "${selected[@]}"; do
    echo "=== Building $svc ==="
    # All services use root context for shared/ directory
    docker build -f "$svc/Dockerfile" -t "$svc:latest" .

    echo "=== Saving $svc ==="
    docker save "$svc:latest" -o "/tmp/$svc.tar"

    echo "=== Importing $svc to k3s ==="
    sudo k3s ctr images import "/tmp/$svc.tar"

    echo "=== Restarting $svc ==="
    kubectl rollout restart "deploy/$svc" -n knowledge-system

    echo "=== $svc done ==="
    echo ""
done

echo "All done! Watching pods..."
kubectl get pods -n knowledge-system -w
