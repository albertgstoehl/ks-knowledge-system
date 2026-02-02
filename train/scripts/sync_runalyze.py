#!/usr/bin/env python3
"""
Sync Runalyze data to Train database.

Usage:
    python sync_runalyze.py              # Sync today
    python sync_runalyze.py --days 7     # Sync last 7 days
    python sync_runalyze.py --activities # Sync activities
"""

import argparse
import asyncio
import os
import sys
from datetime import date, timedelta
from datetime import datetime

import httpx

RUNALYZE_TOKEN = os.getenv("RUNALYZE_TOKEN")
TRAIN_API_URL = os.getenv("TRAIN_API_URL", "http://localhost:8000")
RUNALYZE_API_URL = "https://runalyze.com/api/v1"


async def fetch_runalyze_stats(client: httpx.AsyncClient, target_date: date) -> dict:
    """Fetch stats from Runalyze API."""
    if not RUNALYZE_TOKEN:
        raise ValueError("RUNALYZE_TOKEN environment variable required")
    
    headers = {"token": RUNALYZE_TOKEN}
    
    # Main training statistics (Supporter/Premium endpoint)
    resp = await client.get(
        f"{RUNALYZE_API_URL}/statistics/current",
        headers=headers
    )
    resp.raise_for_status()
    stats = resp.json()
    
    # Try to fetch HRV data if available
    try:
        hrv_resp = await client.get(
            f"{RUNALYZE_API_URL}/metrics/hrv?limit=1",
            headers=headers
        )
        if hrv_resp.status_code == 200:
            hrv_data = hrv_resp.json()
            if hrv_data and len(hrv_data) > 0:
                stats['latestHrv'] = hrv_data[0]
    except Exception:
        pass
    
    # Try to fetch sleep data if available
    try:
        sleep_resp = await client.get(
            f"{RUNALYZE_API_URL}/metrics/sleep?limit=1",
            headers=headers
        )
        if sleep_resp.status_code == 200:
            sleep_data = sleep_resp.json()
            if sleep_data and len(sleep_data) > 0:
                stats['latestSleep'] = sleep_data[0]
    except Exception:
        pass
    
    return stats


async def fetch_runalyze_activities(client: httpx.AsyncClient, days: int = 7) -> list:
    """Fetch running activities from Runalyze API."""
    if not RUNALYZE_TOKEN:
        raise ValueError("RUNALYZE_TOKEN environment variable required")
    
    headers = {"token": RUNALYZE_TOKEN}
    
    resp = await client.get(
        f"{RUNALYZE_API_URL}/activity",
        headers=headers,
        params={"limit": 50}  # Get last 50 activities
    )
    resp.raise_for_status()
    
    activities = resp.json()
    
    # Filter to running activities within date range
    cutoff = datetime.now() - timedelta(days=days)
    runs = []
    
    for act in activities:
        sport = act.get('sport', {}).get('name', '')
        if sport != 'Running':
            continue
        
        # Parse activity date
        act_date = datetime.fromisoformat(act['date_time'].replace('Z', '+00:00'))
        if act_date < cutoff:
            continue
        
        runs.append({
            'date': act_date.date().isoformat(),
            'distance_km': round(act.get('distance', 0), 2),
            'duration_minutes': int(act.get('duration', 0) / 60),
            'avg_hr': act.get('hr_avg'),
            'max_hr': act.get('hr_max'),
            'elevation_gain_m': act.get('elevation_up'),
            'notes': f"Synced from Runalyze: {act.get('title', 'Run')}",
            'source': 'garmin',
            'external_id': str(act.get('id'))
        })
    
    return runs


