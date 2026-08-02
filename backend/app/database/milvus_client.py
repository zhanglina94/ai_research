"""Milvus vector store for paper embeddings."""

import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

COLLECTION_NAME = "paper_embeddings"
DIMENSION = 1536  # OpenAI text-embedding-3-small


class MilvusStore:
    def __init__(self) -> None:
        self._connected = False
        self._collection = None

    def connect(self) -> None:
        if self._connected:
            return
        try:
            from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

            connections.connect(alias="default", host=settings.milvus_host, port=settings.milvus_port)

            if not utility.has_collection(COLLECTION_NAME):
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
                    FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=64),
                    FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=1024),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIMENSION),
                ]
                schema = CollectionSchema(fields=fields, description="Paper embeddings")
                self._collection = Collection(name=COLLECTION_NAME, schema=schema)
                self._collection.create_index(
                    field_name="embedding",
                    index_params={"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}},
                )
            else:
                self._collection = Collection(name=COLLECTION_NAME)

            self._collection.load()
            self._connected = True
        except Exception as e:
            logger.warning("Milvus connection failed (degraded mode): %s", e)
            self._connected = False

    def insert(self, paper_id: str, title: str, embedding: list[float]) -> bool:
        self.connect()
        if not self._connected or self._collection is None:
            return False
        try:
            self._collection.insert([[paper_id], [paper_id], [title[:1024]], [embedding]])
            self._collection.flush()
            return True
        except Exception as e:
            logger.error("Milvus insert failed: %s", e)
            return False

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        self.connect()
        if not self._connected or self._collection is None:
            return []
        try:
            results = self._collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param={"metric_type": "COSINE", "params": {"nprobe": 10}},
                limit=top_k,
                output_fields=["paper_id", "title"],
            )
            hits = []
            for hit in results[0]:
                hits.append({"paper_id": hit.entity.get("paper_id"), "title": hit.entity.get("title"), "score": hit.score})
            return hits
        except Exception as e:
            logger.error("Milvus search failed: %s", e)
            return []


_milvus_store: MilvusStore | None = None


def get_milvus_store() -> MilvusStore:
    global _milvus_store
    if _milvus_store is None:
        _milvus_store = MilvusStore()
    return _milvus_store
