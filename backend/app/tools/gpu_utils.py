"""GPU detection for experiment training."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def detect_gpu() -> dict:
    """Return GPU availability and device info."""
    info: dict = {
        "available": False,
        "device": "cpu",
        "device_name": None,
        "cuda_version": None,
        "torch_available": False,
    }
    try:
        import torch

        info["torch_available"] = True
        if torch.cuda.is_available():
            info["available"] = True
            info["device"] = "cuda"
            info["device_name"] = torch.cuda.get_device_name(0)
            info["cuda_version"] = torch.version.cuda
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            info["available"] = True
            info["device"] = "mps"
            info["device_name"] = "Apple MPS"
    except ImportError:
        logger.debug("PyTorch not installed — GPU training unavailable")
    except Exception as e:
        logger.debug("GPU detection failed: %s", e)
    return info


def resolve_training_device(use_gpu: bool = True) -> str:
    """Pick device string for nanochat training."""
    if not use_gpu:
        return "cpu"
    gpu = detect_gpu()
    return gpu["device"] if gpu["available"] else "cpu"
