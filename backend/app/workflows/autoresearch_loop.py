"""AutoResearch loop — patch train.py → run → evaluate → keep/discard → repeat."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any

from app.agents.code_patcher import CodePatcherAgent
from app.tools.experiment_git import (
    discard_train,
    init_repo,
    keep_train,
    save_iteration_log,
    snapshot_train,
)
from app.tools.experiment_runner import primary_metric_value, run_experiment_script
from app.tools.experiment_template import PRIMARY_METRIC

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


async def _emit(callback: ProgressCallback | None, event: dict[str, Any]) -> None:
    if callback is None:
        return
    result = callback(event)
    if asyncio.iscoroutine(result):
        await result


async def iter_autoresearch_events(
    experiment_id: str,
    experiment_dir: str,
    topic: str,
    project_id: str | None = None,
    max_iterations: int = 5,
    train_budget_seconds: int = 30,
    on_progress: ProgressCallback | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield iteration-level progress events; final event is autoresearch_complete."""
    exp_path = Path(experiment_dir)
    init_repo(exp_path)

    train_path = exp_path / "train.py"
    program_path = exp_path / "program.md"
    program_md = program_path.read_text(encoding="utf-8") if program_path.exists() else ""

    best_metric: float | None = None
    history: list[dict] = []
    patcher = CodePatcherAgent()

    await _emit(
        on_progress,
        {
            "event": "autoresearch_start",
            "experiment_id": experiment_id,
            "max_iterations": max_iterations,
            "train_budget_seconds": train_budget_seconds,
        },
    )

    for iteration in range(max_iterations):
        await _emit(
            on_progress,
            {"event": "iteration_start", "iteration": iteration, "experiment_id": experiment_id},
        )

        train_code = train_path.read_text(encoding="utf-8") if train_path.exists() else ""

        if iteration > 0:
            stderr = history[-1].get("stderr", "") if history else ""
            patched = await patcher.patch_train(train_code, program_md, history, stderr)
            train_path.write_text(patched, encoding="utf-8")
            await _emit(
                on_progress,
                {"event": "iteration_patched", "iteration": iteration, "experiment_id": experiment_id},
            )

        snapshot_train(exp_path, iteration)

        run_result = await run_experiment_script(
            str(train_path.resolve()),
            timeout=train_budget_seconds + 60,
            train_budget_seconds=train_budget_seconds,
            iteration=iteration,
        )

        metrics = run_result.get("metrics", {})
        value = primary_metric_value(metrics, PRIMARY_METRIC)
        run_ok = run_result.get("status") == "completed" and value is not None

        kept = False
        if run_ok and (best_metric is None or value < best_metric):
            keep_train(exp_path, iteration)
            kept = True
            best_metric = value
        else:
            discard_train(exp_path)

        from app.tools.mlflow_client import get_mlflow_client

        mlflow = get_mlflow_client()
        try:
            await asyncio.wait_for(
                asyncio.to_thread(
                    mlflow.log_run,
                    f"autoresearch-{project_id or 'default'}",
                    f"{experiment_id}-iter-{iteration:03d}",
                    {"iteration": iteration, "train_budget_seconds": train_budget_seconds, "kept": kept},
                    {PRIMARY_METRIC: float(value)} if value is not None else {},
                    {"experiment_id": experiment_id, "topic": topic[:120]},
                    {"train.py": str(train_path)},
                ),
                timeout=3,
            )
        except Exception as e:
            logger.debug("MLflow log skipped: %s", e)

        record = {
            "iteration": iteration,
            PRIMARY_METRIC: value,
            "kept": kept,
            "status": run_result.get("status"),
            "best_metric": best_metric,
            "stderr": run_result.get("stderr", ""),
            "runner": run_result.get("runner"),
            "training_mode": run_result.get("training_mode") or metrics.get("mode"),
        }
        history.append(record)
        save_iteration_log(exp_path, iteration, {**record, "metrics": metrics})

        done_event = {
            "event": "iteration_done",
            "iteration": iteration,
            "experiment_id": experiment_id,
            PRIMARY_METRIC: value,
            "kept": kept,
            "status": run_result.get("status"),
            "best_metric": best_metric,
        }
        await _emit(on_progress, done_event)
        yield done_event

    complete = {
        "event": "autoresearch_complete",
        "experiment_id": experiment_id,
        "status": "completed",
        "best_metric": best_metric,
        "primary_metric": PRIMARY_METRIC,
        "history": history,
        "iteration_count": len(history),
        "experiment_dir": experiment_dir,
    }
    await _emit(on_progress, complete)
    yield complete


async def run_autoresearch_loop(
    experiment_id: str,
    experiment_dir: str,
    topic: str,
    project_id: str | None = None,
    max_iterations: int = 5,
    train_budget_seconds: int = 30,
    on_progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    final: dict[str, Any] | None = None
    async for event in iter_autoresearch_events(
        experiment_id,
        experiment_dir,
        topic,
        project_id=project_id,
        max_iterations=max_iterations,
        train_budget_seconds=train_budget_seconds,
        on_progress=on_progress,
    ):
        if event.get("event") == "autoresearch_complete":
            final = event

    if final is None:
        return {"experiment_id": experiment_id, "status": "failed", "history": []}

    return {k: v for k, v in final.items() if k != "event"}


def build_autoresearch_graph():
    """Compatibility shim for tests — loop is implemented imperatively."""
    return object()
