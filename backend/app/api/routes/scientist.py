"""AI Scientist Loop API — full research automation pipeline."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ScientistRunRequest, ScientistRunResponse
from app.database.postgres import ScientistRun, get_db
from app.workflows.scientist_loop import run_scientist_loop, run_scientist_loop_stream

router = APIRouter(prefix="/scientist", tags=["scientist"])


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


@router.post("/run/stream")
async def stream_scientist_run(request: ScientistRunRequest) -> StreamingResponse:
    """Server-Sent Events stream of Scientist loop progress."""

    async def event_generator():
        try:
            async for event in run_scientist_loop_stream(request.idea, request.project_id):
                yield _sse_event(event)
        except Exception as exc:
            yield _sse_event({"event": "error", "message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/run", response_model=ScientistRunResponse)
async def start_scientist_run(
    request: ScientistRunRequest,
    db: AsyncSession = Depends(get_db),
) -> ScientistRunResponse:
    run = ScientistRun(
        idea=request.idea,
        project_id=request.project_id,
        status="running",
        current_step="idea",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    result = await run_scientist_loop(request.idea, request.project_id, run_id=run.id)

    run.status = result["status"]
    run.current_step = result["current_step"]
    run.paper_draft = result.get("paper_draft")
    run.result = {
        "plan": result.get("plan"),
        "experiment_spec": result.get("experiment_spec"),
        "code_result": result.get("code_result"),
        "run_result": result.get("run_result"),
        "analysis": result.get("analysis"),
    }
    await db.commit()

    return ScientistRunResponse(
        run_id=run.id,
        status=result["status"],
        current_step=result["current_step"],
        plan=result.get("plan"),
        experiment_spec=result.get("experiment_spec"),
        run_result=result.get("run_result"),
        analysis=result.get("analysis"),
        paper_draft=result.get("paper_draft"),
    )


@router.get("/runs", response_model=list[ScientistRunResponse])
async def list_scientist_runs(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[ScientistRunResponse]:
    query = select(ScientistRun).order_by(ScientistRun.created_at.desc())
    if project_id:
        query = query.where(ScientistRun.project_id == project_id)
    result = await db.execute(query)
    runs = result.scalars().all()
    return [
        ScientistRunResponse(
            run_id=r.id,
            status=r.status,
            current_step=r.current_step,
            plan=(r.result or {}).get("plan"),
            experiment_spec=(r.result or {}).get("experiment_spec"),
            run_result=(r.result or {}).get("run_result"),
            analysis=(r.result or {}).get("analysis"),
            paper_draft=r.paper_draft,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=ScientistRunResponse)
async def get_scientist_run(run_id: str, db: AsyncSession = Depends(get_db)) -> ScientistRunResponse:
    run = await db.get(ScientistRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return ScientistRunResponse(
        run_id=run.id,
        status=run.status,
        current_step=run.current_step,
        plan=(run.result or {}).get("plan"),
        experiment_spec=(run.result or {}).get("experiment_spec"),
        run_result=(run.result or {}).get("run_result"),
        analysis=(run.result or {}).get("analysis"),
        paper_draft=run.paper_draft,
    )
