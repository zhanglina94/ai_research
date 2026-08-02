"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str = "1.0.0"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    project_id: str | None = None
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    agent: str | None = None
    metadata: dict[str, Any] | None = None


class ResearchPlanRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=2000)
    project_id: str | None = None


class TaskItem(BaseModel):
    title: str
    description: str
    priority: str = "medium"
    estimated_days: int = 7


class ResearchPlanResponse(BaseModel):
    research_question: str
    tasks: list[TaskItem]
    timeline: str
    directions: list[str]
    project_id: str | None = None


class PaperSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    max_results: int = Field(default=10, ge=1, le=50)
    project_id: str | None = None


class PaperItem(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: str | None = None
    pdf_url: str | None = None


class PaperSearchResponse(BaseModel):
    query: str
    papers: list[PaperItem]
    total: int


class PaperSummarizeRequest(BaseModel):
    arxiv_id: str | None = None
    text: str | None = None
    title: str | None = None
    project_id: str | None = None


class PaperSummaryResponse(BaseModel):
    title: str
    summary: str
    methods: list[str]
    datasets: list[str]
    innovations: list[str]
    paper_id: str | None = None


class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    topic: str = Field(..., min_length=3, max_length=2000)


class ProjectResponse(BaseModel):
    id: str
    title: str
    topic: str
    status: str
    roadmap: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Phase 2: Knowledge Graph ---

class KnowledgeIngestRequest(BaseModel):
    paper_id: str
    title: str
    methods: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    arxiv_id: str | None = None


class KnowledgeGraphResponse(BaseModel):
    paper_id: str | None = None
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    subgraph: dict[str, Any] | None = None


# --- Phase 2: Experiments ---

class ExperimentDesignRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=2000)
    project_id: str | None = None
    context: dict[str, Any] | None = None


class ExperimentDesignResponse(BaseModel):
    experiment_id: str
    hypothesis: str
    datasets: list[dict[str, str]]
    baselines: list[dict[str, str]]
    metrics: list[dict[str, str]]
    ablations: list[dict[str, Any]]
    training_config: dict[str, Any]


class ExperimentRunRequest(BaseModel):
    experiment_id: str


class ExperimentResponse(BaseModel):
    id: str
    name: str
    hypothesis: str | None
    status: str
    spec: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    mlflow_run_id: str | None = None
    code_dir: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CodeGenerateRequest(BaseModel):
    experiment_id: str
    spec: dict[str, Any]


class CodeGenerateResponse(BaseModel):
    experiment_id: str
    files: list[dict[str, str]]
    written_paths: list[str]
    experiment_dir: str


class MLflowExperimentItem(BaseModel):
    experiment_id: str
    name: str
    lifecycle_stage: str


# --- Phase 3: AI Scientist Loop ---

class ScientistRunRequest(BaseModel):
    idea: str = Field(..., min_length=3, max_length=5000)
    project_id: str | None = None


class ScientistRunResponse(BaseModel):
    run_id: str
    status: str
    current_step: str
    plan: dict[str, Any] | None = None
    experiment_spec: dict[str, Any] | None = None
    run_result: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    paper_draft: str | None = None


# --- AutoResearch (autoresearch-style) ---

class AutoResearchInitRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=2000)
    project_id: str | None = None
    hypothesis: str | None = None
    train_budget_seconds: int = Field(default=300, ge=10, le=3600)
    max_iterations: int = Field(default=12, ge=1, le=100)


class AutoResearchInitResponse(BaseModel):
    experiment_id: str
    experiment_dir: str
    program_path: str
    train_path: str
    prepare_status: str
    primary_metric: str = "val_bpb"


class AutoResearchRunRequest(BaseModel):
    max_iterations: int | None = Field(default=None, ge=1, le=100)
    train_budget_seconds: int | None = Field(default=None, ge=10, le=3600)


class AutoResearchIterationItem(BaseModel):
    iteration: int
    val_bpb: float | None = None
    kept: bool
    status: str | None = None
    best_metric: float | None = None


class AutoResearchRunResponse(BaseModel):
    experiment_id: str
    status: str
    best_metric: float | None
    primary_metric: str
    iteration_count: int
    iterations: list[AutoResearchIterationItem]
    experiment_dir: str

