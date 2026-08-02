"""LangGraph research workflow orchestration."""

import logging
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.literature import LiteratureAgent
from app.agents.planner import PlannerAgent

logger = logging.getLogger(__name__)


class ResearchState(TypedDict):
    message: str
    history: list[dict]
    project_id: str | None
    intent: str
    reply: str
    agent: str
    metadata: dict[str, Any]


def _detect_intent(message: str) -> str:
    lower = message.lower()
    if any(kw in lower for kw in ("search paper", "find paper", "arxiv", "literature", "论文", "文献")):
        return "literature"
    if any(
        kw in lower
        for kw in (
            "plan",
            "roadmap",
            "research plan",
            "规划",
            "路线",
            "计划",
            "深度研究",
            "深度调研",
            "deep research",
        )
    ):
        return "planner"
    return "general"


async def _planner_node(state: ResearchState) -> ResearchState:
    agent = PlannerAgent()
    plan = await agent.generate_plan(state["message"])
    reply = (
        f"**Research Question:** {plan['research_question']}\n\n"
        f"**Timeline:** {plan['timeline']}\n\n"
        f"**Tasks:**\n"
        + "\n".join(f"- {t['title']}: {t['description']}" for t in plan["tasks"])
        + f"\n\n**Survey Directions:**\n"
        + "\n".join(f"- {d}" for d in plan["directions"])
    )
    return {**state, "reply": reply, "agent": "planner", "metadata": plan}


async def _literature_node(state: ResearchState) -> ResearchState:
    agent = LiteratureAgent()
    query = state["message"]
    for prefix in ("search paper", "find paper", "search papers about", "search "):
        if query.lower().startswith(prefix):
            query = query[len(prefix) :].strip()
            break

    papers = await agent.search_papers(query, max_results=5)
    if not papers:
        return {**state, "reply": "No papers found. Try a different query.", "agent": "literature"}

    lines = [f"Found {len(papers)} papers for '{query}':\n"]
    for i, p in enumerate(papers, 1):
        lines.append(f"{i}. **{p['title']}** ({p['arxiv_id']})")
        lines.append(f"   Authors: {', '.join(p['authors'][:3])}")
        lines.append(f"   {p['abstract'][:200]}...\n")

    return {**state, "reply": "\n".join(lines), "agent": "literature", "metadata": {"papers": papers}}


def _offline_reply() -> str:
    return (
        "我是 AI Research OS 助手，可以帮你：\n"
        "- 生成研究规划（试试：「为 Transformer 效率优化制定研究计划」）\n"
        "- 检索论文（试试：「搜索 transformer efficiency 相关论文」）\n"
        "- 讨论研究思路\n\n"
        "请在 `.env` 中配置有效的 `OPENAI_API_KEY` 以启用完整 LLM 能力。"
    )


async def _general_node(state: ResearchState) -> ResearchState:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    from app.config import get_settings

    cfg = get_settings()
    if not cfg.llm_configured:
        return {**state, "reply": _offline_reply(), "agent": "general", "metadata": {}}

    llm = ChatOpenAI(
        model=cfg.openai_model,
        api_key=cfg.openai_api_key or "sk-placeholder",
        base_url=cfg.openai_base_url,
        timeout=20,
        max_retries=1,
    )

    messages = [
        SystemMessage(
            content=(
                "You are AI Research OS, an intelligent research assistant. "
                "Help with research planning, literature review, experiment design, and analysis. "
                "Be concise and actionable."
            )
        )
    ]
    for msg in state["history"][-6:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    try:
        response = await llm.ainvoke(messages)
        reply = response.content if isinstance(response.content, str) else str(response.content)
    except Exception as e:
        logger.warning("General chat LLM failed: %s", e)
        reply = _offline_reply()

    return {**state, "reply": reply, "agent": "general", "metadata": {}}


def _route_intent(state: ResearchState) -> str:
    return state["intent"]


def build_research_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("router", lambda state: {**state, "intent": _detect_intent(state["message"])})
    graph.add_node("planner", _planner_node)
    graph.add_node("literature", _literature_node)
    graph.add_node("general", _general_node)

    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        _route_intent,
        {"planner": "planner", "literature": "literature", "general": "general"},
    )
    graph.add_edge("planner", END)
    graph.add_edge("literature", END)
    graph.add_edge("general", END)

    return graph.compile()


_research_graph = None


def get_research_graph():
    global _research_graph
    if _research_graph is None:
        _research_graph = build_research_graph()
    return _research_graph


async def run_research_chat(
    message: str,
    history: list[dict],
    project_id: str | None = None,
) -> dict:
    graph = get_research_graph()
    result = await graph.ainvoke(
        {
            "message": message,
            "history": history,
            "project_id": project_id,
            "intent": "",
            "reply": "",
            "agent": "",
            "metadata": {},
        }
    )
    return {"reply": result["reply"], "agent": result["agent"], "metadata": result.get("metadata")}
