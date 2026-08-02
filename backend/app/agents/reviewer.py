"""Reviewer Agent — simulates paper peer review (Phase 2 stub)."""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ReviewerAgent:
    """Simulates paper review across novelty, method, experiment, and writing."""

    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key or "sk-placeholder",
            base_url=settings.openai_base_url,
            temperature=0.4,
        )

    async def review(self, paper_summary: str) -> dict:
        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(
                        content=(
                            "You are a strict but fair ML paper reviewer. "
                            "Return JSON with: novelty, method, experiment, writing (each with score 1-10 and comments), "
                            "overall_recommendation (accept/weak_accept/borderline/weak_reject/reject)."
                        )
                    ),
                    HumanMessage(content=f"Paper summary:\n{paper_summary}"),
                ]
            )
            content = response.content if isinstance(response.content, str) else str(response.content)
            return {"review": content, "status": "generated"}
        except Exception as e:
            logger.warning("Reviewer agent failed: %s", e)
            return {
                "review": {
                    "novelty": {"score": 5, "comments": "Unable to assess without LLM."},
                    "method": {"score": 5, "comments": "Unable to assess without LLM."},
                    "experiment": {"score": 5, "comments": "Unable to assess without LLM."},
                    "writing": {"score": 5, "comments": "Unable to assess without LLM."},
                    "overall_recommendation": "borderline",
                },
                "status": "fallback",
            }
