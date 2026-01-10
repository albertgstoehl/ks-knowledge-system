# E2E Testing & Dev→Prod Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build automated dev→prod deployment pipeline with E2E smoke tests gating production releases

**Architecture:** Two K8s namespaces (dev/prod) with path-based routing, GHCR image registry, GitHub Actions CI/CD, Playwright + pytest smoke tests

**Tech Stack:** K3s, Traefik, GitHub Actions, GHCR, Playwright (Python), pytest, httpx, FastAPI

**Design Doc:** `docs/plans/2026-01-10-e2e-testing-devprod-workflow-design.md`

---

## Task 1: Create Dev Namespace K8s Manifests

**Goal:** Set up `knowledge-system-dev` namespace with dev-specific configurations

**Files:**
- Create: `k8s/dev/namespace.yaml`
- Create: `k8s/dev/balance.yaml`
- Create: `k8s/dev/bookmark-manager.yaml`
- Create: `k8s/dev/canvas.yaml`
- Create: `k8s/dev/kasten.yaml`
- Reference: `k8s/base/balance.yaml` (template for dev manifests)

**Step 1: Create dev namespace manifest**

Create `k8s/dev/namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: knowledge-system-dev
```

**Step 2: Create Balance dev deployment**

Copy `k8s/base/balance.yaml` to `k8s/dev/balance.yaml` and modify:

```yaml
# /home/ags/knowledge-system/k8s/dev/balance.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: balance
  namespace: knowledge-system-dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: balance
  template:
    metadata:
      labels:
        app: balance
    spec:
      containers:
        - name: balance
          image: ghcr.io/USERNAME/balance:dev  # Change from docker.io/library/balance:latest
          imagePullPolicy: Always  # Change from Never
          ports:
            - containerPort: 8000
          env:
            - name: TZ
              value: "Europe/Zurich"
            - name: DATABASE_URL
              value: "./data/balance.db"
            - name: BASE_PATH  # NEW
              value: "/dev"
            - name: NEXTDNS_API_KEY
              valueFrom:
                secretKeyRef:
                  name: balance-secrets-dev  # Change from balance-secrets
                  key: nextdns-api-key
                  optional: true
            - name: NEXTDNS_PROFILE_ID
              valueFrom:
                secretKeyRef:
                  name: balance-secrets-dev  # Change from balance-secrets
                  key: nextdns-profile-id
                  optional: true
          volumeMounts:
            - name: data
              mountPath: /app/data
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "200m"
      volumes:
        - name: data
          emptyDir: {}  # Dev uses ephemeral storage (no PVC needed)
      imagePullSecrets:
        - name: ghcr-pull-secret  # NEW: for GHCR authentication
---
apiVersion: v1
kind: Service
metadata:
  name: balance
  namespace: knowledge-system-dev
spec:
  selector:
    app: balance
  ports:
    - port: 8000
      targetPort: 8000
  type: ClusterIP
```

**Step 3: Create bookmark-manager dev deployment**

Copy `k8s/base/bookmark-manager.yaml` to `k8s/dev/bookmark-manager.yaml` and modify similarly:
- namespace: `knowledge-system-dev`
- image: `ghcr.io/USERNAME/bookmark-manager:dev`
- imagePullPolicy: `Always`
- Add `BASE_PATH: /dev` env var
- volumes: `emptyDir: {}` (no PVC)
- Add `imagePullSecrets`

**Step 4: Create canvas dev deployment**

Copy `k8s/base/canvas.yaml` to `k8s/dev/canvas.yaml` with same modifications.

**Step 5: Create kasten dev deployment**

Copy `k8s/base/kasten.yaml` to `k8s/dev/kasten.yaml` with same modifications.

**Step 6: Verify manifest syntax**

Run: `kubectl apply --dry-run=client -f k8s/dev/`
Expected: No errors, validates YAML syntax

**Step 7: Commit dev manifests**

```bash
git add k8s/dev/
git commit -m "feat: add dev namespace K8s manifests for CI/CD pipeline"
```

---

## Task 2: Update Prod Manifests for GHCR

**Goal:** Update production manifests to pull from GHCR instead of local images

**Files:**
- Modify: `k8s/base/balance.yaml`
- Modify: `k8s/base/bookmark-manager.yaml`
- Modify: `k8s/base/canvas.yaml`
- Modify: `k8s/base/kasten.yaml`

**Step 1: Update Balance prod manifest**

In `k8s/base/balance.yaml`, change:

```yaml
# OLD:
image: docker.io/library/balance:latest
imagePullPolicy: Never

# NEW:
image: ghcr.io/USERNAME/balance:latest
imagePullPolicy: Always
```

Add imagePullSecrets to spec:

```yaml
spec:
  template:
    spec:
      imagePullSecrets:
        - name: ghcr-pull-secret
      containers:
        - name: balance
          image: ghcr.io/USERNAME/balance:latest
          imagePullPolicy: Always
```

**Step 2: Update bookmark-manager prod manifest**

Same changes in `k8s/base/bookmark-manager.yaml`

**Step 3: Update canvas prod manifest**

Same changes in `k8s/base/canvas.yaml`

**Step 4: Update kasten prod manifest**

Same changes in `k8s/base/kasten.yaml`

**Step 5: Verify manifest syntax**

Run: `kubectl apply --dry-run=client -f k8s/base/`
Expected: No errors

**Step 6: Commit prod manifest updates**

```bash
git add k8s/base/*.yaml
git commit -m "feat: update prod manifests to pull from GHCR"
```

---

## Task 3: Implement BASE_PATH Support in Services

