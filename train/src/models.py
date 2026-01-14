from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text
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

    session = relationship("Session")
    exercise = relationship("Exercise")
