"""arXiv paper search tool."""

import asyncio
import logging
from datetime import datetime

import arxiv

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _search_sync(query: str, max_results: int) -> list[dict]:
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    papers = []
    for result in client.results(search):
        published = result.published.isoformat() if result.published else None
        papers.append(
            {
                "arxiv_id": result.entry_id.split("/abs/")[-1],
                "title": result.title.replace("\n", " "),
                "authors": [a.name for a in result.authors],
                "abstract": result.summary.replace("\n", " "),
                "published": published,
                "pdf_url": result.pdf_url,
            }
        )
    return papers


async def search_arxiv(query: str, max_results: int | None = None) -> list[dict]:
    limit = max_results or settings.arxiv_max_results
    try:
        return await asyncio.to_thread(_search_sync, query, limit)
    except Exception as e:
        logger.error("arXiv search failed: %s", e)
        return []