**Goal:** Make all services handle `BASE_PATH` environment variable for path-based routing

**Files:**
- Modify: `balance/src/main.py`
- Modify: `bookmark-manager/src/main.py`
- Modify: `canvas/src/main.py`
- Modify: `kasten/src/main.py`

**Step 1: Add BASE_PATH to Balance**

In `balance/src/main.py`, add after imports:

```python
import os

# Support path-based routing (e.g., /dev prefix for dev environment)
BASE_PATH = os.getenv("BASE_PATH", "").rstrip("/")

app = FastAPI(
    title="Balance",
    lifespan=lifespan,
    root_path=BASE_PATH  # NEW: FastAPI handles path prefix automatically
)
```

**Step 2: Test Balance BASE_PATH locally**

Run:
```bash
cd balance
BASE_PATH=/dev python -m uvicorn src.main:app --reload --port 8005
```

Visit: `http://localhost:8005/dev/health`
Expected: Returns `{"status": "healthy"}`

**Step 3: Add BASE_PATH to bookmark-manager**

In `bookmark-manager/src/main.py`:

```python
import os

BASE_PATH = os.getenv("BASE_PATH", "").rstrip("/")

app = FastAPI(
    title="Bookmark Manager API",
    description="Minimal bookmark management with semantic search",
    version="0.1.0",
    root_path=BASE_PATH  # NEW
)
```

**Step 4: Add BASE_PATH to canvas**

In `canvas/src/main.py`, add `root_path=BASE_PATH` to FastAPI initialization

**Step 5: Add BASE_PATH to kasten**

In `kasten/src/main.py`, add `root_path=BASE_PATH` to FastAPI initialization

**Step 6: Commit BASE_PATH support**

```bash
git add balance/src/main.py bookmark-manager/src/main.py canvas/src/main.py kasten/src/main.py
git commit -m "feat: add BASE_PATH support for path-based routing in all services"
```

---

## Task 4: Update Ingress for Path-Based Routing

**Goal:** Configure Traefik ingress to route `/dev/*` to dev namespace, `/*` to prod

**Files:**
- Modify: `k8s/base/ingress.yaml`
- Reference: `docs/plans/2026-01-10-e2e-testing-devprod-workflow-design.md` (routing design)

**Step 1: Read existing ingress configuration**

Run: `cat k8s/base/ingress.yaml`
Understand: Current routing rules

**Step 2: Add dev path prefix middleware**

Create `k8s/dev/middleware-stripprefix.yaml`:

```yaml
apiVersion: traefik.containo.us/v1alpha1
kind: Middleware
metadata:
  name: strip-dev-prefix
  namespace: knowledge-system-dev
spec:
  stripPrefix:
    prefixes:
      - /dev
```

**Step 3: Create dev ingress rules**

Create `k8s/dev/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: knowledge-system-dev-ingress
  namespace: knowledge-system-dev
  annotations:
    traefik.ingress.kubernetes.io/router.middlewares: knowledge-system-dev-strip-dev-prefix@kubernetescrd
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: traefik
  tls:
    - hosts:
        - bookmark.gstoehl.dev
        - canvas.gstoehl.dev
        - kasten.gstoehl.dev
        - balance.gstoehl.dev
      secretName: knowledge-system-dev-tls
  rules:
    - host: bookmark.gstoehl.dev
      http:
        paths:
          - path: /dev
            pathType: Prefix
            backend:
              service:
                name: bookmark-manager
                port:
                  number: 8001
    - host: canvas.gstoehl.dev
      http:
        paths:
          - path: /dev
            pathType: Prefix
            backend:
              service:
                name: canvas
                port:
                  number: 8002
    - host: kasten.gstoehl.dev
      http:
        paths:
          - path: /dev
            pathType: Prefix
            backend:
              service:
                name: kasten
                port:
                  number: 8003
    - host: balance.gstoehl.dev
      http:
        paths:
          - path: /dev
            pathType: Prefix
            backend:
              service:
                name: balance
                port:
                  number: 8000
```

**Step 4: Verify ingress syntax**

Run: `kubectl apply --dry-run=client -f k8s/dev/ingress.yaml`
Expected: No errors

**Step 5: Commit ingress updates**

```bash
git add k8s/dev/middleware-stripprefix.yaml k8s/dev/ingress.yaml
git commit -m "feat: add path-based routing ingress for dev environment"
```

---

## Task 5: Create GitHub Actions Deploy-Dev Workflow

**Goal:** Automate build, deploy, and test on push to `dev` branch

**Files:**
- Create: `.github/workflows/deploy-dev.yml`
- Reference: `docs/plans/2026-01-10-e2e-testing-devprod-workflow-design.md` (workflow design)

**Step 1: Create workflow file**

Create `.github/workflows/deploy-dev.yml`:

