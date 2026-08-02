"""Tests for GPU, Docker sandbox routing, and Scientist streaming."""

import pytest

from app.tools.experiment_docker import docker_available
from app.tools.experiment_runner import experiment_runtime_info
from app.tools.experiment_template import TRAIN_NANOCHAT_PY, default_train_template, init_experiment_workspace
from app.tools.gpu_utils import detect_gpu, resolve_training_device
from app.workflows.scientist_loop import run_scientist_loop_stream


def test_detect_gpu_returns_dict():
    info = detect_gpu()
    assert "available" in info
    assert "device" in info
    assert info["device"] in ("cpu", "cuda", "mps")


def test_resolve_training_device_cpu_when_disabled():
    assert resolve_training_device(use_gpu=False) == "cpu"


def test_default_train_template_mock():
    import app.tools.experiment_template as et

    original = et.settings.experiment_training_mode
    et.settings.experiment_training_mode = "mock"
    try:
        tpl = default_train_template()
        assert "mock" in tpl or "random" in tpl
    finally:
        et.settings.experiment_training_mode = original


def test_default_train_template_nanochat():
    import app.tools.experiment_template as et

    original = et.settings.experiment_training_mode
    et.settings.experiment_training_mode = "nanochat"
    try:
        tpl = default_train_template()
        assert tpl == TRAIN_NANOCHAT_PY
    finally:
        et.settings.experiment_training_mode = original


def test_experiment_runtime_info():
    info = experiment_runtime_info()
    assert "training_mode" in info
    assert "docker_available" in info
    assert isinstance(docker_available(), bool)


@pytest.mark.asyncio
async def test_scientist_stream_emits_events(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import app.tools.experiment_template as et

    monkeypatch.setattr(et.settings, "storage_path", str(tmp_path / "storage"))

    events = []
    async for event in run_scientist_loop_stream("test streaming idea"):
        events.append(event)
        if len(events) > 200:
            break

    event_types = {e.get("event") for e in events}
    assert "run_start" in event_types
    assert "step_start" in event_types
    assert "complete" in event_types or "iteration_done" in event_types
