import pytest
from datetime import date


@pytest.mark.asyncio
async def test_sync_daily_metrics(client):
    payload = {
        "date": "2026-02-01",
        "resting_hr": 48,
        "hrv_avg": 52,
        "sleep_score": 82,
        "sleep_duration_hours": 7.2,
        "vo2max": 40.2,
        "marathon_shape": 78.0,
        "tsb": -12.0,
        "atl": 85.0,
        "ctl": 73.0,
    }
    resp = await client.post("/api/daily-metrics/sync", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "synced"
    assert data["date"] == "2026-02-01"
