import pytest
from datetime import date
from src.models import DailyMetrics


def test_daily_metrics_creation():
    metrics = DailyMetrics(
        date=date(2026, 2, 1),
        resting_hr=48,
        hrv_avg=52,
        sleep_score=82,
        sleep_duration_hours=7.2,
        vo2max=40.2,
        marathon_shape=78.0,
        tsb=-12.0,
        atl=85.0,
        ctl=73.0,
        soreness=2,
        energy=7,
    )
    assert metrics.date == date(2026, 2, 1)
    assert metrics.marathon_shape == 78.0
    assert metrics.tsb == -12.0
