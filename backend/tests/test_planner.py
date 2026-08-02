"""Planner agent tests."""

import pytest

from app.agents.planner import PlannerAgent


@pytest.mark.asyncio
async def test_planner_fallback_plan():
    agent = PlannerAgent()
    plan = agent._fallback_plan("graph neural networks")
    assert "research_question" in plan
    assert len(plan["tasks"]) >= 3
    assert plan["timeline"]
    assert len(plan["directions"]) >= 1


@pytest.mark.asyncio
async def test_planner_parse_valid_json():
    agent = PlannerAgent()
    content = '{"research_question": "Q?", "tasks": [], "timeline": "1 month", "directions": ["d1"]}'
    plan = agent._parse_plan(content, "test topic")
    assert plan["research_question"] == "Q?"