```yaml
name: Deploy to Dev & Run E2E Tests

on:
  push:
    branches:
      - dev

env:
  REGISTRY: ghcr.io
  # TODO: Replace USERNAME with actual GitHub username
  IMAGE_PREFIX: ghcr.io/USERNAME

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      balance: ${{ steps.changes.outputs.balance }}
      bookmark-manager: ${{ steps.changes.outputs.bookmark-manager }}
      canvas: ${{ steps.changes.outputs.canvas }}
      kasten: ${{ steps.changes.outputs.kasten }}
      shared: ${{ steps.changes.outputs.shared }}
    steps:
      - uses: actions/checkout@v4
      
      - uses: dorny/paths-filter@v2
        id: changes
        with:
          filters: |
            balance:
              - 'balance/**'
            bookmark-manager:
              - 'bookmark-manager/**'
            canvas:
              - 'canvas/**'
            kasten:
              - 'kasten/**'
            shared:
              - 'shared/**'

  build-and-push:
    needs: detect-changes
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    strategy:
      matrix:
        service: [balance, bookmark-manager, canvas, kasten]
    steps:
      - uses: actions/checkout@v4
      
      - name: Check if build needed
        id: should-build
        run: |
          if [ "${{ needs.detect-changes.outputs.shared }}" == "true" ]; then
            echo "build=true" >> $GITHUB_OUTPUT
          elif [ "${{ needs.detect-changes.outputs[matrix.service] }}" == "true" ]; then
            echo "build=true" >> $GITHUB_OUTPUT
          else
            echo "build=false" >> $GITHUB_OUTPUT
          fi
      
      - name: Log in to GHCR
        if: steps.should-build.outputs.build == 'true'
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push image
        if: steps.should-build.outputs.build == 'true'
        working-directory: ${{ matrix.service }}
        run: |
          docker build -t ${{ env.IMAGE_PREFIX }}/${{ matrix.service }}:dev .
          docker push ${{ env.IMAGE_PREFIX }}/${{ matrix.service }}:dev

  deploy-to-dev:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up kubectl
        uses: azure/k8s-set-context@v3
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBECONFIG }}
      
      - name: Deploy to dev namespace
        run: |
          kubectl apply -f k8s/dev/
      
      - name: Restart deployments
        run: |
          kubectl rollout restart deployment/balance -n knowledge-system-dev
          kubectl rollout restart deployment/bookmark-manager -n knowledge-system-dev
          kubectl rollout restart deployment/canvas -n knowledge-system-dev
          kubectl rollout restart deployment/kasten -n knowledge-system-dev
      
      - name: Wait for pods ready
        run: |
          kubectl wait --for=condition=ready pod -l app=balance -n knowledge-system-dev --timeout=5m
          kubectl wait --for=condition=ready pod -l app=bookmark-manager -n knowledge-system-dev --timeout=5m
          kubectl wait --for=condition=ready pod -l app=canvas -n knowledge-system-dev --timeout=5m
          kubectl wait --for=condition=ready pod -l app=kasten -n knowledge-system-dev --timeout=5m

  reset-dev-databases:
    needs: deploy-to-dev
    runs-on: ubuntu-latest
    steps:
      - name: Set up kubectl
        uses: azure/k8s-set-context@v3
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBECONFIG }}
      
      - name: Reset databases
        run: |
          kubectl exec -n knowledge-system-dev deployment/balance -- sh -c "rm -f /app/data/*.db || true"
          kubectl exec -n knowledge-system-dev deployment/bookmark-manager -- sh -c "rm -f /app/data/*.db || true"
          kubectl exec -n knowledge-system-dev deployment/canvas -- sh -c "rm -f /app/data/*.db || true"
          kubectl exec -n knowledge-system-dev deployment/kasten -- sh -c "rm -f /app/data/*.db || true"
      
      - name: Wait for pods to restart
        run: |
          sleep 10
          kubectl wait --for=condition=ready pod -l app=balance -n knowledge-system-dev --timeout=2m
          kubectl wait --for=condition=ready pod -l app=bookmark-manager -n knowledge-system-dev --timeout=2m
          kubectl wait --for=condition=ready pod -l app=canvas -n knowledge-system-dev --timeout=2m
          kubectl wait --for=condition=ready pod -l app=kasten -n knowledge-system-dev --timeout=2m

  run-api-tests:
    needs: reset-dev-databases
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install test dependencies
        run: |
          pip install -r tests/requirements-test.txt
      
      - name: Run API tests
        run: |
          pytest tests/e2e/api/ -v --base-url=https://bookmark.gstoehl.dev/dev

  run-ui-tests:
    needs: run-api-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install test dependencies
        run: |
          pip install -r tests/requirements-test.txt
          playwright install chromium
      
      - name: Run Playwright tests
        run: |
          playwright test tests/e2e/ui/
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/

  create-pr:
    needs: run-ui-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Create PR to main
        run: |
          gh pr create --base main --head dev \
            --title "Deploy to prod (tests passed)" \
            --body "All smoke tests passed in dev environment. Ready for production deployment." \
            || echo "PR already exists"
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Step 2: Verify workflow syntax**

Run: `cat .github/workflows/deploy-dev.yml | head -20`
Expected: Valid YAML, no syntax errors

**Step 3: Commit workflow**

```bash
git add .github/workflows/deploy-dev.yml
git commit -m "feat: add GitHub Actions deploy-dev workflow"
```

---

## Task 6: Create GitHub Actions Deploy-Prod Workflow

**Goal:** Deploy to production on merge to main

**Files:**
- Create: `.github/workflows/deploy-prod.yml`

**Step 1: Create workflow file**

Create `.github/workflows/deploy-prod.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches:
      - main

env:
  REGISTRY: ghcr.io
  # TODO: Replace USERNAME with actual GitHub username
  IMAGE_PREFIX: ghcr.io/USERNAME

