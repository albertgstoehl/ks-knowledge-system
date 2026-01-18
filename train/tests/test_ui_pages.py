from fastapi.testclient import TestClient
from src.main import app


def test_today_page_renders():
    with TestClient(app) as client:
        response = client.get("/today")
        assert response.status_code == 200
        assert "Today" in response.text
