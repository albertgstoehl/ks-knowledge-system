#!/usr/bin/env python3
"""
Sync Garmin Connect data to Train database.

Usage:
    python sync_garmin.py              # Sync last 7 days
    python sync_garmin.py --days 14    # Sync last 14 days
    python sync_garmin.py --date 2026-01-31  # Sync specific date
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import init_db, async_session_maker
from src.models import RecoverySummary
from sqlalchemy import select


GARMIN_USERNAME = os.getenv("GARMIN_USERNAME")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
API_BASE_URL = os.getenv("TRAIN_API_URL", "http://localhost:8000")


def parse_garmin_daily_summary(data: dict) -> dict:
    """Extract relevant fields from Garmin daily summary."""
    return {
        "resting_hr": data.get("restingHeartRateInBeatsPerMinute"),
        "avg_stress": data.get("averageStressLevel"),
    }


def parse_garmin_sleep_summary(data: dict) -> dict:
    """Extract relevant fields from Garmin sleep summary."""
    duration_sec = data.get("durationInSeconds", 0)
    deep_sec = data.get("deepSleepDurationInSeconds", 0)
    
    return {
        "sleep_score": data.get("overallSleepScoreValue"),
        "sleep_duration_hours": duration_sec / 3600 if duration_sec else None,
        "deep_sleep_percent": (deep_sec / duration_sec * 100) if duration_sec else None,
    }


def parse_garmin_hrv_summary(data: dict) -> dict:
    """Extract relevant fields from Garmin HRV summary."""
    return {
        "hrv_avg": data.get("lastNightAvg"),
    }


async def sync_date(target_date: date, client: httpx.AsyncClient) -> bool:
    """Sync a single date's data from Garmin to Train API."""
    try:
        from garminconnect import Garmin
        
        if not GARMIN_USERNAME or not GARMIN_PASSWORD:
            print("Error: GARMIN_USERNAME and GARMIN_PASSWORD must be set")
            return False
        
        garmin = Garmin(GARMIN_USERNAME, GARMIN_PASSWORD)
        garmin.login()
        
        # Fetch data for date
        date_str = target_date.isoformat()
        
        # Get stats (includes resting HR, stress)
        stats = garmin.get_stats(date_str)
        
        # Get sleep data
        sleep_data = garmin.get_sleep_data(date_str)
        
        # Get HRV data
        hrv_data = garmin.get_hrv_data(date_str)
        
        # Merge all data
        payload = {"date": date_str}
        payload.update(parse_garmin_daily_summary(stats))
        payload.update(parse_garmin_sleep_summary(sleep_data))
        payload.update(parse_garmin_hrv_summary(hrv_data))
        
        # Send to Train API
        resp = await client.post(f"{API_BASE_URL}/api/recovery/sync", json=payload)
        resp.raise_for_status()
        
        print(f"✓ Synced {date_str}: readiness={resp.json()['readiness_score']}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to sync {target_date}: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Sync Garmin data to Train")
    parser.add_argument("--days", type=int, default=7, help="Number of days to sync")
    parser.add_argument("--date", help="Specific date to sync (YYYY-MM-DD)")
    args = parser.parse_args()
    
    async with httpx.AsyncClient() as client:
        if args.date:
            # Sync single date
            target = date.fromisoformat(args.date)
            success = await sync_date(target, client)
            sys.exit(0 if success else 1)
        else:
            # Sync range
            today = date.today()
            success_count = 0
            
            for i in range(args.days):
                target = today - timedelta(days=i)
                if await sync_date(target, client):
                    success_count += 1
            
            print(f"\nSynced {success_count}/{args.days} days")
            sys.exit(0 if success_count > 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
