import os
import tempfile
from fastapi.testclient import TestClient
from src.main import app


def test_plan_register_and_fetch_current():
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["PLAN_DIR"] = tmp_dir
        with TestClient(app) as client:
            payload = {"title": "Plan A", "markdown": "# A", "carry_over_notes": ""}
            response = client.post("/api/plan/register", json=payload)
            assert response.status_code == 200

            current = client.get("/api/plan/current")
            assert current.status_code == 200
            assert current.json()["title"] == "Plan A"
