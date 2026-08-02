"""Literature Agent — paper search, PDF parsing, and knowledge extraction."""

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.tools.arxiv_search import search_arxiv
from app.tools.pdf_parser import extract_text_from_pdf, fetch_arxiv_pdf

logger = logging.getLogger(__name__)
settings = get_settings()

SUMMARY_SYSTEM_PROMPT = """You are an expert paper analyst.
Analyze the given paper text and return JSON with:
- title: paper title
- summary: 3-5 sentence summary
- methods: list of key methods/techniques
- datasets: list of datasets used
- innovations: list of main contributions

Respond ONLY with valid JSON, no markdown fences."""


class LiteratureAgent:
    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key or "sk-placeholder",
            base_url=settings.openai_base_url,
            temperature=0.2,
        )

    async def search_papers(self, query: str, max_results: int | None = None) -> list[dict]:
        limit = max_results or settings.arxiv_max_results
        return await search_arxiv(query, max_results=limit)

    async def summarize_paper(
        self,
        arxiv_id: str | None = None,
        text: str | None = None,
        title: str | None = None,
    ) -> dict:
        paper_text = text
        paper_title = title or "Unknown Paper"

        if arxiv_id and not paper_text:
            pdf_path = await fetch_arxiv_pdf(arxiv_id)
            if pdf_path:
                paper_text = extract_text_from_pdf(pdf_path)
                paper_title = title or f"arXiv:{arxiv_id}"

        if not paper_text:
            paper_text = f"Title: {paper_title}\n(No full text available — summarize from title only.)"

        truncated = paper_text[:12000]

        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
                    HumanMessage(content=f"Paper title: {paper_title}\n\nContent:\n{truncated}"),
                ]
            )
            content = response.content if isinstance(response.content, str) else str(response.content)
            return self._parse_summary(content, paper_title)
        except Exception as e:
            logger.warning("LLM summarization failed, using fallback: %s", e)
            return self._fallback_summary(paper_title, truncated)

    def _parse_summary(self, content: str, fallback_title: str) -> dict:
        cleaned = re.sub(r"```json\s*|\s*```", "", content.strip())
        try:
            summary = json.loads(cleaned)
            summary.setdefault("title", fallback_title)
            for key in ("methods", "datasets", "innovations"):
                summary.setdefault(key, [])
            summary.setdefault("summary", "")
            return summary
        except json.JSONDecodeError:
            return self._fallback_summary(fallback_title, content)

    def _fallback_summary(self, title: str, text: str) -> dict:
        preview = text[:500].replace("\n", " ")
        return {
            "title": title,
            "summary": preview,
            "methods": [],
            "datasets": [],
            "innovations": [],
        }
