import pytest
from datetime import date


@pytest.mark.asyncio
async def test_sync_recovery_data(client):
    payload = {
        "date": "2026-01-31",
        "resting_hr": 48,
        "hrv_avg": 52,
        "sleep_score": 82,
        "sleep_duration_hours": 7.2,
        "deep_sleep_percent": 18.5,
        "avg_stress": 22,
    }
    resp = await client.post("/api/recovery/sync", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["date"] == "2026-01-31"
    assert data["readiness"]["verdict"] in ["GREEN", "YELLOW", "RED"]
    assert data["readiness"]["guidance"] != ""
    assert len(data["readiness"]["metrics"]) > 0
