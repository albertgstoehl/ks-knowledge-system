from fastapi.testclient import TestClient
from src.main import app


def test_start_and_end_session():
    with TestClient(app) as client:
        response = client.post("/api/sessions/start", json={"template_key": "A"})
        assert response.status_code == 200
        session_id = response.json()["id"]

        end = client.post("/api/sessions/end", json={"session_id": session_id, "notes": "done"})
        assert end.status_code == 200
        assert end.json()["ended_at"] is not None
