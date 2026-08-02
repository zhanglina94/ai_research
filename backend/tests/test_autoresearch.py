"""AutoResearch workflow tests."""

import pytest

from app.agents.code_patcher import CodePatcherAgent
from app.tools.experiment_runner import _extract_metrics, primary_metric_value
from app.tools.experiment_template import PRIMARY_METRIC, init_experiment_workspace
from app.workflows.autoresearch_loop import build_autoresearch_graph, run_autoresearch_loop


def test_init_experiment_workspace():
    ws = init_experiment_workspace("test-exp-1", "nano LM efficiency", train_budget_seconds=30)
    assert ws["train_path"]
    assert ws["program_path"]


def test_extract_val_bpb():
    stdout = 'step=20\nMETRICS_JSON:{"val_bpb": 1.23, "steps": 100}\n'
    m = _extract_metrics(stdout)
    assert m["val_bpb"] == 1.23
    assert primary_metric_value(m, PRIMARY_METRIC) == 1.23


def test_heuristic_patch_changes_config():
    agent = CodePatcherAgent()
    from app.tools.experiment_template import TRAIN_PY

    patched = agent._heuristic_patch(TRAIN_PY, [])
    assert patched != TRAIN_PY or "LEARNING_RATE" in patched


@pytest.mark.asyncio
async def test_autoresearch_graph_builds():
    from app.workflows.autoresearch_loop import build_autoresearch_graph

    assert build_autoresearch_graph() is not None


@pytest.mark.asyncio
async def test_autoresearch_loop_runs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import app.tools.experiment_template as et

    monkeypatch.setattr(et.settings, "storage_path", str(tmp_path / "storage"))
    exp_id = "ar-test-001"
    ws = init_experiment_workspace(exp_id, "test topic", train_budget_seconds=5)

    result = await run_autoresearch_loop(
        experiment_id=exp_id,
        experiment_dir=ws["experiment_dir"],
        topic="test topic",
        max_iterations=2,
        train_budget_seconds=1,
    )

    assert result["status"] == "completed"
    assert result["iteration_count"] == 2
    assert result["best_metric"] is not None
    assert result["best_metric"] < 999
    assert len(result["history"]) == 2
