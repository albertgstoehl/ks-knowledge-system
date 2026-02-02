import pytest
from datetime import date


@pytest.mark.asyncio
async def test_log_manual_run(client):
    payload = {
        "date": "2026-01-31",
        "distance_km": 5.0,
        "duration_minutes": 32,
        "effort": 4,
        "notes": "Felt good, kept it easy",
    }
    resp = await client.post("/api/runs", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["distance_km"] == 5.0
    assert data["pace_per_km"] == "6:24"
