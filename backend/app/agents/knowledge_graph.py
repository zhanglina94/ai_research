"""Knowledge Graph Agent — manages Paper, Method, Dataset, Model, Citation relations."""

import logging
from typing import Any

from app.database.neo4j_client import get_neo4j_store

logger = logging.getLogger(__name__)


class KnowledgeGraphAgent:
    """Builds and queries the research knowledge graph in Neo4j."""

    def __init__(self) -> None:
        self.store = get_neo4j_store()

    def ingest_paper_knowledge(
        self,
        paper_id: str,
        title: str,
        methods: list[str] | None = None,
        datasets: list[str] | None = None,
        arxiv_id: str | None = None,
    ) -> dict[str, bool]:
        results = {"paper": self.store.upsert_paper(paper_id, title, arxiv_id)}
        for method in methods or []:
            results[f"method:{method}"] = self.store.link_method(paper_id, method)
        for dataset in datasets or []:
            results[f"dataset:{dataset}"] = self.store.link_dataset(paper_id, dataset)
        return results

    def link_citation(self, paper_id: str, cited_paper_id: str) -> bool:
        return self.store.link_citation(paper_id, cited_paper_id)

    def link_model(self, paper_id: str, model_name: str) -> bool:
        return self.store.link_model(paper_id, model_name)

    def get_paper_subgraph(self, paper_id: str) -> dict[str, Any]:
        return self.store.get_paper_graph(paper_id)

    def search_by_method(self, method_name: str, limit: int = 10) -> list[dict[str, Any]]:
        return self.store.search_by_method(method_name, limit)

    def get_full_graph(self, limit: int = 50) -> dict[str, Any]:
        return self.store.get_full_graph(limit)
