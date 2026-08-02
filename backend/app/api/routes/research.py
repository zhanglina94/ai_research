"""Research planning API."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.planner import PlannerAgent
from app.api.schemas import ResearchPlanRequest, ResearchPlanResponse, TaskItem
from app.database.postgres import ResearchProject, get_db

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/plan", response_model=ResearchPlanResponse)
async def create_research_plan(
    request: ResearchPlanRequest,
    db: AsyncSession = Depends(get_db),
) -> ResearchPlanResponse:
    agent = PlannerAgent()
    plan = await agent.generate_plan(request.topic)

    project_id = request.project_id
    if not project_id:
        project = ResearchProject(
            title=plan["research_question"][:512],
            topic=request.topic,
            roadmap=plan,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        project_id = project.id
    else:
        project = await db.get(ResearchProject, project_id)
        if project:
            project.roadmap = plan
            await db.commit()

    return ResearchPlanResponse(
        research_question=plan["research_question"],
        tasks=[TaskItem(**t) for t in plan["tasks"]],
        timeline=plan["timeline"],
        directions=plan["directions"],
        project_id=project_id,
    )
