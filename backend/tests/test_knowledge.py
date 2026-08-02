"""Knowledge Graph API tests."""

from app.agents.knowledge_graph import KnowledgeGraphAgent


def test_knowledge_graph_agent_init():
    agent = KnowledgeGraphAgent()
    assert agent.store is not None


def test_get_full_graph_degraded():
    agent = KnowledgeGraphAgent()
    graph = agent.get_full_graph()
    assert "nodes" in graph
    assert "edges" in graph
