from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal


# Session models
class SessionStart(BaseModel):
    type: Literal["expected", "personal"]
    intention: Optional[str] = None


class SessionEnd(BaseModel):
    distractions: Literal["none", "some", "many"]
    did_the_thing: bool
    rabbit_hole: Optional[bool] = None


class Session(BaseModel):
    id: int
    type: str
    intention: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    distractions: Optional[str]
    did_the_thing: Optional[bool]
    rabbit_hole: Optional[bool]


# Priority models
class Priority(BaseModel):
    id: int
    name: str
    rank: int
    session_count: int = 0


class PriorityCreate(BaseModel):
    name: str


class PriorityReorder(BaseModel):
    order: list[int]  # List of priority IDs in new order


# Meditation models
class MeditationLog(BaseModel):
    duration_minutes: int
    time_of_day: Optional[Literal["morning", "afternoon", "evening"]] = None
    occurred_at: Optional[datetime] = None


# Exercise models
class ExerciseLog(BaseModel):
    type: Literal["cardio", "strength"]
    duration_minutes: int
    intensity: Literal["light", "medium", "hard"]


# Pulse models
class PulseLog(BaseModel):
    feeling: Literal["heavy", "okay", "light"]
    had_connection: bool
    connection_type: Optional[Literal["friend", "family", "partner"]] = None


# Settings models
class Settings(BaseModel):
    daily_cap: int = 10
    hard_max: int = 16
    evening_cutoff: str = "19:00"
    rabbit_hole_check: int = 3
    weekly_rest_min: int = 1
    session_duration: int = 25
    short_break: int = 5
    long_break: int = 15


class SettingsUpdate(BaseModel):
    daily_cap: Optional[int] = None
    hard_max: Optional[int] = None
    evening_cutoff: Optional[str] = None
    rabbit_hole_check: Optional[int] = None
    weekly_rest_min: Optional[int] = None
    session_duration: Optional[int] = None
    short_break: Optional[int] = None
    long_break: Optional[int] = None


# App State
class AppState(BaseModel):
    break_until: Optional[datetime]
    check_in_mode: bool
    north_star: str


# API responses
class TimerCompleteResponse(BaseModel):
    break_duration: int
    cycle_position: int
    is_long_break: bool
    break_until: datetime


class BreakCheck(BaseModel):
    on_break: bool
    remaining_seconds: int = 0


class CanStart(BaseModel):
    allowed: bool
    reason: Optional[str] = None


# Claude Code integration models
class SessionInfo(BaseModel):
    id: int
    type: str
    intention: Optional[str]
    remaining_seconds: int


class SessionActiveResponse(BaseModel):
    allowed: bool
    reason: Optional[Literal["no_session", "on_break"]] = None
    break_remaining: Optional[int] = None
    session: Optional[SessionInfo] = None


class QuickStartRequest(BaseModel):
    type: Literal["expected", "personal"]
    intention: str


class QuickStartResponse(BaseModel):
    success: bool
    session_id: Optional[int] = None
    reason: Optional[str] = None
    remaining: Optional[int] = None


class MarkClaudeUsedResponse(BaseModel):
    marked: bool