jobs:
  retag-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    strategy:
      matrix:
        service: [balance, bookmark-manager, canvas, kasten]
    steps:
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Re-tag dev as latest
        run: |
          docker pull ${{ env.IMAGE_PREFIX }}/${{ matrix.service }}:dev
          docker tag ${{ env.IMAGE_PREFIX }}/${{ matrix.service }}:dev ${{ env.IMAGE_PREFIX }}/${{ matrix.service }}:latest
          docker push ${{ env.IMAGE_PREFIX }}/${{ matrix.service }}:latest

  deploy-to-prod:
    needs: retag-and-push
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up kubectl
        uses: azure/k8s-set-context@v3
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBECONFIG }}
      
      - name: Deploy to prod namespace
        run: |
          kubectl apply -f k8s/base/
      
      - name: Restart deployments
        run: |
          kubectl rollout restart deployment/balance -n knowledge-system
          kubectl rollout restart deployment/bookmark-manager -n knowledge-system
          kubectl rollout restart deployment/canvas -n knowledge-system
          kubectl rollout restart deployment/kasten -n knowledge-system
      
      - name: Wait for pods ready
        run: |
          kubectl wait --for=condition=ready pod -l app=balance -n knowledge-system --timeout=5m
          kubectl wait --for=condition=ready pod -l app=bookmark-manager -n knowledge-system --timeout=5m
          kubectl wait --for=condition=ready pod -l app=canvas -n knowledge-system --timeout=5m
          kubectl wait --for=condition=ready pod -l app=kasten -n knowledge-system --timeout=5m
```

**Step 2: Commit workflow**

```bash
git add .github/workflows/deploy-prod.yml
git commit -m "feat: add GitHub Actions deploy-prod workflow"
```

---

## Task 7: Create Test Infrastructure

**Goal:** Set up pytest + Playwright test structure

**Files:**
- Create: `tests/e2e/api/__init__.py`
- Create: `tests/e2e/ui/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/requirements-test.txt`
- Create: `playwright.config.ts`

**Step 1: Create directory structure**

Run:
```bash
mkdir -p tests/e2e/api tests/e2e/ui
touch tests/e2e/__init__.py tests/e2e/api/__init__.py tests/e2e/ui/__init__.py
```

**Step 2: Create test requirements**

Create `tests/requirements-test.txt`:

```txt
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
playwright==1.40.0
pytest-playwright==0.4.3
```

**Step 3: Create pytest configuration**

Create `tests/conftest.py`:

```python
import pytest
import os

@pytest.fixture(scope="session")
def base_url():
    """Base URL for E2E tests (defaults to dev environment)."""
    return os.getenv("BASE_URL", "https://bookmark.gstoehl.dev/dev")

@pytest.fixture(scope="session")
def bookmark_url(base_url):
    """Bookmark manager service URL."""
    # Dev: https://bookmark.gstoehl.dev/dev
    # Prod: https://bookmark.gstoehl.dev
    return base_url.replace("bookmark.gstoehl.dev", "bookmark.gstoehl.dev")

@pytest.fixture(scope="session")
def canvas_url(base_url):
    """Canvas service URL."""
    return base_url.replace("bookmark.gstoehl.dev", "canvas.gstoehl.dev")

@pytest.fixture(scope="session")
def kasten_url(base_url):
    """Kasten service URL."""
    return base_url.replace("bookmark.gstoehl.dev", "kasten.gstoehl.dev")

@pytest.fixture(scope="session")
def balance_url(base_url):
    """Balance service URL."""
    return base_url.replace("bookmark.gstoehl.dev", "balance.gstoehl.dev")
```

**Step 4: Create Playwright configuration**

Create `playwright.config.ts`:

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e/ui',
  fullyParallel: false,  // Run tests sequentially (they modify shared state)
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,  // Single worker to avoid race conditions
  reporter: 'html',
  use: {
    baseURL: process.env.BASE_URL || 'https://bookmark.gstoehl.dev/dev',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
```

**Step 5: Install test dependencies locally**

Run:
```bash
pip install -r tests/requirements-test.txt
playwright install chromium
```

Expected: Dependencies installed successfully

**Step 6: Commit test infrastructure**

```bash
git add tests/ playwright.config.ts
git commit -m "feat: add E2E test infrastructure (pytest + Playwright)"
```

---

## Task 8: Write Balance API Tests

**Goal:** Create API smoke tests for Balance service

**Files:**
- Create: `tests/e2e/api/test_balance.py`
- Reference: `balance/tests/test_sessions.py` (existing unit tests for patterns)

**Step 1: Write Balance API test skeleton**

Create `tests/e2e/api/test_balance.py`:

```python
"""Balance service API smoke tests."""
import pytest
import httpx


@pytest.mark.asyncio
async def test_health_check(balance_url):
    """Verify Balance service is healthy."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{balance_url}/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_timer_complete_idempotency(balance_url):
    """Verify timer-complete doesn't reset active break (bug fix validation)."""
    async with httpx.AsyncClient() as client:
        # Start a session
        response = await client.post(
            f"{balance_url}/api/sessions/start",
            json={"activity_type": "coding", "priority_id": 1}
        )
        assert response.status_code == 200
        
        # Complete timer (creates break)
        response = await client.post(f"{balance_url}/api/sessions/timer-complete")
        assert response.status_code == 200
        data = response.json()
        first_break_until = data.get("break_until")
        assert first_break_until is not None
        
        # Call timer-complete again (should NOT extend break)
        response = await client.post(f"{balance_url}/api/sessions/timer-complete")
        assert response.status_code == 200
        data = response.json()
        second_break_until = data.get("break_until")
        
        # Bug fix: break_until should NOT change
        assert second_break_until == first_break_until


@pytest.mark.asyncio
async def test_log_meditation(balance_url):
    """Verify meditation logging works."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{balance_url}/api/logging/meditation",
            json={"duration_minutes": 10}
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_log_exercise(balance_url):
    """Verify exercise logging works."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{balance_url}/api/logging/exercise",
            json={"duration_minutes": 30, "activity": "running"}
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_stats(balance_url):
    """Verify stats endpoint returns data."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{balance_url}/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_sessions" in data
```

