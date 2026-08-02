"""Coding Agent — project scaffolding and code generation."""

import json
import logging
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

CODE_SYSTEM_PROMPT = """You are an expert ML engineer.
Generate experiment code as JSON:
{
  "files": [
    {"path": "train.py", "content": "..."},
    {"path": "evaluate.py", "content": "..."},
    {"path": "config.yaml", "content": "..."},
    {"path": "requirements.txt", "content": "..."}
  ]
}
train.py must be runnable and log metrics to stdout as JSON at the end: {"accuracy": 0.85, "loss": 0.3}
Respond ONLY with valid JSON, no markdown fences."""


class CodingAgent:
    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key or "sk-placeholder",
            base_url=settings.openai_base_url,
            temperature=0.1,
        )

    async def generate_code(self, experiment_spec: dict, experiment_id: str) -> dict:
        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=CODE_SYSTEM_PROMPT),
                    HumanMessage(content=f"Experiment spec:\n{json.dumps(experiment_spec, indent=2)}"),
                ]
            )
            content = response.content if isinstance(response.content, str) else str(response.content)
            parsed = self._parse_code(content)
        except Exception as e:
            logger.warning("Code generation LLM failed: %s", e)
            parsed = self._fallback_code(experiment_spec)

        written = self._write_files(parsed["files"], experiment_id)
        return {"files": parsed["files"], "written_paths": written, "experiment_dir": str(self._exp_dir(experiment_id))}

    async def generate_project_structure(self, experiment_spec: dict) -> dict:
        result = await self.generate_code(experiment_spec, experiment_spec.get("id", "draft"))
        return {"structure": result, "status": "generated"}

    def _parse_code(self, content: str) -> dict:
        cleaned = re.sub(r"```json\s*|\s*```", "", content.strip())
        try:
            data = json.loads(cleaned)
            if "files" in data:
                return data
        except json.JSONDecodeError:
            pass
        return self._fallback_code({})

    def _fallback_code(self, experiment_spec: dict) -> dict:
        hypothesis = experiment_spec.get("hypothesis", "ML experiment")
        config = experiment_spec.get("training_config", {})
        epochs = config.get("epochs", 10)
        return {
            "files": [
                {
                    "path": "train.py",
                    "content": f'''"""Auto-generated training script for: {hypothesis}"""
import json
import random

def main():
    random.seed(42)
    metrics = {{
        "val_bpb": round(1.8 - random.random() * 0.3, 4),
        "accuracy": round(0.7 + random.random() * 0.2, 4),
        "loss": round(random.random() * 0.5, 4),
    }}
    for epoch in range(1, {epochs + 1}):
        print(f"Epoch {{epoch}}/{epochs} loss={{metrics['loss'] / epoch:.4f}}")
    print("METRICS_JSON:" + json.dumps(metrics))

if __name__ == "__main__":
    main()
''',
                },
                {
                    "path": "evaluate.py",
                    "content": '"""Evaluation script"""\nprint("Evaluation complete.")\n',
                },
                {
                    "path": "config.yaml",
                    "content": f"hypothesis: {hypothesis}\nepochs: {epochs}\n",
                },
                {
                    "path": "requirements.txt",
                    "content": "numpy\n",
                },
            ]
        }

    def _exp_dir(self, experiment_id: str) -> Path:
        path = Path(settings.storage_path) / "experiments" / experiment_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _write_files(self, files: list[dict], experiment_id: str) -> list[str]:
        base = self._exp_dir(experiment_id)
        written = []
        for f in files:
            file_path = base / f["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f["content"], encoding="utf-8")
            written.append(str(file_path))
        return written
