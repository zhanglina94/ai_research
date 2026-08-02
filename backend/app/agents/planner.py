"""Research Planner Agent — generates research roadmap and task breakdown."""

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PLANNER_SYSTEM_PROMPT = """You are an expert AI research planner.
Given a research topic, produce a structured research plan as JSON with these fields:
- research_question: a clear, focused research question
- tasks: array of {title, description, priority (high/medium/low), estimated_days}
- timeline: overall timeline description (e.g. "3 months")
- directions: array of literature survey directions

Respond ONLY with valid JSON, no markdown fences."""


class PlannerAgent:
    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key or "sk-placeholder",
            base_url=settings.openai_base_url,
            temperature=0.3,
            timeout=20,
            max_retries=1,
        )

    async def generate_plan(self, topic: str) -> dict:
        if not settings.llm_configured:
            return self._fallback_plan(topic)
        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=PLANNER_SYSTEM_PROMPT),
                    HumanMessage(content=f"Research topic: {topic}"),
                ]
            )
            content = response.content if isinstance(response.content, str) else str(response.content)
            return self._parse_plan(content, topic)
        except Exception as e:
            logger.warning("LLM plan generation failed, using fallback: %s", e)
            return self._fallback_plan(topic)

    def _parse_plan(self, content: str, topic: str) -> dict:
        cleaned = re.sub(r"```json\s*|\s*```", "", content.strip())
        try:
            plan = json.loads(cleaned)
            required = ["research_question", "tasks", "timeline", "directions"]
            if all(k in plan for k in required):
                return plan
        except json.JSONDecodeError:
            pass
        return self._fallback_plan(topic)

    def _fallback_plan(self, topic: str) -> dict:
        return {
            "research_question": f"How can we advance {topic}?",
            "tasks": [
                {
                    "title": "Literature Review",
                    "description": f"Survey existing work on {topic}",
                    "priority": "high",
                    "estimated_days": 14,
                },
                {
                    "title": "Problem Formulation",
                    "description": "Define research problem and hypotheses",
                    "priority": "high",
                    "estimated_days": 7,
                },
                {
                    "title": "Method Design",
                    "description": "Design proposed approach and baselines",
                    "priority": "medium",
                    "estimated_days": 14,
                },
                {
                    "title": "Experiment Implementation",
                    "description": "Implement and run experiments",
                    "priority": "medium",
                    "estimated_days": 21,
                },
                {
                    "title": "Analysis & Writing",
                    "description": "Analyze results and draft paper",
                    "priority": "medium",
                    "estimated_days": 14,
                },
            ],
            "timeline": "2-3 months",
            "directions": [
                f"State-of-the-art methods in {topic}",
                f"Benchmark datasets for {topic}",
                f"Open problems in {topic}",
            ],
        }
