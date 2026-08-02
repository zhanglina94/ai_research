"""AutoResearch experiment directory templates (autoresearch-style)."""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings

settings = get_settings()
PRIMARY_METRIC = "val_bpb"


def program_md(topic: str, train_budget_seconds: int = 300) -> str:
    return f"""# Research Program — {topic}

## Goal
Optimize language-model training for **{topic}** under a fixed compute budget.

## Rules (autoresearch-style)
- **Editable file:** `train.py` only
- **Fixed files:** `prepare.py`, `program.md` (do not modify)
- **Training budget:** {train_budget_seconds}s wall-clock per iteration
- **Primary metric:** `{PRIMARY_METRIC}` — **lower is better**
- **Decision:** keep changes only if `{PRIMARY_METRIC}` improves vs best so far

## Hints for the agent
- Tune `LEARNING_RATE`, `HIDDEN_DIM`, `DEPTH` in the AR_CONFIG block
- Prefer stable improvements over large risky changes
- If a run fails, fix errors before tuning hyperparameters
"""


PREPARE_PY = '''"""Fixed data prep — do not modify (autoresearch prepare.py analogue)."""
import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
MANIFEST = DATA_DIR / "manifest.json"
TRAIN_PATH = DATA_DIR / "train_tokens.json"
VAL_PATH = DATA_DIR / "val_tokens.json"

VOCAB_SIZE = 4096
SEQ_LEN = 64
N_TRAIN = 512
N_VAL = 64


def _generate_sequences(n: int, vocab: int, seq_len: int) -> list[list[int]]:
    random.seed(42)
    return [[random.randint(0, vocab - 1) for _ in range(seq_len)] for _ in range(n)]


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    train = _generate_sequences(N_TRAIN, VOCAB_SIZE, SEQ_LEN)
    val = _generate_sequences(N_VAL, VOCAB_SIZE, SEQ_LEN)
    TRAIN_PATH.write_text(json.dumps(train), encoding="utf-8")
    VAL_PATH.write_text(json.dumps(val), encoding="utf-8")
    manifest = {
        "status": "ready",
        "vocab_size": VOCAB_SIZE,
        "seq_len": SEQ_LEN,
        "train_sequences": N_TRAIN,
        "val_sequences": N_VAL,
        "train_tokens": N_TRAIN * SEQ_LEN,
        "val_tokens": N_VAL * SEQ_LEN,
        "note": "Synthetic token sequences for nanochat-style LM training",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("PREPARE_OK")


if __name__ == "__main__":
    main()
'''


TRAIN_PY = '''"""Agent-editable training script — autoresearch train.py analogue."""
# --- AR_CONFIG (agent editable) ---
LEARNING_RATE = 1e-3
HIDDEN_DIM = 128
DEPTH = 4
# --- END AR_CONFIG ---

import json
import math
import os
import random
import time


def main() -> None:
    budget = int(os.environ.get("TRAIN_BUDGET_SECONDS", "300"))
    random.seed(42)
    start = time.time()
    step = 0
    best_bpb = 999.0

    lr_factor = math.log10(max(LEARNING_RATE, 1e-6) * 1000)
    arch_factor = HIDDEN_DIM / 512.0 + DEPTH / 16.0

    while time.time() - start < budget:
        step += 1
        noise = random.random() * 0.08
        val_bpb = 2.8 - lr_factor * 0.15 - arch_factor * 0.25 + noise
        val_bpb = max(0.45, val_bpb)
        best_bpb = min(best_bpb, val_bpb)
        if step % 20 == 0:
            elapsed = time.time() - start
            print(f"step={step} elapsed={elapsed:.1f}s val_bpb={val_bpb:.4f}")
        time.sleep(min(0.005, max(budget / 1000, 0.001)))

    metrics = {
        "val_bpb": round(best_bpb, 4),
        "steps": step,
        "learning_rate": LEARNING_RATE,
        "hidden_dim": HIDDEN_DIM,
        "depth": DEPTH,
    }
    print("METRICS_JSON:" + json.dumps(metrics))


if __name__ == "__main__":
    main()
'''


