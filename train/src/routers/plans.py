import os
import re
import yaml
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models import Plan
from src.schemas import PlanCreate, PlanResponse


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.
    
    Returns (frontmatter_dict, markdown_without_frontmatter).
    If no frontmatter, returns ({}, original_content).
    """
    # Strip leading whitespace for matching, but preserve original if no match
    stripped = content.lstrip()
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, stripped, re.DOTALL)
    if not match:
        return {}, content
    
    frontmatter_yaml = match.group(1)
    markdown = match.group(2)
    
    try:
        frontmatter = yaml.safe_load(frontmatter_yaml) or {}
    except yaml.YAMLError:
        return {}, content
    
    return frontmatter, markdown


def normalize_templates(raw_templates: dict) -> dict:
    """Normalize templates to consistent format with name and muscles.
    
    Handles both old format (list of strings) and new format (list of objects).
    """
    normalized = {}
    for template_key, exercises in raw_templates.items():
        normalized[template_key] = []
        for ex in exercises:
            if isinstance(ex, str):
                # Old format: just exercise name
                normalized[template_key].append({"name": ex, "muscles": []})
            elif isinstance(ex, dict):
                # New format: {name, muscles}
                normalized[template_key].append({
                    "name": ex.get("name", ""),
                    "muscles": ex.get("muscles", [])
                })
    return normalized

router = APIRouter(prefix="/api/plan", tags=["plan"])

PLAN_DIR = os.getenv("PLAN_DIR", "./plan")


@router.get("/current", response_model=PlanResponse)
async def get_current_plan(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Plan).order_by(Plan.created_at.desc()))
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="No plan found")
    with open(str(plan.markdown_path), "r", encoding="utf-8") as file:
        raw_content = file.read()
    
    frontmatter, markdown = parse_frontmatter(raw_content)
    templates = normalize_templates(frontmatter.get("templates", {}))
    
    return PlanResponse(
        id=plan.id,
        title=plan.title,
        markdown=markdown,
        templates=templates,
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

    frontmatter, markdown = parse_frontmatter(payload.markdown)
    templates = normalize_templates(frontmatter.get("templates", {}))
    
    return PlanResponse(
        id=plan.id,
        title=plan.title,
        markdown=markdown,
        templates=templates,
        created_at=str(plan.created_at),
        previous_plan_id=plan.previous_plan_id,
        carry_over_notes=plan.carry_over_notes,
    )