**Step 2: Run Balance API tests locally**

Run: `pytest tests/e2e/api/test_balance.py -v --base-url=http://localhost:8005`
Expected: Tests pass against local Balance instance

**Step 3: Commit Balance API tests**

```bash
git add tests/e2e/api/test_balance.py
git commit -m "test: add Balance API smoke tests (5 scenarios)"
```

---

## Task 9: Write Bookmark Manager API Tests

**Goal:** Create API smoke tests for bookmark-manager service

**Files:**
- Create: `tests/e2e/api/test_bookmark_manager.py`

**Step 1: Write bookmark-manager API tests**

Create `tests/e2e/api/test_bookmark_manager.py`:

```python
"""Bookmark Manager service API smoke tests."""
import pytest
import httpx


@pytest.mark.asyncio
async def test_health_check(bookmark_url):
    """Verify bookmark-manager service is healthy."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{bookmark_url}/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_create_and_retrieve_bookmark(bookmark_url):
    """Verify bookmark creation and retrieval."""
    async with httpx.AsyncClient() as client:
        # Create bookmark
        response = await client.post(
            f"{bookmark_url}/api/bookmarks",
            json={"url": "https://example.com", "title": "Example"}
        )
        assert response.status_code == 200
        bookmark_id = response.json()["id"]
        
        # Retrieve bookmark
        response = await client.get(f"{bookmark_url}/api/bookmarks/{bookmark_id}")
        assert response.status_code == 200
        assert response.json()["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_list_bookmarks(bookmark_url):
    """Verify bookmark listing works."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{bookmark_url}/api/bookmarks")
        assert response.status_code == 200
        data = response.json()
        assert "bookmarks" in data


@pytest.mark.asyncio
async def test_rss_feeds(bookmark_url):
    """Verify RSS feeds endpoint works."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{bookmark_url}/api/feeds")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
```

**Step 2: Run bookmark-manager API tests locally**

Run: `pytest tests/e2e/api/test_bookmark_manager.py -v --base-url=http://localhost:8001`
Expected: Tests pass

**Step 3: Commit bookmark-manager API tests**

```bash
git add tests/e2e/api/test_bookmark_manager.py
git commit -m "test: add bookmark-manager API smoke tests"
```

---

## Task 10: Write Canvas and Kasten API Tests

**Goal:** Create API smoke tests for canvas and kasten services

**Files:**
- Create: `tests/e2e/api/test_canvas.py`
- Create: `tests/e2e/api/test_kasten.py`

**Step 1: Write canvas API tests**

Create `tests/e2e/api/test_canvas.py`:

```python
"""Canvas service API smoke tests."""
import pytest
import httpx


@pytest.mark.asyncio
async def test_health_check(canvas_url):
    """Verify canvas service is healthy."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{canvas_url}/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_draft(canvas_url):
    """Verify draft creation works."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{canvas_url}/api/drafts",
            json={"title": "Test Draft", "content": "Test content"}
        )
        assert response.status_code == 200
        assert "id" in response.json()


@pytest.mark.asyncio
async def test_list_drafts(canvas_url):
    """Verify draft listing works."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{canvas_url}/api/drafts")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
```

**Step 2: Write kasten API tests**

Create `tests/e2e/api/test_kasten.py`:

```python
"""Kasten service API smoke tests."""
import pytest
import httpx


@pytest.mark.asyncio
async def test_health_check(kasten_url):
    """Verify kasten service is healthy."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{kasten_url}/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_notes(kasten_url):
    """Verify note listing works."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{kasten_url}/api/notes")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
```

**Step 3: Commit canvas and kasten API tests**

```bash
git add tests/e2e/api/test_canvas.py tests/e2e/api/test_kasten.py
git commit -m "test: add canvas and kasten API smoke tests"
```

---

## Task 11: Write Balance UI Tests (Playwright)

**Goal:** Create Playwright UI tests for Balance (7 scenarios)

**Files:**
- Create: `tests/e2e/ui/test_balance.py`

**Step 1: Write Balance UI test skeleton**

Create `tests/e2e/ui/test_balance.py`:

