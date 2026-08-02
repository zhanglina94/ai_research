"""Research project management API."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ProjectCreateRequest, ProjectResponse
from app.database.postgres import ResearchProject, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)) -> list[ProjectResponse]:
    try:
        result = await db.execute(select(ResearchProject).order_by(ResearchProject.created_at.desc()))
        projects = result.scalars().all()
        return [ProjectResponse.model_validate(p) for p in projects]
    except Exception as e:
        logger.warning("Failed to list projects (PostgreSQL unavailable): %s", e)
        return []


@router.post("", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    project = ResearchProject(title=request.title, topic=request.topic)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)) -> ProjectResponse:
    project = await db.get(ResearchProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)
