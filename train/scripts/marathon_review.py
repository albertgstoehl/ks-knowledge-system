#!/usr/bin/env python3
"""
Interactive weekly review for marathon training.

Usage:
    python marathon_review.py
"""

import asyncio
import httpx
from datetime import date

API_BASE = "http://localhost:8000"


async def main():
    async with httpx.AsyncClient() as client:
        # Fetch review data
        resp = await client.get(f"{API_BASE}/api/marathon/review")
        data = resp.json()
        
        print("=" * 50)
        print(f"WEEK {data['week_number']} REVIEW")
        print("=" * 50)
        print()
        
        # 1. Weekly Load
        print("1. WEEKLY LOAD")
        print(f"   Target: {data['target_miles']} km")
        actual = input(f"   Actual (default: {data['actual_miles']}): ") or data['actual_miles']
        actual = float(actual)
        print(f"   Long run: {'✓' if data['long_run_completed'] else '✗'} ({data['long_run_distance']}km)")
        print()
        
        # 2. Recovery Check
        print("2. RECOVERY METRICS")
        print(f"   Avg readiness: {data['avg_readiness']}/100")
        print(f"   Avg sleep: {data['avg_sleep']}/100")
        print(f"   HRV trend: {data['hrv_trend']}")
        print()
        
        # 3. Subjective
        print("3. HOW DID THIS WEEK FEEL?")
        print("   [1] Easier than expected")
        print("   [2] About right")
        print("   [3] Harder than expected")
        print("   [4] Something hurts")
        feel = input("   Choice: ")
        print()
        
        # 4. Calculate adjustments
        target_next = data['target_miles']
        
        if feel == "4":
            target_next = data['target_miles'] * 0.8
            print("⚠️  Reducing volume 20% due to pain/soreness")
        elif feel == "3":
            target_next = data['target_miles']
            print("→ Holding steady - week was hard enough")
        elif data['avg_readiness'] > 75 and actual >= data['target_miles'] * 0.9:
            target_next = data['target_miles'] * 1.1
            print(f"→ Progressing: {target_next:.1f} km (+10%)")
        else:
            print(f"→ Holding: {target_next:.1f} km")
        
        long_run_next = min(data['long_run_distance'] + 2, 25)
        
        print()
        print("4. NEXT WEEK TARGETS")
        print(f"   Mileage: {target_next:.1f} km")
        print(f"   Long run: {long_run_next:.0f} km")
        
        confirm = input("\nGenerate plan? [Y/n]: ").lower()
        if confirm != 'n':
            payload = {
                "target_miles": round(target_next, 1),
                "long_run_distance": long_run_next,
                "easy_pace_range": "6:15-6:30",
                "notes": f"Week felt: {['easier', 'about right', 'harder', 'pain'][int(feel)-1] if feel in '1234' else 'unknown'}"
            }
            
            resp = await client.post(f"{API_BASE}/api/marathon/plan/next", json=payload)
            result = resp.json()
            
            print(f"\n✓ Plan saved: {result['filename']}")


if __name__ == "__main__":
    asyncio.run(main())