```python
"""Balance service UI smoke tests (Playwright)."""
import pytest
from playwright.sync_api import Page, expect


def test_break_timer_idempotency(page: Page):
    """
    Verify break timer doesn't reset on page reload (bug fix validation).
    
    Steps:
    1. Start a coding session
    2. Complete timer (creates break)
    3. Reload page
    4. Verify break timer hasn't reset (still counting down)
    """
    page.goto("/")
    
    # Start coding session
    page.click("text=Start Session")
    page.select_option("select#activity-type", "coding")
    page.click("button:has-text('Start')")
    
    # Wait for timer to appear
    expect(page.locator("#timer")).to_be_visible()
    
    # Complete timer (fast-forward in dev: click "Complete" button if exists)
    # OR wait for timer to complete naturally (slower)
    # For smoke test: use API to force completion
    page.evaluate("""
        fetch('/api/sessions/timer-complete', { method: 'POST' })
    """)
    
    # Wait for break screen
    expect(page.locator("text=Break Time")).to_be_visible(timeout=5000)
    
    # Get initial break time
    initial_break_text = page.locator("#break-timer").inner_text()
    
    # Reload page
    page.reload()
    
    # Verify break screen still shows
    expect(page.locator("text=Break Time")).to_be_visible()
    
    # Verify break timer hasn't reset (should be same or decreased, not increased)
    current_break_text = page.locator("#break-timer").inner_text()
    # Parse minutes (e.g., "5:00" -> 5)
    initial_minutes = int(initial_break_text.split(":")[0])
    current_minutes = int(current_break_text.split(":")[0])
    assert current_minutes <= initial_minutes, "Break timer reset (bug not fixed!)"


def test_log_meditation(page: Page):
    """Verify meditation logging flow."""
    page.goto("/")
    page.click("text=Log Activity")
    page.click("text=Meditation")
    page.fill("input#duration", "10")
    page.click("button:has-text('Log')")
    expect(page.locator("text=Meditation logged")).to_be_visible()


def test_log_exercise(page: Page):
    """Verify exercise logging flow."""
    page.goto("/")
    page.click("text=Log Activity")
    page.click("text=Exercise")
    page.fill("input#duration", "30")
    page.fill("input#activity", "running")
    page.click("button:has-text('Log')")
    expect(page.locator("text=Exercise logged")).to_be_visible()


def test_change_settings(page: Page):
    """Verify settings can be changed."""
    page.goto("/settings")
    page.fill("input#pomodoro-duration", "25")
    page.click("button:has-text('Save')")
    expect(page.locator("text=Settings saved")).to_be_visible()


def test_view_stats(page: Page):
    """Verify stats page loads and shows data."""
    page.goto("/stats")
    expect(page.locator("text=Statistics")).to_be_visible()
    expect(page.locator("text=Total Sessions")).to_be_visible()


def test_start_pomodoro_session(page: Page):
    """Verify Pomodoro session can be started."""
    page.goto("/")
    page.click("text=Start Session")
    page.select_option("select#activity-type", "coding")
    page.click("button:has-text('Start')")
    expect(page.locator("#timer")).to_be_visible()
    expect(page.locator("text=Coding")).to_be_visible()


def test_abandon_pomodoro_session(page: Page):
    """Verify Pomodoro session can be abandoned."""
    page.goto("/")
    page.click("text=Start Session")
    page.select_option("select#activity-type", "coding")
    page.click("button:has-text('Start')")
    expect(page.locator("#timer")).to_be_visible()
    
    page.click("button:has-text('Abandon')")
    expect(page.locator("text=Session abandoned")).to_be_visible()
    expect(page.locator("#timer")).not_to_be_visible()
```

**Step 2: Run Balance UI tests locally (dry run)**

Run: `playwright test tests/e2e/ui/test_balance.py --headed`
Expected: Tests run against local dev environment (may fail due to missing UI elements - will fix after inspecting actual UI)

**Step 3: Commit Balance UI tests**

```bash
git add tests/e2e/ui/test_balance.py
git commit -m "test: add Balance UI smoke tests (7 scenarios, Playwright)"
```

---

## Task 12: Write Bookmark Manager UI Tests

**Goal:** Create Playwright UI tests for bookmark-manager (7 scenarios)

**Files:**
- Create: `tests/e2e/ui/test_bookmark_manager.py`

**Step 1: Write bookmark-manager UI tests**

Create `tests/e2e/ui/test_bookmark_manager.py`:

```python
"""Bookmark Manager service UI smoke tests (Playwright)."""
import pytest
from playwright.sync_api import Page, expect


def test_move_bookmark(page: Page):
    """Verify bookmark can be moved between categories."""
    page.goto("/")
    
    # Create a bookmark first
    page.click("text=Add Bookmark")
    page.fill("input#url", "https://example.com")
    page.click("button:has-text('Save')")
    
    # Move to different category
    page.click("button:has-text('Move')")
    page.select_option("select#category", "archive")
    page.click("button:has-text('Move')")
    
    expect(page.locator("text=Bookmark moved")).to_be_visible()


def test_show_rss_feeds(page: Page):
    """Verify RSS feeds page loads."""
    page.goto("/feeds")
    expect(page.locator("text=RSS Feeds")).to_be_visible()


def test_add_rss_feed(page: Page):
    """Verify RSS feed can be added."""
    page.goto("/feeds")
    page.click("text=Add Feed")
    page.fill("input#feed-url", "https://example.com/rss")
    page.click("button:has-text('Subscribe')")
    expect(page.locator("text=Feed added")).to_be_visible()


def test_delete_item_in_all_overview(page: Page):
    """Verify item can be deleted from 'all' view."""
    page.goto("/all")
    page.click("button:has-text('Delete'):first")
    page.click("button:has-text('Confirm')")
    expect(page.locator("text=Bookmark deleted")).to_be_visible()


def test_dismiss_rss_item(page: Page):
    """Verify RSS item can be dismissed."""
    page.goto("/feeds")
    page.click("button:has-text('Dismiss'):first")
    expect(page.locator("text=Item dismissed")).to_be_visible()


def test_delete_rss_subscription(page: Page):
    """Verify RSS subscription can be deleted."""
    page.goto("/feeds")
    page.click("button:has-text('Unsubscribe'):first")
    page.click("button:has-text('Confirm')")
    expect(page.locator("text=Subscription deleted")).to_be_visible()


def test_cite_text(page: Page):
    """Verify text can be cited from bookmark."""
    page.goto("/")
    page.click("a:has-text('Example'):first")  # Click first bookmark
    page.click("button:has-text('Cite')")
    page.fill("textarea#citation", "Important quote")
    page.click("button:has-text('Save Citation')")
    expect(page.locator("text=Citation saved")).to_be_visible()
```

**Step 2: Commit bookmark-manager UI tests**

```bash
git add tests/e2e/ui/test_bookmark_manager.py
git commit -m "test: add bookmark-manager UI smoke tests (7 scenarios)"
```

---

## Task 13: Write Canvas and Kasten UI Tests

