from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    markdown_path = Column(String, nullable=False)
    previous_plan_id = Column(Integer, ForeignKey("plans.id"))
    carry_over_notes = Column(Text)

    previous_plan = relationship("Plan", remote_side=[id])


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime)
    template_key = Column(String, nullable=False)
    notes = Column(Text)
    plan_id = Column(Integer, ForeignKey("plans.id"))

    plan = relationship("Plan")


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    muscle_groups = Column(Text)
    default_rep_range = Column(String)


class SetEntry(Base):
    __tablename__ = "set_entries"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    set_order = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)
    reps = Column(Integer, nullable=False)
    rir = Column(Integer)
    notes = Column(Text)

    session = relationship("Session")
    exercise = relationship("Exercise")


class RecoverySummary(Base):
    __tablename__ = "recovery_summaries"

    date = Column(Date, primary_key=True)
    
    # Garmin imported metrics
    resting_hr = Column(Integer)
    hrv_avg = Column(Integer)
    sleep_score = Column(Integer)
    sleep_duration_hours = Column(Float)
    deep_sleep_percent = Column(Float)
    avg_stress = Column(Integer)
    
    # Calculated fields
    weekly_mileage = Column(Float)
    readiness_score = Column(Integer)
    
    # User subjective inputs
    soreness = Column(Integer)
    energy = Column(Integer)


class DailyMetrics(Base):
    __tablename__ = "daily_metrics"

    date = Column(Date, primary_key=True)
    
    # Health metrics from Runalyze (originally from Garmin)
    resting_hr = Column(Integer)
    hrv_avg = Column(Integer)
    sleep_score = Column(Integer)
    sleep_duration_hours = Column(Float)
    
    # Training metrics from Runalyze (calculated)
    vo2max = Column(Float)
    marathon_shape = Column(Float)
    tsb = Column(Float)
    atl = Column(Float)
    ctl = Column(Float)
    
    # User subjective inputs
    soreness = Column(Integer)
    energy = Column(Integer)


class Run(Base):
    __tablename__ = "runs"
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    distance_km = Column(Float, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    
    # Optional fields
    avg_hr = Column(Integer)
    elevation_gain_m = Column(Integer)
    
    # User subjective inputs
    effort = Column(Integer)  # 1-10 RPE
    soreness_next_day = Column(Integer)  # 0-10
    notes = Column(Text)
    
    # Source tracking
    source = Column(String, default="manual")  # manual, garmin, strava
    external_id = Column(String)  # Garmin activity ID if imported
    
    created_at = Column(DateTime, server_default=func.now())
