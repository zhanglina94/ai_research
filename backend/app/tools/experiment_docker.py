"""Run experiments inside an isolated Docker container."""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def docker_available() -> bool:
    return shutil.which("docker") is not None


async def run_in_docker_sandbox(
    experiment_dir: Path,
    script_name: str = "train.py",
    timeout: int = 420,
    train_budget_seconds: int | None = 300,
    use_gpu: bool = False,
) -> dict:
    """Execute train.py in Docker with workspace volume mount and no network."""
    if not docker_available():
        return {"status": "failed", "error": "Docker CLI not available", "runner": "docker"}

    exp_dir = experiment_dir.resolve()
    image = settings.experiment_docker_image

    env_args: list[str] = []
    if train_budget_seconds is not None:
        env_args.extend(["-e", f"TRAIN_BUDGET_SECONDS={train_budget_seconds}"])
    env_args.extend(["-e", f"AR_TRAINING_MODE={settings.experiment_training_mode}"])
    env_args.extend(["-e", f"AR_USE_GPU={'1' if use_gpu else '0'}"])

    cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--memory",
        settings.experiment_docker_memory,
        "-v",
        f"{exp_dir}:/workspace",
        "-w",
        "/workspace",
        *env_args,
    ]

    if use_gpu and settings.experiment_use_gpu:
        cmd.insert(3, "--gpus")
        cmd.insert(4, "all")

    cmd.extend([image, "python", script_name])

    try:
        proc = await asyncio.to_thread(
            __import__("subprocess").run,
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        from app.tools.experiment_runner import _extract_metrics

        metrics = _extract_metrics(stdout)
        return {
            "status": "completed" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "stdout": stdout[-2000:],
            "stderr": stderr[-1000:],
            "metrics": metrics,
            "runner": "docker",
            "image": image,
        }
    except __import__("subprocess").TimeoutExpired:
        return {"status": "timeout", "error": f"Docker exceeded {timeout}s", "runner": "docker"}
    except Exception as e:
        logger.error("Docker sandbox run failed: %s", e)
        return {"status": "failed", "error": str(e), "runner": "docker"}
