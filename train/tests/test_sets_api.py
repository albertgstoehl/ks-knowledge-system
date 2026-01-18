from fastapi.testclient import TestClient
from src.main import app


def test_add_set_and_fetch_recent():
    with TestClient(app) as client:
        session = client.post("/api/sessions/start", json={"template_key": "A"}).json()
        response = client.post("/api/sets", json={
            "session_id": session["id"],
            "exercise_name": "Bench",
            "weight": 100,
            "reps": 8,
            "rir": 2,
        })
        assert response.status_code == 200

        recent = client.get("/api/sets/recent")
        assert recent.status_code == 200
        assert recent.json()[0]["exercise_name"] == "Bench"