def transform_to_train_format(stats: dict, target_date: date) -> dict:
    """Transform Runalyze stats to Train API format."""
    # Extract latest HRV if available
    hrv_avg = None
    if 'latestHrv' in stats and stats['latestHrv']:
        hrv_avg = stats['latestHrv'].get('value') or stats['latestHrv'].get('hrv')
    
    # If no HRV in metrics, use hrvBaseline from statistics
    if hrv_avg is None:
        hrv_avg = stats.get('hrvBaseline')
    
    # Extract sleep data if available
    sleep_score = None
    sleep_duration = None
    if 'latestSleep' in stats and stats['latestSleep']:
        sleep_score = stats['latestSleep'].get('quality') or stats['latestSleep'].get('score')
        sleep_duration = stats['latestSleep'].get('duration') or stats['latestSleep'].get('totalTime')
        if sleep_duration:
            # Convert to hours if in minutes
            if sleep_duration > 20:  # Assume minutes if > 20
                sleep_duration = round(sleep_duration / 60, 2)
    
    # Map Runalyze fields to Train fields
    # fitness = CTL, fatigue = ATL, performance = TSB
    return {
        "date": target_date.isoformat(),
        # Health metrics (from Garmin via Runalyze if synced)
        "resting_hr": None,  # Not available via API currently
        "hrv_avg": hrv_avg,
        "sleep_score": sleep_score,
        "sleep_duration_hours": sleep_duration,
        # Training metrics from Runalyze calculations
        "vo2max": stats.get("effectiveVO2max") if stats.get("effectiveVO2max") else None,
        "marathon_shape": stats.get("marathonShape") if stats.get("marathonShape") else None,
        "atl": stats.get("fatigue"),  # ATL = Acute Training Load (fatigue)
        "ctl": stats.get("fitness"),   # CTL = Chronic Training Load (fitness)
        "tsb": stats.get("performance"),  # TSB = Training Stress Balance (performance)
    }


async def sync_activities(client: httpx.AsyncClient) -> int:
    """Sync running activities from Runalyze to Train."""
    runs = await fetch_runalyze_activities(client, days=7)
    
    if not runs:
        print("No running activities found in last 7 days")
        return 0
    
    synced = 0
    for run in runs:
        try:
            # Check if already exists
            check_resp = await client.get(
                f"{TRAIN_API_URL}/api/runs",
                params={"date": run['date']}
            )
            
            # Create the run
            resp = await client.post(
                f"{TRAIN_API_URL}/api/runs",
                json=run
            )
            
            if resp.status_code in [200, 201]:
                print(f"✓ Synced run: {run['date']} - {run['distance_km']}km in {run['duration_minutes']}min")
                synced += 1
            elif resp.status_code == 409:
                print(f"→ Already exists: {run['date']}")
            else:
                print(f"✗ Failed to sync {run['date']}: HTTP {resp.status_code}")
                
        except Exception as e:
            print(f"✗ Error syncing {run['date']}: {e}", file=sys.stderr)
    
    return synced


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
        hrv = payload.get('hrv_avg')
        
        parts = []
        if vo2max: parts.append(f"vo2max={vo2max}")
        if shape: parts.append(f"shape={shape}%")
        if tsb is not None: parts.append(f"tsb={tsb}")
        if hrv: parts.append(f"hrv={hrv}")
        
        status = ", ".join(parts) if parts else "no training data (sync Garmin to Runalyze)"
        print(f"✓ Synced {target_date}: {status}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to sync {target_date}: {e}", file=sys.stderr)
        return False


async def main():
    parser = argparse.ArgumentParser(description="Sync Runalyze to Train")
    parser.add_argument("--days", type=int, default=1, help="Number of days to sync")
    parser.add_argument("--date", help="Specific date (YYYY-MM-DD)")
    parser.add_argument("--activities", action="store_true", help="Sync activities/runs")
    args = parser.parse_args()
    
    async with httpx.AsyncClient() as client:
        if args.activities:
            print("Syncing activities from Runalyze...")
            synced = await sync_activities(client)
            print(f"\nSynced {synced} activities")
            sys.exit(0 if synced >= 0 else 1)
        elif args.date:
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
