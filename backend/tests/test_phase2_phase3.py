"""Phase 2 & 3 agent and workflow tests."""

import pytest

from app.agents.experiment import ExperimentAgent
from app.agents.coding import CodingAgent
from app.tools.experiment_runner import _extract_metrics


def test_experiment_fallback_spec():
    agent = ExperimentAgent()
    spec = agent._fallback_spec("graph neural networks")
    assert "hypothesis" in spec
    assert len(spec["baselines"]) >= 2
    assert len(spec["ablations"]) >= 1


def test_coding_fallback_generates_train_py():
    agent = CodingAgent()
    code = agent._fallback_code({"hypothesis": "test", "training_config": {"epochs": 3}})
    paths = [f["path"] for f in code["files"]]
    assert "train.py" in paths
    train_content = next(f["content"] for f in code["files"] if f["path"] == "train.py")
    assert "METRICS_JSON" in train_content


def test_extract_metrics_from_stdout():
    stdout = "Training...\nMETRICS_JSON:{\"accuracy\": 0.91, \"loss\": 0.12}\n"
    metrics = _extract_metrics(stdout)
    assert metrics["accuracy"] == 0.91


@pytest.mark.asyncio
async def test_scientist_graph_builds():
    from app.workflows.scientist_loop import build_scientist_graph

    graph = build_scientist_graph()
    assert graph is not None
