"""Neo4j knowledge graph store."""

import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Neo4jStore:
    def __init__(self) -> None:
        self._driver = None

    def connect(self) -> None:
        if self._driver is not None:
            return
        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            self._driver.verify_connectivity()
        except Exception as e:
            logger.warning("Neo4j connection failed (degraded mode): %s", e)
            self._driver = None

    def close(self) -> None:
        if self._driver:
            self._driver.close()
            self._driver = None

    def upsert_paper(self, paper_id: str, title: str, arxiv_id: str | None = None) -> bool:
        self.connect()
        if not self._driver:
            return False
        try:
            with self._driver.session() as session:
                session.run(
                    """
                    MERGE (p:Paper {id: $paper_id})
                    SET p.title = $title, p.arxiv_id = $arxiv_id
                    """,
                    paper_id=paper_id,
                    title=title,
                    arxiv_id=arxiv_id,
                )
            return True
        except Exception as e:
            logger.error("Neo4j upsert_paper failed: %s", e)
            return False

    def link_method(self, paper_id: str, method_name: str) -> bool:
        self.connect()
        if not self._driver:
            return False
        try:
            with self._driver.session() as session:
                session.run(
                    """
                    MATCH (p:Paper {id: $paper_id})
                    MERGE (m:Method {name: $method_name})
                    MERGE (p)-[:USES]->(m)
                    """,
                    paper_id=paper_id,
                    method_name=method_name,
                )
            return True
        except Exception as e:
            logger.error("Neo4j link_method failed: %s", e)
            return False

    def link_dataset(self, paper_id: str, dataset_name: str) -> bool:
        self.connect()
        if not self._driver:
            return False
        try:
            with self._driver.session() as session:
                session.run(
                    """
                    MATCH (p:Paper {id: $paper_id})
                    MERGE (d:Dataset {name: $dataset_name})
                    MERGE (p)-[:USES]->(d)
                    """,
                    paper_id=paper_id,
                    dataset_name=dataset_name,
                )
            return True
        except Exception as e:
            logger.error("Neo4j link_dataset failed: %s", e)
            return False

    def link_model(self, paper_id: str, model_name: str) -> bool:
        self.connect()
        if not self._driver:
            return False
        try:
            with self._driver.session() as session:
                session.run(
                    """
                    MATCH (p:Paper {id: $paper_id})
                    MERGE (m:Model {name: $model_name})
                    MERGE (p)-[:PROPOSES]->(m)
                    """,
                    paper_id=paper_id,
                    model_name=model_name,
                )
            return True
        except Exception as e:
            logger.error("Neo4j link_model failed: %s", e)
            return False

    def link_citation(self, paper_id: str, cited_paper_id: str) -> bool:
        self.connect()
        if not self._driver:
            return False
        try:
            with self._driver.session() as session:
                session.run(
                    """
                    MATCH (p:Paper {id: $paper_id}), (c:Paper {id: $cited_paper_id})
                    MERGE (p)-[:CITES]->(c)
                    """,
                    paper_id=paper_id,
                    cited_paper_id=cited_paper_id,
                )
            return True
        except Exception as e:
            logger.error("Neo4j link_citation failed: %s", e)
            return False

    def get_paper_graph(self, paper_id: str) -> dict[str, Any]:
        self.connect()
        if not self._driver:
            return {"paper_id": paper_id, "methods": [], "datasets": [], "models": []}
        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (p:Paper {id: $paper_id})
                    OPTIONAL MATCH (p)-[:USES]->(m:Method)
                    OPTIONAL MATCH (p)-[:USES]->(d:Dataset)
                    OPTIONAL MATCH (p)-[:PROPOSES]->(mo:Model)
                    OPTIONAL MATCH (p)-[:CITES]->(c:Paper)
                    RETURN p.title AS title,
                           collect(DISTINCT m.name) AS methods,
                           collect(DISTINCT d.name) AS datasets,
                           collect(DISTINCT mo.name) AS models,
                           collect(DISTINCT c.title) AS citations
                    """,
                    paper_id=paper_id,
                )
                record = result.single()
                if not record:
                    return {"paper_id": paper_id, "methods": [], "datasets": [], "models": []}
                return {
                    "paper_id": paper_id,
                    "title": record["title"],
                    "methods": [m for m in record["methods"] if m],
                    "datasets": [d for d in record["datasets"] if d],
                    "models": [m for m in record["models"] if m],
                    "citations": [c for c in record["citations"] if c],
                }
        except Exception as e:
            logger.error("Neo4j get_paper_graph failed: %s", e)
            return {"paper_id": paper_id, "methods": [], "datasets": [], "models": []}

    def search_by_method(self, method_name: str, limit: int = 10) -> list[dict[str, Any]]:
        self.connect()
        if not self._driver:
            return []
        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (m:Method {name: $method_name})<-[:USES]-(p:Paper)
                    RETURN p.id AS paper_id, p.title AS title
                    LIMIT $limit
                    """,
                    method_name=method_name,
                    limit=limit,
                )
                return [dict(r) for r in result]
        except Exception as e:
            logger.error("Neo4j search_by_method failed: %s", e)
            return []

    def get_full_graph(self, limit: int = 50) -> dict[str, Any]:
        self.connect()
        if not self._driver:
            return {"nodes": [], "edges": []}
        try:
            with self._driver.session() as session:
                nodes_result = session.run(
                    """
                    MATCH (n) WHERE n:Paper OR n:Method OR n:Dataset OR n:Model
                    RETURN labels(n)[0] AS type,
                           coalesce(n.id, n.name) AS id,
                           coalesce(n.title, n.name) AS label
                    LIMIT $limit
                    """,
                    limit=limit,
                )
                edges_result = session.run(
                    """
                    MATCH (a)-[r]->(b)
                    WHERE type(r) IN ['USES', 'PROPOSES', 'CITES']
                    RETURN coalesce(a.id, a.name) AS source,
                           coalesce(b.id, b.name) AS target,
                           type(r) AS relation
                    LIMIT $limit
                    """,
                    limit=limit,
                )
                return {
                    "nodes": [dict(n) for n in nodes_result],
                    "edges": [dict(e) for e in edges_result],
                }
        except Exception as e:
            logger.error("Neo4j get_full_graph failed: %s", e)
            return {"nodes": [], "edges": []}


_neo4j_store: Neo4jStore | None = None


def get_neo4j_store() -> Neo4jStore:
    global _neo4j_store
    if _neo4j_store is None:
        _neo4j_store = Neo4jStore()
    return _neo4j_store
