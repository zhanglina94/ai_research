"""One-time experiment prepare step."""

import logging

from app.tools.experiment_runner import run_experiment_script

logger = logging.getLogger(__name__)


async def run_prepare(prepare_script: str, timeout: int = 120) -> dict:
    result = await run_experiment_script(prepare_script, timeout=timeout, train_budget_seconds=None)
    if result.get("status") == "completed":
        result["prepared"] = True
    else:
        logger.warning("Prepare step failed: %s", result)
        result["prepared"] = False
    return result
