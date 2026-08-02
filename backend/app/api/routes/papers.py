"""Paper search and summarization API."""

from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.literature import LiteratureAgent
from app.api.schemas import (
    PaperItem,
    PaperSearchRequest,
    PaperSearchResponse,
    PaperSummarizeRequest,
    PaperSummaryResponse,
)
from app.database.postgres import PaperRecord, get_db
from app.tools.embeddings import get_embedding
from app.database.milvus_client import get_milvus_store
from app.database.neo4j_client import get_neo4j_store

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("/search", response_model=PaperSearchResponse)
async def search_papers(
    request: PaperSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> PaperSearchResponse:
    agent = LiteratureAgent()
    papers = await agent.search_papers(request.query, request.max_results)

    for paper in papers:
        record = PaperRecord(
            project_id=request.project_id,
            arxiv_id=paper["arxiv_id"],
            title=paper["title"],
            authors=paper["authors"],
            abstract=paper["abstract"],
            extra={"published": paper.get("published"), "pdf_url": paper.get("pdf_url")},
        )
        db.add(record)

    await db.commit()

    return PaperSearchResponse(
        query=request.query,
        papers=[PaperItem(**p) for p in papers],
        total=len(papers),
    )


@router.post("/summarize", response_model=PaperSummaryResponse)
async def summarize_paper(
    request: PaperSummarizeRequest,
    db: AsyncSession = Depends(get_db),
) -> PaperSummaryResponse:
    agent = LiteratureAgent()
    summary = await agent.summarize_paper(
        arxiv_id=request.arxiv_id,
        text=request.text,
        title=request.title,
    )

    paper_id = str(uuid4())
    record = PaperRecord(
        id=paper_id,
        project_id=request.project_id,
        arxiv_id=request.arxiv_id,
        title=summary["title"],
        summary=summary["summary"],
        extra={
            "methods": summary["methods"],
            "datasets": summary["datasets"],
            "innovations": summary["innovations"],
        },
    )
    db.add(record)
    await db.commit()

    # Index in vector store and knowledge graph
    embedding = await get_embedding(f"{summary['title']}\n{summary['summary']}")
    if embedding:
        get_milvus_store().insert(paper_id, summary["title"], embedding)

    neo4j = get_neo4j_store()
    neo4j.upsert_paper(paper_id, summary["title"], request.arxiv_id)
    for method in summary["methods"]:
        neo4j.link_method(paper_id, method)
    for dataset in summary["datasets"]:
        neo4j.link_dataset(paper_id, dataset)

    return PaperSummaryResponse(paper_id=paper_id, **summary)
