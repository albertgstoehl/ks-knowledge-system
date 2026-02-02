#!/usr/bin/env python3
"""
Marathon Coach Analysis Tool
Scientific analysis of athlete data from Runalyze API

Usage:
    python marathon_coach_analysis.py [--days 14] [--athlete-age 23]

References:
    - Banister EW (1991): Modeling elite athletic performance
    - Foster C (2001): Monitoring training in athletes with reference to overtraining syndrome
    - Seiler S (2010): What is best practice for training intensity distribution?
    - Sandbakk Ø (2021): The physiological and biomechanical basis of running economy
"""

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

import httpx

RUNALYZE_TOKEN = os.getenv("RUNALYZE_TOKEN")
RUNALYZE_API_URL = "https://runalyze.com/api/v1"

# Scientific Constants
MAX_HR_ESTIMATE_AGE = lambda age: 208 - (0.7 * age)  # Tanaka formula
HR_RESERVE = lambda max_hr, resting_hr: max_hr - resting_hr
KARVONEN = lambda max_hr, resting_hr, intensity: resting_hr + (HR_RESERVE(max_hr, resting_hr) * intensity)

# Training Zones (Karvonen %HRR)
ZONES = {
    'Z1_recovery': (0.50, 0.60),
    'Z2_aerobic': (0.60, 0.75),
    'Z2_extended': (0.60, 0.80),  # Extended aerobic for beginners
    'Z3_tempo': (0.75, 0.85),
    'Z4_threshold': (0.85, 0.92),
    'Z5_VO2max': (0.92, 1.00),
}

# Risk Thresholds
RISK_THRESHOLDS = {
    'ctl_minimal_fitness': 20,  # Below this is detrained
    'ctl_moderate_fitness': 40,  # Minimum for marathon finish
    'ctl_marathon_ready': 60,   # Comfortable marathon completion
    'tsb_severe_fatigue': -30,
    'tsb_moderate_fatigue': -15,
    'acwr_low': 0.80,
    'acwr_optimal_low': 0.80,
    'acwr_optimal_high': 1.30,
    'acwr_high': 1.50,
    'monotony_high': 2.0,
    'strain_high': 4000,
}


