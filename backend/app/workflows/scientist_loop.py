"""AI Scientist Loop — Idea → Experiment → AutoResearch → Analyze → Paper."""

import json
import logging
from collections.abc import AsyncIterator
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, StateGraph

from app.agents.experiment import ExperimentAgent
from app.agents.planner import PlannerAgent
from app.agents.reviewer import ReviewerAgent
from app.config import get_settings
from app.tools.experiment_prepare import run_prepare
from app.tools.experiment_template import PRIMARY_METRIC, init_experiment_workspace
from app.workflows.autoresearch_loop import iter_autoresearch_events, run_autoresearch_loop

logger = logging.getLogger(__name__)
settings = get_settings()

SCIENTIST_STEPS = ("idea", "experiment", "autoresearch", "analyze", "paper", "done")


class ScientistState(TypedDict):
    idea: str
    project_id: str | None
    run_id: str
    plan: dict
    experiment_spec: dict
    code_result: dict
    run_result: dict
    analysis: dict
    paper_draft: str
    current_step: str
    status: str


async def _idea_node(state: ScientistState) -> ScientistState:
    planner = PlannerAgent()
    plan = await planner.generate_plan(state["idea"])
    return {**state, "plan": plan, "current_step": "experiment", "status": "running"}


async def _experiment_node(state: ScientistState) -> ScientistState:
    agent = ExperimentAgent()
    spec = await agent.design_experiment(state["idea"], context=state.get("plan"))
    return {**state, "experiment_spec": spec, "current_step": "autoresearch", "status": "running"}


async def _autoresearch_node(state: ScientistState) -> ScientistState:
    exp_id = state["run_id"]
    workspace = init_experiment_workspace(
        exp_id,
        state["idea"],
        train_budget_seconds=min(settings.autoresearch_train_budget_seconds, 60),
        hypothesis=state["experiment_spec"].get("hypothesis"),
    )
    await run_prepare(workspace["prepare_path"], timeout=120)

    ar_result = await run_autoresearch_loop(
        experiment_id=exp_id,
        experiment_dir=workspace["experiment_dir"],
        topic=state["idea"],
        project_id=state["project_id"],
        max_iterations=min(3, settings.autoresearch_max_iterations),
        train_budget_seconds=min(15, settings.autoresearch_train_budget_seconds),
    )

    run_result = {
        "status": ar_result["status"],
        "metrics": {PRIMARY_METRIC: ar_result["best_metric"]},
        "autoresearch": ar_result,
    }
    code_result = {
        "experiment_dir": workspace["experiment_dir"],
        "written_paths": [workspace["train_path"]],
    }

    return {
        **state,
        "code_result": code_result,
        "run_result": run_result,
        "current_step": "analyze",
        "status": "running",
    }


async def _analyze_node(state: ScientistState) -> ScientistState:
    metrics = state["run_result"].get("metrics", {})
    ar = state["run_result"].get("autoresearch", {})
    spec = state["experiment_spec"]
    hypothesis = spec.get("hypothesis", state["idea"])

    analysis = {
        "hypothesis": hypothesis,
        "metrics": metrics,
        "autoresearch_iterations": ar.get("history", ar.get("iterations", [])),
        "best_val_bpb": ar.get("best_metric"),
        "conclusion": _build_conclusion(metrics, hypothesis, ar),
        "next_steps": [
            "Scale training budget for longer runs",
            "Compare against published baselines",
            "Export best train.py to production pipeline",
        ],
    }
    return {**state, "analysis": analysis, "current_step": "paper", "status": "running"}


async def _paper_node(state: ScientistState) -> ScientistState:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    from app.config import get_settings

    cfg = get_settings()
    context = {
        "idea": state["idea"],
        "plan": state["plan"],
        "experiment": state["experiment_spec"],
        "results": state["run_result"],
        "analysis": state["analysis"],
    }

    if cfg.llm_configured:
        llm = ChatOpenAI(
            model=cfg.openai_model,
            api_key=cfg.openai_api_key,
            base_url=cfg.openai_base_url,
            temperature=0.4,
            timeout=30,
            max_retries=1,
        )
        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(
                        content=(
                            "You are an AI researcher writing a paper draft. "
                            "Write: Abstract, Introduction, Method, Experiments, Results, Conclusion. Markdown."
                        )
                    ),
                    HumanMessage(content=f"Research context:\n{json.dumps(context, ensure_ascii=False, indent=2)[:8000]}"),
                ]
            )
            paper = response.content if isinstance(response.content, str) else str(response.content)
        except Exception as e:
            logger.warning("Paper generation failed: %s", e)
            paper = _fallback_paper(state)
    else:
        paper = _fallback_paper(state)

    reviewer = ReviewerAgent()
    review = await reviewer.review(paper[:3000])

    return {
        **state,
        "paper_draft": paper,
        "analysis": {**state["analysis"], "review": review},
        "current_step": "done",
        "status": "completed",
    }


def _build_conclusion(metrics: dict, hypothesis: str, ar: dict) -> str:
    bpb = metrics.get("val_bpb") or ar.get("best_metric")
    iters = ar.get("iteration_count", 0)
    if bpb is not None:
        return f"AutoResearch completed {iters} iterations. Best val_bpb={bpb:.4f} (lower is better)."
    return f"Experiment completed. Further validation needed for: {hypothesis}"


