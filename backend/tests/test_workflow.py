"""Intent detection and workflow tests."""

from app.workflows.research_graph import _detect_intent


def test_detect_literature_intent():
    assert _detect_intent("search papers about transformers") == "literature"
    assert _detect_intent("find paper on GNN") == "literature"


def test_detect_planner_intent():
    assert _detect_intent("create a research plan for NLP") == "planner"
    assert _detect_intent("research roadmap for CV") == "planner"


def test_detect_general_intent():
    assert _detect_intent("what is attention mechanism?") == "general"
