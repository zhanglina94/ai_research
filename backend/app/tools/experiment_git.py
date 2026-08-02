"""Keep/discard experiment code snapshots via file copy."""

import json
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def init_repo(exp_dir: Path) -> None:
    """Ensure best/ directory exists (no git required)."""
    (exp_dir / "best").mkdir(parents=True, exist_ok=True)
    (exp_dir / "runs").mkdir(parents=True, exist_ok=True)
    best_train = exp_dir / "best" / "train.py"
    train = exp_dir / "train.py"
    if train.exists() and not best_train.exists():
        shutil.copy2(train, best_train)


def snapshot_train(exp_dir: Path, iteration: int) -> Path:
    runs = exp_dir / "runs" / f"iter_{iteration:03d}"
    runs.mkdir(parents=True, exist_ok=True)
    train = exp_dir / "train.py"
    dest = runs / "train.py"
    if train.exists():
        shutil.copy2(train, dest)
    return runs


def keep_train(exp_dir: Path, iteration: int) -> None:
    train = exp_dir / "train.py"
    best = exp_dir / "best" / "train.py"
    if train.exists():
        shutil.copy2(train, best)
    logger.debug("Kept train.py at iteration %s", iteration)


def discard_train(exp_dir: Path) -> None:
    best = exp_dir / "best" / "train.py"
    train = exp_dir / "train.py"
    if best.exists():
        shutil.copy2(best, train)


def save_iteration_log(exp_dir: Path, iteration: int, data: dict) -> None:
    runs = exp_dir / "runs" / f"iter_{iteration:03d}"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "metrics.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
