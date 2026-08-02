"""Knowledge Graph API."""

from fastapi import APIRouter, Query

from app.agents.knowledge_graph import KnowledgeGraphAgent
from app.api.schemas import KnowledgeGraphResponse, KnowledgeIngestRequest

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/ingest")
async def ingest_knowledge(request: KnowledgeIngestRequest) -> dict:
    agent = KnowledgeGraphAgent()
    results = agent.ingest_paper_knowledge(
        paper_id=request.paper_id,
        title=request.title,
        methods=request.methods,
        datasets=request.datasets,
        arxiv_id=request.arxiv_id,
    )
    for model in request.models:
        agent.link_model(request.paper_id, model)
    return {"paper_id": request.paper_id, "results": results}


@router.get("/graph", response_model=KnowledgeGraphResponse)
async def get_full_graph(limit: int = Query(default=50, ge=1, le=200)) -> KnowledgeGraphResponse:
    agent = KnowledgeGraphAgent()
    graph = agent.get_full_graph(limit)
    return KnowledgeGraphResponse(nodes=graph["nodes"], edges=graph["edges"])


@router.get("/paper/{paper_id}", response_model=KnowledgeGraphResponse)
async def get_paper_subgraph(paper_id: str) -> KnowledgeGraphResponse:
    agent = KnowledgeGraphAgent()
    subgraph = agent.get_paper_subgraph(paper_id)
    return KnowledgeGraphResponse(paper_id=paper_id, subgraph=subgraph)


@router.get("/method/{method_name}")
async def search_by_method(method_name: str, limit: int = Query(default=10, ge=1, le=50)) -> dict:
    agent = KnowledgeGraphAgent()
    papers = agent.search_by_method(method_name, limit)
    return {"method": method_name, "papers": papers}
