#!/usr/bin/env python3
"""
Sync Runalyze data to Train database.

Usage:
    python sync_runalyze.py              # Sync today
    python sync_runalyze.py --days 7     # Sync last 7 days
    python sync_runalyze.py --backfill   # Backfill from Runalyze history
"""

import argparse
import asyncio
import os
import sys
from datetime import date, timedelta

import httpx

RUNALYZE_TOKEN = os.getenv("RUNALYZE_TOKEN")
TRAIN_API_URL = os.getenv("TRAIN_API_URL", "http://localhost:8000")
RUNALYZE_API_URL = "https://runalyze.com/api/v1"


async def fetch_runalyze_stats(client: httpx.AsyncClient, target_date: date) -> dict:
    """Fetch stats from Runalyze API."""
    if not RUNALYZE_TOKEN:
        raise ValueError("RUNALYZE_TOKEN environment variable required")
    
    headers = {"token": RUNALYZE_TOKEN}
    
    # Supporter/Premium tier: use /statistics/current for today's data
    resp = await client.get(
        f"{RUNALYZE_API_URL}/statistics/current",
        headers=headers
    )
    resp.raise_for_status()
    
    return resp.json()


def transform_to_train_format(stats: dict, target_date: date) -> dict:
    """Transform Runalyze stats to Train API format."""
    # Map Runalyze field names to our field names
    # fitness = CTL, fatigue = ATL, performance = TSB
    return {
        "date": target_date.isoformat(),
        # Health metrics - not available from this endpoint, would need Garmin
        "resting_hr": None,
        "hrv_avg": stats.get("hrvBaseline"),
        "sleep_score": None,
        "sleep_duration_hours": None,
        # Training metrics from Runalyze calculations
        "vo2max": stats.get("effectiveVO2max") if stats.get("effectiveVO2max") else None,
        "marathon_shape": stats.get("marathonShape") if stats.get("marathonShape") else None,
        "atl": stats.get("fatigue"),  # ATL = Acute Training Load (fatigue)
        "ctl": stats.get("fitness"),   # CTL = Chronic Training Load (fitness)
        "tsb": stats.get("performance"),  # TSB = Training Stress Balance (performance)
    }


async def sync_date(target_date: date, client: httpx.AsyncClient) -> bool:
    """Sync a single date to Train."""
    try:
        stats = await fetch_runalyze_stats(client, target_date)
        payload = transform_to_train_format(stats, target_date)
        
        resp = await client.post(
            f"{TRAIN_API_URL}/api/daily-metrics/sync",
            json=payload
        )
        resp.raise_for_status()
        
        shape = payload.get('marathon_shape')
        tsb = payload.get('tsb')
        vo2max = payload.get('vo2max')
        print(f"✓ Synced {target_date}: shape={shape}%, tsb={tsb}, vo2max={vo2max}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to sync {target_date}: {e}", file=sys.stderr)
        return False


async def main():
    parser = argparse.ArgumentParser(description="Sync Runalyze to Train")
    parser.add_argument("--days", type=int, default=1, help="Number of days to sync")
    parser.add_argument("--date", help="Specific date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    async with httpx.AsyncClient() as client:
        if args.date:
            target = date.fromisoformat(args.date)
            success = await sync_date(target, client)
            sys.exit(0 if success else 1)
        else:
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
