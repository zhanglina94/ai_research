"""Safe local or Docker-isolated experiment runner."""

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def run_experiment_script(
    script_path: str,
    timeout: int = 120,
    train_budget_seconds: int | None = 300,
    iteration: int | None = None,
) -> dict:
    """Run train.py (or prepare.py) locally or in Docker sandbox."""
    path = Path(script_path).resolve()
    if not path.exists():
        return {"status": "failed", "error": f"Script not found: {script_path}"}

    use_docker = settings.experiment_use_docker and path.name == "train.py"
    if use_docker:
        from app.tools.experiment_docker import run_in_docker_sandbox

        result = await run_in_docker_sandbox(
            path.parent,
            script_name=path.name,
            timeout=timeout,
            train_budget_seconds=train_budget_seconds,
            use_gpu=settings.experiment_use_gpu,
        )
        if log_path := _log_path(path, iteration):
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(
                result.get("stdout", "") + "\n--- stderr ---\n" + result.get("stderr", ""),
                encoding="utf-8",
            )
        return result

    env = os.environ.copy()
    if train_budget_seconds is not None:
        env["TRAIN_BUDGET_SECONDS"] = str(train_budget_seconds)
    if iteration is not None:
        env["AR_ITERATION"] = str(iteration)
    env["AR_TRAINING_MODE"] = settings.experiment_training_mode
    env["AR_USE_GPU"] = "1" if settings.experiment_use_gpu else "0"

    log_path = _log_path(path, iteration)

    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(path.parent),
            env=env,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        metrics = _extract_metrics(stdout)

        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(stdout + "\n--- stderr ---\n" + stderr, encoding="utf-8")

        return {
            "status": "completed" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "stdout": stdout[-2000:],
            "stderr": stderr[-1000:],
            "metrics": metrics,
            "train_budget_seconds": train_budget_seconds,
            "runner": "local",
            "training_mode": settings.experiment_training_mode,
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": f"Exceeded {timeout}s", "metrics": {}, "runner": "local"}
    except Exception as e:
        logger.error("Experiment run failed: %s", e)
        return {"status": "failed", "error": str(e), "metrics": {}, "runner": "local"}


def _log_path(path: Path, iteration: int | None) -> Path | None:
    if iteration is None:
        return None
    return path.parent / "runs" / f"iter_{iteration:03d}" / "stdout.log"


def _extract_metrics(stdout: str) -> dict:
    match = re.search(r"METRICS_JSON:(\{.*\})", stdout)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return {}


def primary_metric_value(metrics: dict, metric_name: str = "val_bpb") -> float | None:
    if metric_name in metrics:
        try:
            return float(metrics[metric_name])
        except (TypeError, ValueError):
            return None
    return None


def experiment_runtime_info() -> dict:
    """Return GPU / Docker / training mode info for API consumers."""
    from app.tools.experiment_docker import docker_available
    from app.tools.gpu_utils import detect_gpu

    gpu = detect_gpu()
    return {
        "training_mode": settings.experiment_training_mode,
        "use_gpu": settings.experiment_use_gpu,
        "use_docker": settings.experiment_use_docker,
        "docker_available": docker_available(),
        "docker_image": settings.experiment_docker_image,
        "gpu": gpu,
    }
