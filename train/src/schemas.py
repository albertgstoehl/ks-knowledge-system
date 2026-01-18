from pydantic import BaseModel
from typing import Optional, Dict, List, Any


class PlanCreate(BaseModel):
    title: str
    markdown: str
    carry_over_notes: Optional[str] = None


class ExerciseTemplate(BaseModel):
    name: str
    muscles: List[str] = []


class PlanResponse(BaseModel):
    id: int
    title: str
    markdown: str
    templates: Dict[str, List[ExerciseTemplate]]
    created_at: str
    previous_plan_id: Optional[int]
    carry_over_notes: Optional[str]