def _fallback_paper(state: ScientistState) -> str:
    spec = state["experiment_spec"]
    ar = state["run_result"].get("autoresearch", {})
    return f"""# Research Paper Draft

## Abstract
This paper investigates: {state['idea']}

## Introduction
{spec.get('hypothesis', '')}

## Method
AutoResearch loop (autoresearch-style): patch train.py → fixed-budget train → keep/discard by val_bpb.

## Results
Best val_bpb: {ar.get('best_metric', 'N/A')}
Iterations: {json.dumps(ar.get('history', ar.get('iterations', [])), indent=2)}

## Conclusion
{state['analysis'].get('conclusion', 'Further work needed.')}
"""


def _state_to_result(state: ScientistState) -> dict[str, Any]:
    return {
        "run_id": state["run_id"],
        "status": state["status"],
        "current_step": state["current_step"],
        "plan": state["plan"],
        "experiment_spec": state["experiment_spec"],
        "code_result": state["code_result"],
        "run_result": state["run_result"],
        "analysis": state["analysis"],
        "paper_draft": state["paper_draft"],
    }


def _initial_state(idea: str, project_id: str | None, run_id: str) -> ScientistState:
    return {
        "idea": idea,
        "project_id": project_id,
        "run_id": run_id,
        "plan": {},
        "experiment_spec": {},
        "code_result": {},
        "run_result": {},
        "analysis": {},
        "paper_draft": "",
        "current_step": "idea",
        "status": "running",
    }


async def run_scientist_loop_stream(
    idea: str,
    project_id: str | None = None,
    run_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Stream Scientist loop progress as SSE-friendly event dicts."""
    rid = run_id or str(uuid4())
    state = _initial_state(idea, project_id, rid)

    yield {"event": "run_start", "run_id": rid, "idea": idea}

    for step in ("idea", "experiment"):
        yield {"event": "step_start", "run_id": rid, "step": step}
        if step == "idea":
            state = await _idea_node(state)
        else:
            state = await _experiment_node(state)
        yield {
            "event": "step_done",
            "run_id": rid,
            "step": step,
            "current_step": state["current_step"],
        }

    yield {"event": "step_start", "run_id": rid, "step": "autoresearch"}
    exp_id = state["run_id"]
    workspace = init_experiment_workspace(
        exp_id,
        state["idea"],
        train_budget_seconds=min(settings.autoresearch_train_budget_seconds, 60),
        hypothesis=state["experiment_spec"].get("hypothesis"),
    )
    await run_prepare(workspace["prepare_path"], timeout=120)
    yield {
        "event": "autoresearch_init",
        "run_id": rid,
        "experiment_dir": workspace["experiment_dir"],
    }

    ar_result: dict[str, Any] = {}
    async for ar_event in iter_autoresearch_events(
        experiment_id=exp_id,
        experiment_dir=workspace["experiment_dir"],
        topic=state["idea"],
        project_id=state["project_id"],
        max_iterations=min(3, settings.autoresearch_max_iterations),
        train_budget_seconds=min(15, settings.autoresearch_train_budget_seconds),
    ):
        yield {"run_id": rid, **ar_event}
        if ar_event.get("event") == "autoresearch_complete":
            ar_result = {k: v for k, v in ar_event.items() if k != "event"}

    run_result = {
        "status": ar_result.get("status", "completed"),
        "metrics": {PRIMARY_METRIC: ar_result.get("best_metric")},
        "autoresearch": ar_result,
    }
    code_result = {
        "experiment_dir": workspace["experiment_dir"],
        "written_paths": [workspace["train_path"]],
    }
    state = {
        **state,
        "code_result": code_result,
        "run_result": run_result,
        "current_step": "analyze",
        "status": "running",
    }
    yield {"event": "step_done", "run_id": rid, "step": "autoresearch", "best_metric": ar_result.get("best_metric")}

    for step, node in (("analyze", _analyze_node), ("paper", _paper_node)):
        yield {"event": "step_start", "run_id": rid, "step": step}
        state = await node(state)
        yield {"event": "step_done", "run_id": rid, "step": step, "current_step": state["current_step"]}

    result = _state_to_result(state)
    yield {"event": "complete", "run_id": rid, "result": result}


def build_scientist_graph():
    graph = StateGraph(ScientistState)

    graph.add_node("idea", _idea_node)
    graph.add_node("experiment", _experiment_node)
    graph.add_node("autoresearch", _autoresearch_node)
    graph.add_node("analyze", _analyze_node)
    graph.add_node("paper", _paper_node)

    graph.set_entry_point("idea")
    graph.add_edge("idea", "experiment")
    graph.add_edge("experiment", "autoresearch")
    graph.add_edge("autoresearch", "analyze")
    graph.add_edge("analyze", "paper")
    graph.add_edge("paper", END)

    return graph.compile()


_scientist_graph = None


def get_scientist_graph():
    global _scientist_graph
    if _scientist_graph is None:
        _scientist_graph = build_scientist_graph()
    return _scientist_graph


async def run_scientist_loop(idea: str, project_id: str | None = None, run_id: str | None = None) -> dict:
    rid = run_id or str(uuid4())
    graph = get_scientist_graph()
    result = await graph.ainvoke(_initial_state(idea, project_id, rid))
    return _state_to_result(result)