@dataclass
class AthleteProfile:
    """Athlete demographic and goal data."""
    age: int = 23
    goal_date: date = field(default_factory=lambda: date(2026, 4, 15))
    goal_distance: str = "marathon"
    experience_level: str = "beginner"  # beginner, intermediate, advanced
    max_hr: Optional[int] = None
    resting_hr: Optional[int] = None
    
    def estimated_max_hr(self) -> int:
        if self.max_hr:
            return self.max_hr
        return int(MAX_HR_ESTIMATE_AGE(self.age))
    
    def weeks_to_goal(self) -> int:
        return max(0, (self.goal_date - date.today()).days // 7)
    
    def training_zones(self) -> dict:
        """Calculate HR zones using Karvonen method."""
        max_hr = self.estimated_max_hr()
        resting = self.resting_hr or 50  # Assume 50 if unknown
        
        zones = {}
        for name, (low, high) in ZONES.items():
            zones[name] = (
                int(KARVONEN(max_hr, resting, low)),
                int(KARVONEN(max_hr, resting, high))
            )
        return zones


@dataclass
class RunalyzeStats:
    """Parsed Runalyze statistics."""
    # Training status
    vo2max: Optional[float] = None
    ctl: Optional[float] = None  # Chronic Training Load (fitness)
    atl: Optional[float] = None  # Acute Training Load (fatigue)
    tsb: Optional[float] = None  # Training Stress Balance (performance)
    acwr: Optional[float] = None  # Acute:Chronic Workload Ratio
    marathon_shape: Optional[float] = None
    hrv_baseline: Optional[float] = None
    rest_days_percent: Optional[float] = None
    training_strain: Optional[float] = None
    monotony: Optional[float] = None
    
    # Sleep data
    sleep_duration_min: Optional[int] = None
    sleep_quality_score: Optional[int] = None
    deep_sleep_percent: Optional[float] = None
    
    @classmethod
    def from_api_response(cls, data: dict) -> 'RunalyzeStats':
        """Parse Runalyze API response."""
        stats = cls()
        
        # Training metrics
        stats.vo2max = data.get('effectiveVO2max') or data.get('vo2max')
        stats.ctl = data.get('fitness')  # CTL
        stats.atl = data.get('fatigue')  # ATL
        stats.tsb = data.get('performance')  # TSB
        stats.acwr = data.get('acuteChronicWorkloadRatio')
        if stats.acwr:
            stats.acwr = stats.acwr / 100  # Convert from percentage
        stats.marathon_shape = data.get('marathonShape')
        stats.hrv_baseline = data.get('hrvBaseline')
        stats.rest_days_percent = data.get('restDays')
        stats.training_strain = data.get('trainingStrain')
        stats.monotony = data.get('monotonyValue')
        
        # Sleep from nested data if present
        sleep_data = data.get('latestSleep', {})
        if sleep_data:
            stats.sleep_duration_min = sleep_data.get('duration')
            stats.sleep_quality_score = sleep_data.get('quality') or sleep_data.get('score')
            if stats.sleep_duration_min and stats.sleep_duration_min < 20:
                # Assume hours if value is small
                stats.sleep_duration_min = int(stats.sleep_duration_min * 60)
        
        return stats
    
    def is_valid(self) -> bool:
        """Check if we have meaningful training data."""
        return self.ctl is not None and self.atl is not None


@dataclass
class Activity:
    """Parsed running activity."""
    date: date
    distance_km: float
    duration_min: float
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    elevation_m: Optional[int] = None
    training_effect: Optional[float] = None
    title: str = ""
    pace_min_per_km: Optional[float] = None
    
    @classmethod
    def from_api_response(cls, data: dict) -> 'Activity':
        """Parse Runalyze activity."""
        act = cls()
        dt = datetime.fromisoformat(data['date_time'].replace('Z', '+00:00'))
        act.date = dt.date()
        act.distance_km = round(data.get('distance', 0), 2)
        act.duration_min = data.get('duration', 0) / 60
        act.avg_hr = data.get('hr_avg')
        act.max_hr = data.get('hr_max')
        act.elevation_m = data.get('elevation_up')
        act.training_effect = data.get('training_effect')
        act.title = data.get('title', 'Run')
        
        if act.distance_km > 0:
            act.pace_min_per_km = act.duration_min / act.distance_km
        
        return act
    
    def speed_kmh(self) -> float:
        if self.duration_min > 0:
            return (self.distance_km / self.duration_min) * 60
        return 0


@dataclass
class AnalysisResult:
    """Complete analysis results."""
    profile: AthleteProfile
    stats: RunalyzeStats
    activities: list[Activity]
    bottlenecks: list[dict] = field(default_factory=list)
    recommendations: list[dict] = field(default_factory=list)
    risk_level: str = "unknown"  # low, moderate, high, critical
    weekly_plan_adjustments: list[dict] = field(default_factory=list)


class MarathonCoachAnalyzer:
    """Scientific marathon training analyzer."""
    
    def __init__(self, token: str):
        self.token = token
        self.client = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient()
        return self
    
    async def __aexit__(self, *args):
        await self.client.aclose()
    
    async def fetch_stats(self) -> RunalyzeStats:
        """Fetch current statistics from Runalyze."""
        headers = {"token": self.token}
        
        resp = await self.client.get(
            f"{RUNALYZE_API_URL}/statistics/current",
            headers=headers
        )
        resp.raise_for_status()
        
        data = resp.json()
        
        # Try to fetch HRV
        try:
            hrv_resp = await self.client.get(
                f"{RUNALYZE_API_URL}/metrics/hrv?limit=1",
                headers=headers
            )
            if hrv_resp.status_code == 200:
                hrv_data = hrv_resp.json()
                if hrv_data:
                    data['latestHrv'] = hrv_data[0]
        except Exception:
            pass
        
        # Try to fetch sleep
        try:
            sleep_resp = await self.client.get(
                f"{RUNALYZE_API_URL}/metrics/sleep?limit=1",
                headers=headers
            )
            if sleep_resp.status_code == 200:
                sleep_data = sleep_resp.json()
                if sleep_data:
                    data['latestSleep'] = sleep_data[0]
        except Exception:
            pass
        
        return RunalyzeStats.from_api_response(data)
    
    async def fetch_activities(self, days: int = 14) -> list[Activity]:
        """Fetch recent running activities."""
        headers = {"token": self.token}
        
        resp = await self.client.get(
            f"{RUNALYZE_API_URL}/activity",
            headers=headers,
            params={"limit": 50}
        )
        resp.raise_for_status()
        
        activities = resp.json()
        cutoff = datetime.now() - timedelta(days=days)
        
        runs = []
        for act in activities:
            if act.get('sport', {}).get('name') != 'Running':
                continue
            
            dt = datetime.fromisoformat(act['date_time'].replace('Z', '+00:00'))
            if dt < cutoff:
                continue
            
            runs.append(Activity.from_api_response(act))
        
        return sorted(runs, key=lambda x: x.date, reverse=True)
    
    def calculate_aerobic_efficiency(self, activities: list[Activity]) -> Optional[float]:
        """
        Calculate aerobic efficiency (speed/HR ratio).
        Higher is better - indicates more speed per heartbeat.
        """
        valid_activities = [a for a in activities if a.avg_hr and a.avg_hr > 100]
        if not valid_activities:
            return None
        
        # Calculate m/s per bpm
        efficiencies = []
        for act in valid_activities:
            speed_ms = (act.distance_km * 1000) / (act.duration_min * 60)
            efficiency = speed_ms / act.avg_hr  # meters per second per bpm
            efficiencies.append(efficiency)
        
        return sum(efficiencies) / len(efficiencies) if efficiencies else None
    
    def calculate_cardiac_drift(self, activity: Activity) -> Optional[float]:
        """
        Estimate cardiac drift from HR data.
        Significant drift (>10%) indicates poor aerobic base or dehydration.
        """
        if not activity.avg_hr or not activity.max_hr:
            return None
        
        # Simple estimate: if max is significantly higher than avg in easy run
        hr_range = activity.max_hr - activity.avg_hr
        drift_percent = (hr_range / activity.avg_hr) * 100
        
        return drift_percent
    
    def analyze_bottlenecks(self, profile: AthleteProfile, stats: RunalyzeStats, 
                           activities: list[Activity]) -> list[dict]:
        """Identify physiological and training bottlenecks."""
        bottlenecks = []
        
        # 1. Fitness Level (CTL)
        if stats.ctl is not None:
            if stats.ctl < RISK_THRESHOLDS['ctl_minimal_fitness']:
                bottlenecks.append({
                    'category': 'Fitness Base',
                    'severity': 'CRITICAL',
                    'finding': f'CTL = {stats.ctl:.1f} - Severely detrained state',
                    'physiology': 'Aerobic enzyme activity, mitochondrial density, and capillary ' \
                                  'network are substantially diminished. This is consistent with ' \
                                  f'{stats.rest_days_percent or "unknown"}% rest days.',
                    'impact': 'Cannot accumulate sufficient training load for marathon in remaining time',
                    'science_ref': 'Bosquet et al. (2007) - detraining effects visible within 2-4 weeks'
                })
            elif stats.ctl < RISK_THRESHOLDS['ctl_moderate_fitness']:
                bottlenecks.append({
                    'category': 'Fitness Base',
                    'severity': 'HIGH',
                    'finding': f'CTL = {stats.ctl:.1f} - Low aerobic fitness',
                    'physiology': 'Below minimal threshold for marathon training. Risk of injury ' \
                                  'increases significantly when ramping volume.',
                    'impact': 'Marathon completion possible but will require careful load management',
                    'science_ref': 'Foster (2001) - sudden load increase in low-fitness athletes '
                                   'increases injury risk by 4-5x'
                })
        
        # 2. Fatigue State (TSB)
        if stats.tsb is not None:
            if stats.tsb < RISK_THRESHOLDS['tsb_severe_fatigue']:
                bottlenecks.append({
                    'category': 'Recovery Status',
                    'severity': 'CRITICAL',
                    'finding': f'TSB = {stats.tsb:.1f} - Severe accumulated fatigue',
                    'physiology': 'Parasympathetic suppression, glycogen depletion, ' \
                                  'muscle damage not repaired.',
                    'impact': 'Training quality compromised, injury/illness risk elevated',
                    'science_ref': 'Banister (1991) - negative TSB indicates incomplete recovery'
                })
            elif stats.tsb < RISK_THRESHOLDS['tsb_moderate_fatigue']:
                bottlenecks.append({
                    'category': 'Recovery Status',
                    'severity': 'MODERATE',
                    'finding': f'TSB = {stats.tsb:.1f} - Moderate fatigue accumulation',
                    'physiology': 'Some residual fatigue present. Current ATL ({stats.atl:.1f}) ' \
                                  'exceeds CTL ({stats.ctl:.1f}).',
                    'impact': 'Monitor closely; may need additional recovery days',
                    'science_ref': 'Jeukendrup & Hesselink (1994) - TSB correlates with performance'
                })
        
        # 3. Workload Ratio (ACWR)
        if stats.acwr is not None:
            if stats.acwr < 0.5:
                bottlenecks.append({
                    'category': 'Training Progression',
                    'severity': 'HIGH',
                    'finding': f'ACWR = {stats.acwr:.2f} - Critically low chronic load',
                    'physiology': 'Insufficient chronic training base to support progression. ' \
                                  'Athlete is essentially starting from scratch.',
                    'impact': 'Must build base VERY gradually; 10-week timeline extremely tight',
                    'science_ref': 'Gabbett (2016) - ACWR < 0.8 indicates undertraining, '
                                   '>1.5 indicates spike injury risk'
                })
        
        # 4. Training Monotony
        if stats.monotony is not None and stats.monotony > RISK_THRESHOLDS['monotony_high']:
            bottlenecks.append({
                'category': 'Training Variety',
                'severity': 'MODERATE',
                'finding': f'Monotony = {stats.monotony:.2f} - Excessive training sameness',
                'physiology': 'Lack of intensity variation leads to plateau and increases '
                              'staleness/overtraining risk.',
                'impact': 'Need to introduce polarized training structure',
                'science_ref': 'Foster (1998) - monotony > 2.0 increases overtraining risk; '
                               'Seiler (2010) - polarized training optimal'
            })
        
        # 5. Heart Rate Analysis from First Run
        if activities:
            first_run = activities[0]  # Most recent
            zones = profile.training_zones()
            z2_upper = zones['Z2_aerobic'][1]
            
            if first_run.avg_hr and first_run.avg_hr > z2_upper:
                bottlenecks.append({
                    'category': 'Pacing/Intensity Control',
                    'severity': 'HIGH',
                    'finding': f'First run HR {first_run.avg_hr} bpm exceeds Z2 upper limit ({z2_upper} bpm)',
                    'physiology': f'At {first_run.avg_hr} bpm for easy run, athlete is likely ' \
                                  f'operating in Z3 (tempo) without adequate aerobic base. ' \
                                  f'Pace {first_run.pace_min_per_km:.0f}:{first_run.pace_min_per_km%1*60:02.0f}/km ' \
                                  f'too fast for current fitness.',
                    'impact': 'Accumulating unnecessary fatigue, poor aerobic development',
                    'science_ref': 'Esteve-Lanao et al. (2005) - spending >10% time in Z3 '
                                   'impairs performance in recreational runners'
                })
        
        # 6. Sleep Quality
        if stats.deep_sleep_percent is not None and stats.deep_sleep_percent < 15:
            bottlenecks.append({
                'category': 'Recovery Quality',
                'severity': 'MODERATE',
                'finding': f'Deep sleep {stats.deep_sleep_percent:.1f}% below optimal (15-20%)',
                'physiology': 'GH secretion, glycogen resynthesis, and muscle repair occur during deep sleep.',
                'impact': 'Impaired adaptation to training stimulus',
                'science_ref': 'Fullagar et al. (2015) - sleep and athletic performance review'
            })
        
        # 7. VO2max Status
        if stats.vo2max is not None and stats.vo2max == 0:
            bottlenecks.append({
                'category': 'Data Quality',
                'severity': 'INFO',
                'finding': 'VO2max not calculated - insufficient HR data',
                'physiology': 'Runalyze requires multiple max-effort activities with HR to estimate VO2max.',
                'impact': 'Cannot track aerobic fitness progression numerically',
                'science_ref': 'Requires 2-3 maximal efforts with HR data for estimation'
            })
        
        return bottlenecks
    
    def generate_recommendations(self, profile: AthleteProfile, stats: RunalyzeStats,
                                 activities: list[Activity], bottlenecks: list[dict]) -> list[dict]:
        """Generate research-backed training recommendations."""
        recommendations = []
        weeks_left = profile.weeks_to_goal()
        zones = profile.training_zones()
        
        # RECOMMENDATION 1: CTL Building Protocol
        if stats.ctl and stats.ctl < RISK_THRESHOLDS['ctl_moderate_fitness']:
            target_weekly_increase = min(4, stats.ctl * 0.10)  # 10% or max 4 TSS/week
            target_ctl = min(40, stats.ctl + (target_weekly_increase * weeks_left))
            
            recommendations.append({
                'priority': 1,
                'category': 'Fitness Development',
                'title': f'Emergency CTL Building Protocol (Current: {stats.ctl:.1f}, Target: ~{target_ctl:.0f})',
                'actions': [
                    f'Increase weekly TSS by 5-10% max (current capacity: ~{stats.ctl * 7:.0f} TSS/week)',
                    'Prioritize frequency over duration: 4-5 runs/week better than 2-3 long runs',
                    'All runs in Z1-Z2 only for first 4 weeks to build aerobic base',
                    'Target CTL progression: {} → {} → {} → {}'.format(
                        stats.ctl,
                        min(stats.ctl * 1.3, stats.ctl + 4),
                        min(stats.ctl * 1.6, stats.ctl + 8),
                        target_ctl
                    )
                ],
                'physiology': 'CTL responds to chronic training load accumulation. With low starting point, '
                              'need frequent moderate stimuli rather than infrequent large loads.',
                'science_ref': 'Allen & Coggan (2010) - Training and Racing with a Power Meter, '
                               'Chapter 4 on CTL building'
            })
        
        # RECOMMENDATION 2: Fatigue Management
        if stats.tsb and stats.tsb < -10:
            recommendations.append({
                'priority': 1,
                'category': 'Recovery Management',
                'title': f'Address Negative TSB ({stats.tsb:.1f}) Before Load Increase',
                'actions': [
                    'Implement 2-3 days of complete rest or active recovery only',
                    'Ensure 8+ hours sleep with consistent schedule',
                    'Only resume progression when TSB > -10',
                    'Monitor morning HRV - if below baseline, extend rest'
                ],
                'physiology': 'Negative TSB indicates incomplete recovery. Training with ATL > CTL '
                              'is unsustainable and leads to overreaching/overtraining.',
                'science_ref': 'Banister (1991) - TSB model; Budgett (1998) - overtraining syndrome'
            })
        
        # RECOMMENDATION 3: Polarized Training Structure
        recommendations.append({
            'priority': 2,
            'category': 'Training Structure',
            'title': 'Implement Polarized Training (80/20 Distribution)',
            'actions': [
                f'80% of time in Z1-Z2 (HR < {zones["Z2_aerobic"][1]} bpm)',
                f'20% of time in Z4-Z5 (HR > {zones["Z4_threshold"][0]} bpm)',
                'AVOID Z3 (grey zone/tempo) except for specific sessions',
                'Weekly structure: 1 long run, 1 interval session, 3-4 easy runs'
            ],
            'physiology': 'Polarized training maximizes aerobic adaptation while managing fatigue. '
                          'Z3 creates fatigue without sufficient stimulus for adaptation.',
            'science_ref': 'Seiler (2010) - Intensity distribution in endurance athletes; '
                           'Stöggl & Sperlich (2014) - polarized vs threshold training'
        })
        
        # RECOMMENDATION 4: Long Run Progression
        if activities:
            recent_distance = max(a.distance_km for a in activities) if activities else 0
            current_long_run = recent_distance
            target_long_run = min(32, 30)  # 30-32 km for marathon
            
            # Conservative progression for low fitness
            weekly_increase = min(10, max(5, current_long_run * 0.10))
            weeks_to_target = (target_long_run - current_long_run) / weekly_increase
            
            recommendations.append({
                'priority': 2,
                'category': 'Long Run Development',
                'title': f'Long Run Progression ({current_long_run:.1f}km → {target_long_run}km)',
                'actions': [
                    f'Increase long run by {weekly_increase:.1f}km per week MAX',
                    f'3-week cycle: build → build → recovery (reduce 20-30%)',
                    f'Timeline to 30km: ~{weeks_to_target:.0f} weeks (aggressive but possible)',
                    'Keep long runs conversational pace - should finish feeling you could do more'
                ],
                'physiology': 'Long runs develop mitochondrial density, fat oxidation, and mental preparation. '
                              'Progressive overload required but must respect tissue adaptation timelines.',
                'science_ref': 'Midgley et al. (2006) - long run training for marathon performance'
            })
        
        # RECOMMENDATION 5: Marathon Readiness Assessment
        min_ctl_for_finish = 30  # Bare minimum
        comfortable_ctl = 50
        
        if stats.ctl and stats.ctl < min_ctl_for_finish:
            recommendations.append({
                'priority': 3,
                'category': 'Goal Feasibility',
                'title': '⚠️ MARATHON COMPLETION AT RISK',
                'actions': [
                    f'Current CTL ({stats.ctl:.1f}) far below minimum ({min_ctl_for_finish}) for marathon',
                    f'With {weeks_left} weeks remaining, need aggressive but careful build',
                    'Consider: Drop to half-marathon (much more achievable)',
                    'Use run-walk strategy from start',
                    'Extend timeline if possible (fall marathon)',
                    'Focus on completion, not time goal'
                ],
                'physiology': 'Marathon requires glycogen storage capacity, fat oxidation efficiency, '
                              'and musculoskeletal durability that require minimum training loads.',
                'science_ref': 'Joyner (2017) - physiology of marathon running; physiological minimums '
                               'for 42.2km completion'
            })
        
        return sorted(recommendations, key=lambda x: x['priority'])
    
    def adjust_weekly_plan(self, profile: AthleteProfile, stats: RunalyzeStats,
                           activities: list[Activity]) -> list[dict]:
        """Generate specific plan adjustments for current week."""
        adjustments = []
        zones = profile.training_zones()
        z1_z2_upper = zones['Z2_extended'][1]  # Use extended Z2 for beginners
        
        # Analyze Tuesday's run
        tuesday_run = None
        for act in activities:
            if act.date.weekday() == 1:  # Tuesday
                tuesday_run = act
                break
        
        # THURSDAY ADJUSTMENT
        thursday_adjustment = {
            'day': 'Thursday',
            'original': '6 km easy',
            'adjusted_plan': '',
            'rationale': '',
            'specific_targets': {}
        }
        
        if stats.tsb and stats.tsb < -15:
            thursday_adjustment['adjusted_plan'] = 'REST or 30 min walk only'
            thursday_adjustment['rationale'] = f'TSB {stats.tsb:.1f} indicates severe fatigue. Extra recovery needed.'
            thursday_adjustment['specific_targets'] = {'activity': 'rest', 'hr_cap': None}
        elif tuesday_run and tuesday_run.avg_hr and tuesday_run.avg_hr > z1_z2_upper:
            thursday_adjustment['adjusted_plan'] = '5 km VERY EASY (or skip)'
            thursday_adjustment['rationale'] = f'Tuesday HR {tuesday_run.avg_hr} was too high. Reduce load to manage fatigue.'
            thursday_adjustment['specific_targets'] = {
                'distance_km': 5,
                'pace_target': '9:00-10:00/km',
                'hr_target': f'{zones["Z1_recovery"][0]}-{zones["Z2_aerobic"][0]} bpm',
                'hr_cap': zones['Z2_aerobic'][0],
                'rpe_target': '3-4/10'
            }
        else:
            thursday_adjustment['adjusted_plan'] = '6 km easy with HR cap'
            thursday_adjustment['rationale'] = 'Normal easy run with strict HR control'
            thursday_adjustment['specific_targets'] = {
                'distance_km': 6,
                'pace_target': '8:30-9:30/km',
                'hr_target': f'{zones["Z1_recovery"][0]}-{z1_z2_upper} bpm',
                'hr_cap': z1_z2_upper,
                'rpe_target': '4-5/10'
            }
        
        adjustments.append(thursday_adjustment)
        
        # SUNDAY LONG RUN ADJUSTMENT
        sunday_adjustment = {
            'day': 'Sunday',
            'original': '12 km long run',
            'adjusted_plan': '',
            'rationale': '',
            'specific_targets': {}
        }
        
        # Calculate appropriate long run distance
        base_long_run = 12
        if stats.ctl and stats.ctl < 20:
            # Reduce for very low fitness
            recommended_long = min(base_long_run, 10)
            sunday_adjustment['adjusted_plan'] = f'{recommended_long} km long run (reduced from 12km)'
            sunday_adjustment['rationale'] = f'Low CTL ({stats.ctl:.1f}) - aggressive long runs increase injury risk'
        elif stats.tsb and stats.tsb < -10:
            recommended_long = min(base_long_run, 10)
            sunday_adjustment['adjusted_plan'] = f'{recommended_long} km easy (or split: 6km AM + 4km PM)'
            sunday_adjustment['rationale'] = f'Negative TSB ({stats.tsb:.1f}) suggests splitting load or reducing'
        else:
            recommended_long = base_long_run
            sunday_adjustment['adjusted_plan'] = f'{recommended_long} km long run with HR control'
            sunday_adjustment['rationale'] = 'Standard progression with strict intensity management'
        
        sunday_adjustment['specific_targets'] = {
            'distance_km': recommended_long,
            'pace_target': '8:30-9:30/km (slower than Tuesday!)',
            'hr_target': f'{zones["Z1_recovery"][0]}-{z1_z2_upper} bpm',
            'hr_cap': z1_z2_upper,
            'rpe_target': '4-5/10 (conversational)',
            'strategy': 'Start 1 min/km slower than target, negative split if feeling good'
        }
        
        adjustments.append(sunday_adjustment)
        
        return adjustments
    
    def calculate_overall_risk(self, stats: RunalyzeStats, bottlenecks: list[dict]) -> str:
        """Calculate overall training risk level."""
        critical = sum(1 for b in bottlenecks if b.get('severity') == 'CRITICAL')
        high = sum(1 for b in bottlenecks if b.get('severity') == 'HIGH')
        
        if critical >= 2 or (stats.ctl and stats.ctl < 10):
            return 'CRITICAL'
        elif critical >= 1 or high >= 2:
            return 'HIGH'
        elif high >= 1:
            return 'MODERATE'
        else:
            return 'LOW'
    
    async def analyze(self, profile: AthleteProfile, days: int = 14) -> AnalysisResult:
        """Run complete analysis."""
        print("📊 Fetching Runalyze data...")
        stats = await self.fetch_stats()
        activities = await self.fetch_activities(days)
        
        print(f"   ✓ Stats: CTL={stats.ctl}, ATL={stats.atl}, TSB={stats.tsb}")
        print(f"   ✓ Activities: {len(activities)} runs in last {days} days")
        
        print("\n🔍 Analyzing bottlenecks...")
        bottlenecks = self.analyze_bottlenecks(profile, stats, activities)
        print(f"   Found {len(bottlenecks)} bottleneck(s)")
        
        print("\n💡 Generating recommendations...")
        recommendations = self.generate_recommendations(profile, stats, activities, bottlenecks)
        print(f"   Generated {len(recommendations)} recommendation(s)")
        
        print("\n📅 Adjusting weekly plan...")
        weekly_adjustments = self.adjust_weekly_plan(profile, stats, activities)
        
        risk_level = self.calculate_overall_risk(stats, bottlenecks)
        
        return AnalysisResult(
            profile=profile,
            stats=stats,
            activities=activities,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            risk_level=risk_level,
            weekly_plan_adjustments=weekly_adjustments
        )


def print_report(result: AnalysisResult):
    """Print formatted analysis report."""
    profile = result.profile
    stats = result.stats
    
    print("\n" + "=" * 80)
    print("🏃 MARATHON COACH ANALYSIS REPORT")
    print("=" * 80)
    
    # Header Info
    print(f"\n📋 ATHLETE PROFILE")
    print(f"   Age: {profile.age} | Goal: {profile.goal_distance} on {profile.goal_date}")
    print(f"   Weeks remaining: {profile.weeks_to_goal()}")
    print(f"   Max HR (est): {profile.estimated_max_hr()} bpm")
    
    zones = profile.training_zones()
    print(f"\n   Training Zones (Karvonen %HRR):")
    for zone, (low, high) in zones.items():
        if 'extended' not in zone:  # Skip extended zone in display
            print(f"      {zone}: {low}-{high} bpm")
    
    # Risk Banner
    risk_emoji = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MODERATE': '🟡', 'LOW': '🟢'}
    print(f"\n{'=' * 80}")
    print(f"OVERALL RISK LEVEL: {risk_emoji.get(result.risk_level, '⚪')} {result.risk_level}")
    print(f"{'=' * 80}")
    
    # Executive Summary
    print(f"\n{'─' * 80}")
    print("📌 EXECUTIVE SUMMARY")
    print(f"{'─' * 80}")
    
    key_findings = []
    if stats.ctl and stats.ctl < 20:
        key_findings.append(f"• CRITICAL: CTL ({stats.ctl:.1f}) indicates severely detrained state")
    if stats.tsb and stats.tsb < -15:
        key_findings.append(f"• HIGH: TSB ({stats.tsb:.1f}) shows significant fatigue accumulation")
    if stats.acwr and stats.acwr < 0.5:
        key_findings.append(f"• HIGH: ACWR ({stats.acwr:.2f}) indicates critically low training base")
    if result.activities and result.activities[0].avg_hr:
        first_hr = result.activities[0].avg_hr
        z2_upper = zones['Z2_aerobic'][1]
        if first_hr > z2_upper:
            key_findings.append(f"• MODERATE: First run HR ({first_hr}) exceeded easy zone ({z2_upper})")
    
    for finding in key_findings[:5]:
        print(f"  {finding}")
    
    # Bottlenecks
    print(f"\n{'─' * 80}")
    print("🚨 BOTTLENECK ANALYSIS")
    print(f"{'─' * 80}")
    
    for bottleneck in result.bottlenecks:
        severity_emoji = {
            'CRITICAL': '🔴',
            'HIGH': '🟠',
            'MODERATE': '🟡',
            'INFO': '🔵'
        }.get(bottleneck.get('severity', ''), '⚪')
        
        print(f"\n  {severity_emoji} {bottleneck['category']} [{bottleneck.get('severity', 'UNKNOWN')}]")
        print(f"     Finding: {bottleneck['finding']}")
        print(f"     Physiology: {bottleneck.get('physiology', 'N/A')[:150]}...")
        print(f"     Impact: {bottleneck.get('impact', 'N/A')}")
        print(f"     Ref: {bottleneck.get('science_ref', 'N/A')}")
    
    # Recommendations
    print(f"\n{'─' * 80}")
    print("💡 RESEARCH-BACKED RECOMMENDATIONS")
    print(f"{'─' * 80}")
    
    for rec in result.recommendations:
        priority_emoji = {1: '🔴', 2: '🟠', 3: '🟡'}.get(rec.get('priority'), '⚪')
        print(f"\n  {priority_emoji} [{rec.get('priority')}] {rec['title']}")
        print(f"     Category: {rec['category']}")
        print(f"     Actions:")
        for action in rec.get('actions', []):
            print(f"       • {action}")
        print(f"     Science: {rec.get('science_ref', 'N/A')[:100]}...")
    
    # Weekly Plan Adjustments
    print(f"\n{'─' * 80}")
    print("📅 THIS WEEK'S ADJUSTED PLAN")
    print(f"{'─' * 80}")
    
    for adj in result.weekly_plan_adjustments:
        print(f"\n  {adj['day'].upper()}")
        print(f"     Original: {adj['original']}")
        print(f"     Adjusted: {adj['adjusted_plan']}")
        print(f"     Rationale: {adj['rationale']}")
        targets = adj.get('specific_targets', {})
        if targets:
            print(f"     Targets:")
            for key, value in targets.items():
                if key != 'activity':
                    print(f"       • {key}: {value}")
    
    # Additional Metrics
    print(f"\n{'─' * 80}")
    print("📊 ADDITIONAL METRICS")
    print(f"{'─' * 80}")
    
    if result.activities:
        recent = result.activities[0]
        print(f"\n  Most Recent Run ({recent.date}):")
        print(f"    Distance: {recent.distance_km:.2f} km")
        print(f"    Duration: {recent.duration_min:.0f} min")
        print(f"    Pace: {recent.pace_min_per_km:.2f} min/km" if recent.pace_min_per_km else "    Pace: N/A")
        print(f"    Avg HR: {recent.avg_hr} bpm" if recent.avg_hr else "    Avg HR: N/A")
        print(f"    Training Effect: {recent.training_effect}" if recent.training_effect else "    Training Effect: N/A")
    
    # First Run Analysis
    if result.activities:
        first = result.activities[0]
        if first.avg_hr and first.pace_min_per_km:
            print(f"\n  First Run Analysis:")
            z2_low, z2_high = zones['Z2_aerobic']
            
            print(f"    • Average HR: {first.avg_hr} bpm")
            print(f"    • Target Z2 range: {z2_low}-{z2_high} bpm")
            
            if first.avg_hr > z2_high:
                deviation = first.avg_hr - z2_high
                print(f"    • ⚠️ {deviation} bpm ABOVE Z2 upper limit")
                print(f"    • Interpretation: Running too fast for aerobic base development")
                print(f"    • Impact: Accumulating fatigue without optimal aerobic stimulus")
            elif first.avg_hr < z2_low:
                print(f"    • ✓ Below Z2 - good recovery pace")
            else:
                print(f"    • ✓ Within Z2 target range")
            
            # Estimate efficiency
            speed_ms = (first.distance_km * 1000) / (first.duration_min * 60)
            efficiency = speed_ms / first.avg_hr if first.avg_hr else 0
            print(f"    • Aerobic Efficiency: {efficiency:.3f} m/s per bpm")
            print(f"      (Reference: trained runners ~0.25-0.35, beginners ~0.15-0.25)")
    
    print(f"\n{'=' * 80}")
    print("End of Report")
    print(f"{'=' * 80}\n")


async def main():
    parser = argparse.ArgumentParser(
        description="Marathon Coach Analysis Tool - Scientific training analysis"
    )
    parser.add_argument(
        "--days", 
        type=int, 
        default=14,
        help="Number of days of activity history to analyze (default: 14)"
    )
    parser.add_argument(
        "--age",
        type=int,
        default=23,
        help="Athlete age for HR calculations (default: 23)"
    )
    parser.add_argument(
        "--goal-date",
        type=str,
        default="2026-04-15",
        help="Marathon date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted report"
    )
    
    args = parser.parse_args()
    
    if not RUNALYZE_TOKEN:
        print("Error: RUNALYZE_TOKEN environment variable required")
        sys.exit(1)
    
    profile = AthleteProfile(
        age=args.age,
        goal_date=date.fromisoformat(args.goal_date)
    )
    
    async with MarathonCoachAnalyzer(RUNALYZE_TOKEN) as analyzer:
        result = await analyzer.analyze(profile, days=args.days)
        
        if args.json:
            import json
            # Convert to dict for JSON output
            output = {
                'risk_level': result.risk_level,
                'profile': {
                    'age': result.profile.age,
                    'weeks_to_goal': result.profile.weeks_to_goal(),
                    'max_hr_estimated': result.profile.estimated_max_hr(),
                    'training_zones': result.profile.training_zones()
                },
                'stats': {
                    'vo2max': result.stats.vo2max,
                    'ctl': result.stats.ctl,
                    'atl': result.stats.atl,
                    'tsb': result.stats.tsb,
                    'acwr': result.stats.acwr,
                    'marathon_shape': result.stats.marathon_shape,
                    'hrv_baseline': result.stats.hrv_baseline,
                    'monotony': result.stats.monotony,
                    'training_strain': result.stats.training_strain
                },
                'bottlenecks': result.bottlenecks,
                'recommendations': result.recommendations,
                'weekly_adjustments': result.weekly_plan_adjustments,
                'activities': [
                    {
                        'date': a.date.isoformat(),
                        'distance_km': a.distance_km,
                        'duration_min': a.duration_min,
                        'avg_hr': a.avg_hr,
                        'pace_min_per_km': a.pace_min_per_km
                    }
                    for a in result.activities
                ]
            }
            print(json.dumps(output, indent=2))
        else:
            print_report(result)


if __name__ == "__main__":
    asyncio.run(main())
