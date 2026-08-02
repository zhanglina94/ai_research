"""Experiment design, code generation, execution, and AutoResearch API."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.coding import CodingAgent
from app.agents.experiment import ExperimentAgent
from app.api.schemas import (
    AutoResearchInitRequest,
    AutoResearchInitResponse,
    AutoResearchIterationItem,
    AutoResearchRunRequest,
    AutoResearchRunResponse,
    CodeGenerateRequest,
    CodeGenerateResponse,
    ExperimentDesignRequest,
    ExperimentDesignResponse,
    ExperimentResponse,
    ExperimentRunRequest,
    MLflowExperimentItem,
)
from app.config import get_settings
from app.database.postgres import ExperimentRecord, get_db
from app.tools.experiment_prepare import run_prepare
from app.tools.experiment_runner import experiment_runtime_info, run_experiment_script
from app.tools.experiment_template import PRIMARY_METRIC, init_experiment_workspace
from app.tools.mlflow_client import get_mlflow_client
from app.workflows.autoresearch_loop import run_autoresearch_loop

router = APIRouter(prefix="/experiments", tags=["experiments"])
settings = get_settings()


def _autoresearch_meta(record: ExperimentRecord) -> dict:
    spec = record.spec or {}
    return spec.get("autoresearch", {})


@router.get("/runtime")
async def get_experiment_runtime() -> dict:
    """GPU, Docker, and training mode configuration."""
    return experiment_runtime_info()


@router.get("/mlflow", response_model=list[MLflowExperimentItem])
async def list_mlflow_experiments() -> list[MLflowExperimentItem]:
    client = get_mlflow_client()
    exps = client.list_experiments()
    return [MLflowExperimentItem(**e) for e in exps]


@router.post("/autoresearch/init", response_model=AutoResearchInitResponse)
async def init_autoresearch(
    request: AutoResearchInitRequest,
    db: AsyncSession = Depends(get_db),
) -> AutoResearchInitResponse:
    exp_id = str(uuid4())
    workspace = init_experiment_workspace(
        exp_id,
        request.topic,
        train_budget_seconds=request.train_budget_seconds,
        hypothesis=request.hypothesis,
    )

    prepare_result = await run_prepare(workspace["prepare_path"], timeout=120)

    record = ExperimentRecord(
        id=exp_id,
        project_id=request.project_id,
        name=request.topic[:512],
        hypothesis=request.hypothesis or request.topic,
        spec={
            "autoresearch": {
                "topic": request.topic,
                "train_budget_seconds": request.train_budget_seconds,
                "max_iterations": request.max_iterations,
                "primary_metric": PRIMARY_METRIC,
                "iterations": [],
            }
        },
        code_dir=workspace["experiment_dir"],
        status="optimizing",
    )
    db.add(record)
    await db.commit()

    return AutoResearchInitResponse(
        experiment_id=exp_id,
        experiment_dir=workspace["experiment_dir"],
        program_path=workspace["program_path"],
        train_path=workspace["train_path"],
        prepare_status=prepare_result.get("status", "unknown"),
        primary_metric=PRIMARY_METRIC,
    )


@router.post("/{experiment_id}/autoresearch", response_model=AutoResearchRunResponse)
async def run_autoresearch(
    experiment_id: str,
    request: AutoResearchRunRequest,
    db: AsyncSession = Depends(get_db),
) -> AutoResearchRunResponse:
    record = await db.get(ExperimentRecord, experiment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if not record.code_dir:
        raise HTTPException(status_code=400, detail="Initialize autoresearch workspace first")

    meta = _autoresearch_meta(record)
    max_iter = request.max_iterations or meta.get("max_iterations") or settings.autoresearch_max_iterations
    budget = request.train_budget_seconds or meta.get("train_budget_seconds") or settings.autoresearch_train_budget_seconds
    topic = meta.get("topic") or record.name

    result = await run_autoresearch_loop(
        experiment_id=experiment_id,
        experiment_dir=record.code_dir,
        topic=topic,
        project_id=record.project_id,
        max_iterations=max_iter,
        train_budget_seconds=budget,
    )

    spec = record.spec or {}
    spec["autoresearch"] = {
        **meta,
        "train_budget_seconds": budget,
        "max_iterations": max_iter,
        "best_metric": result["best_metric"],
        "iterations": result["history"],
    }
    record.spec = spec
    record.status = result["status"]
    record.metrics = {
        PRIMARY_METRIC: result["best_metric"],
        "iteration_count": result["iteration_count"],
    }
    await db.commit()

    iterations = [
        AutoResearchIterationItem(
            iteration=i["iteration"],
            val_bpb=i.get("val_bpb"),
            kept=i.get("kept", False),
            status=i.get("status"),
            best_metric=i.get("best_metric"),
        )
        for i in result["history"]
    ]

    return AutoResearchRunResponse(
        experiment_id=experiment_id,
        status=result["status"],
        best_metric=result["best_metric"],
        primary_metric=result["primary_metric"],
        iteration_count=result["iteration_count"],
        iterations=iterations,
        experiment_dir=record.code_dir,
    )


@router.get("/{experiment_id}/iterations", response_model=list[AutoResearchIterationItem])
async def list_iterations(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[AutoResearchIterationItem]:
    record = await db.get(ExperimentRecord, experiment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Experiment not found")
    meta = _autoresearch_meta(record)
    return [
        AutoResearchIterationItem(
            iteration=i["iteration"],
            val_bpb=i.get("val_bpb"),
            kept=i.get("kept", False),
            status=i.get("status"),
            best_metric=i.get("best_metric"),
        )
        for i in meta.get("iterations", [])
    ]


@router.post("/design", response_model=ExperimentDesignResponse)
async def design_experiment(
    request: ExperimentDesignRequest,
    db: AsyncSession = Depends(get_db),
) -> ExperimentDesignResponse:
    agent = ExperimentAgent()
    spec = await agent.design_experiment(request.topic, context=request.context)
    exp_id = str(uuid4())

    record = ExperimentRecord(
        id=exp_id,
        project_id=request.project_id,
        name=request.topic[:512],
        hypothesis=spec["hypothesis"],
        spec=spec,
        status="designed",
    )
    db.add(record)
    await db.commit()

    return ExperimentDesignResponse(experiment_id=exp_id, **spec)


@router.post("/code", response_model=CodeGenerateResponse)
async def generate_code(
    request: CodeGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> CodeGenerateResponse:
    record = await db.get(ExperimentRecord, request.experiment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Experiment not found")

    agent = CodingAgent()
    result = await agent.generate_code(request.spec or record.spec or {}, request.experiment_id)

    record.code_dir = result["experiment_dir"]
    record.status = "coded"
    await db.commit()

    return CodeGenerateResponse(
        experiment_id=request.experiment_id,
        files=result["files"],
        written_paths=result["written_paths"],
        experiment_dir=result["experiment_dir"],
    )


@router.post("/run")
async def run_experiment(
    request: ExperimentRunRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    record = await db.get(ExperimentRecord, request.experiment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if not record.code_dir:
        raise HTTPException(status_code=400, detail="Generate code first")

    train_script = str(Path(record.code_dir) / "train.py")
    budget = settings.autoresearch_train_budget_seconds
    meta = _autoresearch_meta(record)
    if meta.get("train_budget_seconds"):
        budget = meta["train_budget_seconds"]

    run_result = await run_experiment_script(
        train_script,
        timeout=budget + 60,
        train_budget_seconds=budget,
    )

    mlflow = get_mlflow_client()
    metrics = run_result.get("metrics", {})
    mlflow_run_id = None
    if metrics:
        mlflow_run_id = mlflow.log_run(
            experiment_name=f"exp-{record.project_id or 'default'}",
            run_name=record.id,
            params=(record.spec or {}).get("training_config", {}),
            metrics=metrics,
            artifacts={"train.py": train_script},
        )

    record.status = run_result.get("status", "failed")
    record.metrics = metrics
    record.mlflow_run_id = mlflow_run_id
    await db.commit()

    return {"experiment_id": record.id, "run_result": run_result, "mlflow_run_id": mlflow_run_id}


@router.get("", response_model=list[ExperimentResponse])
async def list_experiments(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[ExperimentResponse]:
    query = select(ExperimentRecord).order_by(ExperimentRecord.created_at.desc())
    if project_id:
        query = query.where(ExperimentRecord.project_id == project_id)
    result = await db.execute(query)
    return [ExperimentResponse.model_validate(e) for e in result.scalars().all()]
