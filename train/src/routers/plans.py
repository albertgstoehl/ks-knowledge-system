import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models import Plan
from src.schemas import PlanCreate, PlanResponse

router = APIRouter(prefix="/api/plan", tags=["plan"])

PLAN_DIR = os.getenv("PLAN_DIR", "./plan")


@router.get("/current", response_model=PlanResponse)
async def get_current_plan(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Plan).order_by(Plan.created_at.desc()))
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="No plan found")
    with open(plan.markdown_path, "r", encoding="utf-8") as file:
        markdown = file.read()
    return PlanResponse(
        id=plan.id,
        title=plan.title,
        markdown=markdown,
        created_at=str(plan.created_at),
        previous_plan_id=plan.previous_plan_id,
        carry_over_notes=plan.carry_over_notes,
    )


@router.post("/register", response_model=PlanResponse)
async def register_plan(payload: PlanCreate, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Plan).order_by(Plan.created_at.desc()))
    previous = result.scalars().first()

    os.makedirs(PLAN_DIR, exist_ok=True)
    filename = f"plan-{payload.title.lower().replace(' ', '-')}.md"
    path = os.path.join(PLAN_DIR, filename)
    with open(path, "w", encoding="utf-8") as file:
        file.write(payload.markdown)

    plan = Plan(
        title=payload.title,
        markdown_path=path,
        previous_plan_id=previous.id if previous else None,
        carry_over_notes=payload.carry_over_notes,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)

    return PlanResponse(
        id=plan.id,
        title=plan.title,
        markdown=payload.markdown,
        created_at=str(plan.created_at),
        previous_plan_id=plan.previous_plan_id,
        carry_over_notes=plan.carry_over_notes,
    )