**Goal:** Create Playwright UI tests for canvas (5 scenarios) and kasten (4 scenarios)

**Files:**
- Create: `tests/e2e/ui/test_canvas.py`
- Create: `tests/e2e/ui/test_kasten.py`

**Step 1: Write canvas UI tests**

Create `tests/e2e/ui/test_canvas.py`:

```python
"""Canvas service UI smoke tests (Playwright)."""
import pytest
from playwright.sync_api import Page, expect


def test_show_cited_text(page: Page):
    """Verify cited text appears in draft."""
    page.goto("/")
    # Assumes citation exists from bookmark-manager test
    expect(page.locator("text=Important quote")).to_be_visible()


def test_make_to_note(page: Page):
    """Verify draft can be converted to note."""
    page.goto("/")
    page.click("button:has-text('Make to Note')")
    page.fill("input#note-title", "My Note")
    page.click("button:has-text('Create Note')")
    expect(page.locator("text=Note created")).to_be_visible()


def test_add_note_to_workspace(page: Page):
    """Verify note can be added to workspace."""
    page.goto("/workspace")
    page.click("button:has-text('Add Note')")
    page.click("text=My Note:first")
    expect(page.locator("#workspace").locator("text=My Note")).to_be_visible()


def test_connect_notes_in_workspace(page: Page):
    """Verify two notes can be connected."""
    page.goto("/workspace")
    # Assumes two notes exist in workspace
    page.click("#note-1")  # Select first note
    page.keyboard.press("Control+L")  # Link command
    page.click("#note-2")  # Select second note
    expect(page.locator("line.connection")).to_be_visible()


def test_export_draft(page: Page):
    """Verify draft can be exported."""
    page.goto("/")
    page.click("button:has-text('Export')")
    page.click("text=Markdown")
    # Download starts
    expect(page.locator("text=Export started")).to_be_visible()
```

**Step 2: Write kasten UI tests**

Create `tests/e2e/ui/test_kasten.py`:

```python
"""Kasten service UI smoke tests (Playwright)."""
import pytest
from playwright.sync_api import Page, expect


def test_note_created_from_canvas(page: Page):
    """Verify note shows Canvas as source."""
    page.goto("/")
    page.click("text=My Note:first")
    expect(page.locator("text=Source: Canvas")).to_be_visible()


def test_navigate_notes(page: Page):
    """Verify navigation between notes via links."""
    page.goto("/")
    page.click("text=My Note:first")
    page.click("a.backlink:first")
    expect(page.locator("h1")).not_to_have_text("My Note")


def test_add_note_to_workspace(page: Page):
    """Verify note can be added to workspace."""
    page.goto("/")
    page.click("text=My Note:first")
    page.click("button:has-text('Add to Workspace')")
    page.goto("/workspace")
    expect(page.locator("text=My Note")).to_be_visible()


def test_workspace_shows_added_note(page: Page):
    """Verify workspace displays added note."""
    page.goto("/workspace")
    expect(page.locator("text=My Note")).to_be_visible()
```

**Step 3: Commit canvas and kasten UI tests**

```bash
git add tests/e2e/ui/test_canvas.py tests/e2e/ui/test_kasten.py
git commit -m "test: add canvas (5) and kasten (4) UI smoke tests"
```

---

## Task 14: Setup K8s Secrets and GHCR Authentication

**Goal:** Configure K8s secrets for GHCR and dev Balance NextDNS

**Prerequisites:**
- GitHub Personal Access Token with `write:packages` scope
- NextDNS API key (existing)

**Step 1: Create GHCR pull secret**

Run:
```bash
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USERNAME \
  --docker-password=YOUR_GITHUB_PAT \
  -n knowledge-system
```

Expected: `secret/ghcr-pull-secret created`

**Step 2: Create GHCR pull secret for dev namespace**

Run:
```bash
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USERNAME \
  --docker-password=YOUR_GITHUB_PAT \
  -n knowledge-system-dev
```

Expected: `secret/ghcr-pull-secret created`

**Step 3: Create balance-secrets-dev**

Run:
```bash
kubectl create secret generic balance-secrets-dev \
  --from-literal=nextdns-api-key=YOUR_NEXTDNS_API_KEY \
  --from-literal=nextdns-profile-id=c87dff \
  -n knowledge-system-dev
```

Expected: `secret/balance-secrets-dev created`

**Step 4: Verify secrets**

Run:
```bash
kubectl get secrets -n knowledge-system
kubectl get secrets -n knowledge-system-dev
```

Expected: Shows `ghcr-pull-secret` and `balance-secrets-dev`

**Step 5: Document secret creation**

Update `k8s/OPERATIONS.md` with secret creation commands (add new section "GHCR Setup")

**Step 6: Commit operations doc update**

```bash
git add k8s/OPERATIONS.md
git commit -m "docs: add GHCR secret setup to operations guide"
```

---

## Task 15: Configure GitHub Repository Secrets

**Goal:** Add required secrets to GitHub repository for Actions

**Prerequisites:**
- GitHub repository access
- Kubeconfig file for K3s cluster

**Step 1: Add KUBECONFIG secret**

1. Go to GitHub repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `KUBECONFIG`
4. Value: Contents of `~/.kube/config`
5. Click "Add secret"

**Step 2: Verify GITHUB_TOKEN permissions**

1. Go to Settings → Actions → General
2. Scroll to "Workflow permissions"
3. Select "Read and write permissions"
4. Check "Allow GitHub Actions to create and approve pull requests"
5. Click "Save"

**Step 3: Test secret access**

Create `.github/workflows/test-secrets.yml`:

