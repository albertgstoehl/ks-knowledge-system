import pytest
from datetime import date
from src.models import RecoverySummary


def test_recovery_summary_creation():
    summary = RecoverySummary(
        date=date(2026, 1, 31),
        resting_hr=48,
        hrv_avg=52,
        sleep_score=82,
        sleep_duration_hours=7.2,
        deep_sleep_percent=18.5,
        avg_stress=22,
        weekly_mileage=18.5,
        readiness_score=78,
        soreness=2,
        energy=7,
    )
    assert summary.date == date(2026, 1, 31)
    assert summary.readiness_score == 78
