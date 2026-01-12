from pydantic import BaseModel
from typing import Optional


class PlanCreate(BaseModel):
    title: str
    markdown: str
    carry_over_notes: Optional[str] = None


class PlanResponse(BaseModel):
    id: int
    title: str
    markdown: str
    created_at: str
    previous_plan_id: Optional[int]
    carry_over_notes: Optional[str]