```yaml
name: Test Secrets
on: workflow_dispatch
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Test kubectl access
        run: echo "${{ secrets.KUBECONFIG }}" | head -c 50
```

Run workflow manually, verify it accesses secret.

**Step 4: Delete test workflow**

```bash
rm .github/workflows/test-secrets.yml
git add .github/workflows/test-secrets.yml
git commit -m "chore: remove test secrets workflow"
```

---

## Task 16: Deploy Dev Namespace Manually (First Time)

**Goal:** Initial deployment of dev namespace before CI/CD is active

**Step 1: Apply dev namespace**

Run: `kubectl apply -f k8s/dev/namespace.yaml`
Expected: `namespace/knowledge-system-dev created`

**Step 2: Apply dev secrets** (already done in Task 14)

Verify: `kubectl get secrets -n knowledge-system-dev`

**Step 3: Build and push initial dev images**

For each service:
```bash
cd balance
docker build -t ghcr.io/YOUR_USERNAME/balance:dev .
docker push ghcr.io/YOUR_USERNAME/balance:dev
cd ..

cd bookmark-manager
docker build -t ghcr.io/YOUR_USERNAME/bookmark-manager:dev .
docker push ghcr.io/YOUR_USERNAME/bookmark-manager:dev
cd ..

cd canvas
docker build -t ghcr.io/YOUR_USERNAME/canvas:dev .
docker push ghcr.io/YOUR_USERNAME/canvas:dev
cd ..

cd kasten
docker build -t ghcr.io/YOUR_USERNAME/kasten:dev .
docker push ghcr.io/YOUR_USERNAME/kasten:dev
cd ..
```

Expected: Images pushed to GHCR

**Step 4: Apply dev manifests**

Run: `kubectl apply -f k8s/dev/`
Expected: Deployments, services, ingress created

**Step 5: Wait for pods ready**

Run: `kubectl get pods -n knowledge-system-dev -w`
Expected: All pods running

**Step 6: Test dev environment access**

Visit: `https://balance.gstoehl.dev/dev/health`
Expected: `{"status": "healthy"}`

**Step 7: Document first deploy**

No commit needed (manual deployment, not code change)

---

## Task 17: Enable Branch Protection on Main

**Goal:** Block direct pushes to main, require PR from dev

**Step 1: Configure branch protection**

1. Go to GitHub repo → Settings → Branches
2. Click "Add branch protection rule"
3. Branch name pattern: `main`
4. Check: "Require a pull request before merging"
5. Check: "Require status checks to pass before merging"
6. Click "Create"

**Step 2: Verify protection**

Try: `git push origin main` (should fail)
Expected: "protected branch hook declined"

**Step 3: Document branch protection**

Update `docs/plans/2026-01-10-e2e-testing-devprod-workflow-design.md` with confirmation that protection is enabled.

---

## Task 18: End-to-End Workflow Validation

**Goal:** Validate entire dev→prod pipeline works

**Step 1: Create test commit on dev branch**

```bash
git checkout dev
echo "# Test" > TEST.md
git add TEST.md
git commit -m "test: validate CI/CD pipeline"
git push origin dev
```

**Step 2: Monitor GitHub Actions**

1. Go to GitHub repo → Actions
2. Watch "Deploy to Dev & Run E2E Tests" workflow
3. Verify all jobs pass (build, deploy, API tests, UI tests, PR creation)

Expected: Workflow succeeds, PR auto-created

**Step 3: Review auto-created PR**

1. Go to Pull Requests tab
2. Find "Deploy to prod (tests passed)" PR
3. Review changes
4. Merge PR

**Step 4: Monitor prod deployment**

1. Watch "Deploy to Production" workflow
2. Verify pods restart in `knowledge-system` namespace
3. Check prod services are healthy

Run: `kubectl get pods -n knowledge-system`
Expected: All pods running

**Step 5: Verify prod services**

Visit: `https://balance.gstoehl.dev/health`
Expected: `{"status": "healthy"}`

**Step 6: Clean up test commit**

```bash
git checkout dev
git revert HEAD
git push origin dev
```

(Let CI run again, merge cleanup PR)

**Step 7: Document successful validation**

Update `docs/plans/2026-01-10-e2e-testing-devprod-workflow-design.md` with "Status: Deployed and Validated"

---

## Success Criteria Checklist

After completing all tasks, verify:

- [ ] Dev namespace deployed and accessible at `/dev` paths
- [ ] Prod namespace updated to pull from GHCR
- [ ] All services handle `BASE_PATH` environment variable
- [ ] GitHub Actions workflows run on push to dev/main
- [ ] API tests pass (pytest + httpx, ~30s runtime)
- [ ] UI tests pass (Playwright, ~5min runtime)
- [ ] Failed tests block PR creation
- [ ] Branch protection prevents direct main pushes
- [ ] Prod deployments re-tag images (no rebuild)
- [ ] K8s rollback works on failed deployment
- [ ] Balance break timer idempotency test validates bug fix

## Next Steps After Implementation

1. **Refine UI tests:** Update Playwright selectors based on actual UI structure
2. **Add more test scenarios:** Expand coverage as new features are added
3. **Monitor test flakiness:** Track and fix flaky tests
4. **Optimize build times:** Add caching to Docker builds in GitHub Actions
5. **Deploy Balance bug fix:** Push fix through new pipeline to production

## References

- Design doc: `docs/plans/2026-01-10-e2e-testing-devprod-workflow-design.md`
- K8s operations: `k8s/OPERATIONS.md`
- Balance bug fix: `balance/src/routers/sessions.py:249`
- Existing unit tests: `balance/tests/test_sessions.py`
