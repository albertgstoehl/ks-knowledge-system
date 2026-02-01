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
RUNALYZE_API_URL = "https://runalyze.com/api/v2"


async def fetch_runalyze_stats(client: httpx.AsyncClient, target_date: date) -> dict:
    """Fetch stats from Runalyze API."""
    if not RUNALYZE_TOKEN:
        raise ValueError("RUNALYZE_TOKEN environment variable required")
    
    headers = {"Authorization": f"Bearer {RUNALYZE_TOKEN}"}
    
    # For Supporter tier, we use /stats/current for today's data
    # For historical, we'd need different endpoints
    resp = await client.get(
        f"{RUNALYZE_API_URL}/stats/current",
        headers=headers
    )
    resp.raise_for_status()
    
    return resp.json()


def transform_to_train_format(stats: dict, target_date: date) -> dict:
    """Transform Runalyze stats to Train API format."""
    return {
        "date": target_date.isoformat(),
        "resting_hr": stats.get("resting_heart_rate"),
        "hrv_avg": stats.get("hrv", {}).get("last_night_avg"),
        "sleep_score": stats.get("sleep", {}).get("score"),
        "sleep_duration_hours": stats.get("sleep", {}).get("duration_hours"),
        "vo2max": stats.get("effective_vo2max"),
        "marathon_shape": stats.get("marathon_shape", {}).get("marathon"),
        "atl": stats.get("atl"),
        "ctl": stats.get("ctl"),
        "tsb": stats.get("ctl", 0) - stats.get("atl", 0) if stats.get("ctl") and stats.get("atl") else None,
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
        
        print(f"✓ Synced {target_date}: shape={payload['marathon_shape']}%, tsb={payload['tsb']}")
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
