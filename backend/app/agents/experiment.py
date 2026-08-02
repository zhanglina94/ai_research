"""Experiment Agent — dataset selection, baseline, metrics, ablation design."""

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

EXPERIMENT_SYSTEM_PROMPT = """You are an expert ML experiment designer.
Given a research topic or hypothesis, design an experiment plan as JSON:
{
  "hypothesis": "...",
  "datasets": [{"name": "...", "reason": "..."}],
  "baselines": [{"name": "...", "description": "..."}],
  "metrics": [{"name": "...", "description": "..."}],
  "ablations": [{"name": "...", "variable": "...", "values": ["..."]}],
  "training_config": {"epochs": 10, "batch_size": 32, "lr": 0.001}
}
Respond ONLY with valid JSON, no markdown fences."""


class ExperimentAgent:
    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key or "sk-placeholder",
            base_url=settings.openai_base_url,
            temperature=0.3,
        )

    async def design_experiment(self, topic: str, context: dict | None = None) -> dict:
        user_content = f"Research topic: {topic}"
        if context:
            user_content += f"\nContext: {json.dumps(context, ensure_ascii=False)[:2000]}"

        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=EXPERIMENT_SYSTEM_PROMPT),
                    HumanMessage(content=user_content),
                ]
            )
            content = response.content if isinstance(response.content, str) else str(response.content)
            return self._parse_spec(content, topic)
        except Exception as e:
            logger.warning("Experiment design LLM failed: %s", e)
            return self._fallback_spec(topic)

    def _parse_spec(self, content: str, topic: str) -> dict:
        cleaned = re.sub(r"```json\s*|\s*```", "", content.strip())
        try:
            spec = json.loads(cleaned)
            required = ["hypothesis", "datasets", "baselines", "metrics", "ablations"]
            if all(k in spec for k in required):
                spec.setdefault("training_config", {"epochs": 10, "batch_size": 32, "lr": 0.001})
                return spec
        except json.JSONDecodeError:
            pass
        return self._fallback_spec(topic)

    def _fallback_spec(self, topic: str) -> dict:
        return {
            "hypothesis": f"A novel approach can improve performance on {topic}",
            "datasets": [{"name": "Standard Benchmark", "reason": f"Common evaluation for {topic}"}],
            "baselines": [
                {"name": "Vanilla Baseline", "description": "Standard baseline method"},
                {"name": "SOTA Reference", "description": "Current state-of-the-art comparison"},
            ],
            "metrics": [
                {"name": "Accuracy", "description": "Primary evaluation metric"},
                {"name": "F1 Score", "description": "Balanced precision-recall"},
            ],
            "ablations": [
                {"name": "Component Ablation", "variable": "key_module", "values": ["on", "off"]},
            ],
            "training_config": {"epochs": 10, "batch_size": 32, "lr": 0.001},
        }