TRAIN_NANOCHAT_PY = '''"""Agent-editable nanochat-style LM training — autoresearch train.py analogue."""
# --- AR_CONFIG (agent editable) ---
LEARNING_RATE = 1e-3
HIDDEN_DIM = 128
DEPTH = 4
# --- END AR_CONFIG ---

import json
import math
import os
import random
import time
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
MANIFEST = DATA_DIR / "manifest.json"


def _mock_train(budget: int) -> dict:
    random.seed(42)
    start = time.time()
    step = 0
    best_bpb = 999.0
    lr_factor = math.log10(max(LEARNING_RATE, 1e-6) * 1000)
    arch_factor = HIDDEN_DIM / 512.0 + DEPTH / 16.0
    while time.time() - start < budget:
        step += 1
        noise = random.random() * 0.08
        val_bpb = 2.8 - lr_factor * 0.15 - arch_factor * 0.25 + noise
        val_bpb = max(0.45, val_bpb)
        best_bpb = min(best_bpb, val_bpb)
        if step % 20 == 0:
            print(f"step={step} elapsed={time.time()-start:.1f}s val_bpb={val_bpb:.4f} mode=mock")
        time.sleep(min(0.005, max(budget / 1000, 0.001)))
    return {"val_bpb": round(best_bpb, 4), "steps": step, "mode": "mock"}


def _nanochat_train(budget: int) -> dict:
    import torch
    import torch.nn as nn

    use_gpu = os.environ.get("AR_USE_GPU", "0") == "1"
    if use_gpu and torch.cuda.is_available():
        device = torch.device("cuda")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available() and use_gpu:
        device = torch.device("mps")
    else:
        device = torch.device("cpu")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    vocab = manifest["vocab_size"]
    seq_len = manifest["seq_len"]

    train_tokens = json.loads((DATA_DIR / "train_tokens.json").read_text(encoding="utf-8"))
    val_tokens = json.loads((DATA_DIR / "val_tokens.json").read_text(encoding="utf-8"))
    x_train = torch.tensor(train_tokens, dtype=torch.long, device=device)
    x_val = torch.tensor(val_tokens, dtype=torch.long, device=device)

    class TinyLM(nn.Module):
        def __init__(self, vocab_size: int, hidden: int, depth: int):
            super().__init__()
            self.embed = nn.Embedding(vocab_size, hidden)
            layers = []
            for _ in range(depth):
                layers.extend([nn.Linear(hidden, hidden * 4), nn.GELU(), nn.Linear(hidden * 4, hidden)])
            self.blocks = nn.Sequential(*layers)
            self.head = nn.Linear(hidden, vocab_size)

        def forward(self, x):
            h = self.embed(x)
            h = self.blocks(h)
            return self.head(h)

        def bpb(self, logits, targets):
            loss = nn.functional.cross_entropy(logits.view(-1, vocab), targets.view(-1))
            return (loss / math.log(2)).item()

    model = TinyLM(vocab, HIDDEN_DIM, DEPTH).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)

    start = time.time()
    step = 0
    best_bpb = 999.0
    batch = min(32, x_train.size(0))

    while time.time() - start < budget:
        idx = torch.randint(0, x_train.size(0), (batch,), device=device)
        batch_x = x_train[idx]
        inp, tgt = batch_x[:, :-1], batch_x[:, 1:]
        logits = model(inp)
        loss = nn.functional.cross_entropy(logits.reshape(-1, vocab), tgt.reshape(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        step += 1

        if step % 10 == 0:
            with torch.no_grad():
                v_idx = torch.arange(min(16, x_val.size(0)), device=device)
                v_inp, v_tgt = x_val[v_idx, :-1], x_val[v_idx, 1:]
                v_logits = model(v_inp)
                val_bpb = model.bpb(v_logits, v_tgt)
                best_bpb = min(best_bpb, val_bpb)
                print(
                    f"step={step} elapsed={time.time()-start:.1f}s val_bpb={val_bpb:.4f} "
                    f"device={device.type} mode=nanochat"
                )

    with torch.no_grad():
        v_idx = torch.arange(min(16, x_val.size(0)), device=device)
        v_inp, v_tgt = x_val[v_idx, :-1], x_val[v_idx, 1:]
        v_logits = model(v_inp)
        final_bpb = model.bpb(v_logits, v_tgt)
        best_bpb = min(best_bpb, final_bpb)

    return {
        "val_bpb": round(best_bpb, 4),
        "steps": step,
        "mode": "nanochat",
        "device": device.type,
        "learning_rate": LEARNING_RATE,
        "hidden_dim": HIDDEN_DIM,
        "depth": DEPTH,
    }


def main() -> None:
    budget = int(os.environ.get("TRAIN_BUDGET_SECONDS", "300"))
    mode = os.environ.get("AR_TRAINING_MODE", "nanochat").lower()
    try:
        if mode == "nanochat":
            metrics = _nanochat_train(budget)
        else:
            metrics = _mock_train(budget)
    except Exception as exc:
        print(f"NANOCHAT_FALLBACK: {exc}")
        metrics = _mock_train(budget)
        metrics["fallback_reason"] = str(exc)[:200]
    metrics.setdefault("learning_rate", LEARNING_RATE)
    metrics.setdefault("hidden_dim", HIDDEN_DIM)
    metrics.setdefault("depth", DEPTH)
    print("METRICS_JSON:" + json.dumps(metrics))


if __name__ == "__main__":
    main()
'''


def default_train_template() -> str:
    mode = settings.experiment_training_mode.lower()
    if mode == "nanochat":
        return TRAIN_NANOCHAT_PY
    return TRAIN_PY


def experiment_dir(experiment_id: str) -> Path:
    path = Path(settings.storage_path) / "experiments" / experiment_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def init_experiment_workspace(
    experiment_id: str,
    topic: str,
    train_budget_seconds: int = 300,
    hypothesis: str | None = None,
) -> dict:
    """Create autoresearch-style workspace with program.md, prepare.py, train.py."""
    base = experiment_dir(experiment_id)
    runs = base / "runs"
    best = base / "best"
    runs.mkdir(exist_ok=True)
    best.mkdir(exist_ok=True)

    program_path = base / "program.md"
    prepare_path = base / "prepare.py"
    train_path = base / "train.py"

    train_template = default_train_template()
    program_path.write_text(program_md(topic, train_budget_seconds), encoding="utf-8")
    prepare_path.write_text(PREPARE_PY, encoding="utf-8")
    train_path.write_text(train_template, encoding="utf-8")
    (best / "train.py").write_text(train_template, encoding="utf-8")

    return {
        "experiment_dir": str(base),
        "program_path": str(program_path),
        "prepare_path": str(prepare_path),
        "train_path": str(train_path),
        "runs_dir": str(runs),
        "best_dir": str(best),
        "hypothesis": hypothesis or topic,
        "train_budget_seconds": train_budget_seconds,
        "primary_metric": PRIMARY_METRIC,
    }
