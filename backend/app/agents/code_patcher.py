"""Code Patcher Agent — modifies train.py only (autoresearch-style)."""

import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PATCH_SYSTEM = """You are an ML research agent in autoresearch mode.
You may ONLY edit the AR_CONFIG section and training logic in train.py.
Respond with the COMPLETE updated train.py file content only — no markdown fences."""


class CodePatcherAgent:
    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key or "sk-placeholder",
            base_url=settings.openai_base_url,
            temperature=0.2,
            timeout=30,
            max_retries=1,
        )

    async def patch_train(
        self,
        train_code: str,
        program_md: str,
        history: list[dict],
        stderr: str = "",
    ) -> str:
        if settings.llm_configured:
            try:
                hist_text = "\n".join(
                    f"iter {h.get('iteration')}: val_bpb={h.get('val_bpb')} kept={h.get('kept')}"
                    for h in history[-6:]
                )
                response = await self.llm.ainvoke(
                    [
                        SystemMessage(content=PATCH_SYSTEM),
                        HumanMessage(
                            content=(
                                f"Program:\n{program_md[:2000]}\n\n"
                                f"Recent iterations:\n{hist_text}\n\n"
                                f"Last stderr:\n{stderr[:1000]}\n\n"
                                f"Current train.py:\n{train_code[:6000]}"
                            )
                        ),
                    ]
                )
                content = response.content if isinstance(response.content, str) else str(response.content)
                cleaned = re.sub(r"^```(?:python)?\s*|\s*```$", "", content.strip())
                if "AR_CONFIG" in cleaned and "def main" in cleaned:
                    return cleaned
            except Exception as e:
                logger.warning("LLM patch failed, using heuristic: %s", e)

        return self._heuristic_patch(train_code, history)

    def _heuristic_patch(self, train_code: str, history: list[dict]) -> str:
        """Deterministic patch for demo / offline mode."""
        lr_match = re.search(r"LEARNING_RATE\s*=\s*([0-9.eE+-]+)", train_code)
        dim_match = re.search(r"HIDDEN_DIM\s*=\s*(\d+)", train_code)
        depth_match = re.search(r"DEPTH\s*=\s*(\d+)", train_code)

        lr = float(lr_match.group(1)) if lr_match else 1e-3
        dim = int(dim_match.group(1)) if dim_match else 128
        depth = int(depth_match.group(1)) if depth_match else 4

        last_kept = next((h for h in reversed(history) if h.get("kept")), None)
        if last_kept is None or not history:
            lr *= 1.5
            dim = min(dim + 32, 512)
        elif history[-1].get("kept"):
            depth = min(depth + 1, 12)
        else:
            lr *= 0.7
            dim = max(dim - 16, 64)

        code = train_code
        code = re.sub(r"LEARNING_RATE\s*=\s*[0-9.eE+-]+", f"LEARNING_RATE = {lr:.6g}", code)
        code = re.sub(r"HIDDEN_DIM\s*=\s*\d+", f"HIDDEN_DIM = {dim}", code)
        code = re.sub(r"DEPTH\s*=\s*\d+", f"DEPTH = {depth}", code)
        return code
