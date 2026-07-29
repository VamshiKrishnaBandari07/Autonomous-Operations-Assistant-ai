"""
Vector store abstraction for OpsFlow AI.

Uses ChromaDB with SentenceTransformer embeddings by default.
Falls back to a lightweight in-memory store when Chroma is unavailable
(useful for unit tests without heavyweight ML deps).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    content: str
    metadata: dict[str, Any]
    score: float


class InMemoryVectorStore:
    """Minimal cosine-similarity store for tests / offline demos."""

    def __init__(self) -> None:
        self._docs: list[dict[str, Any]] = []

    def add_texts(self, texts: list[str], metadatas: list[dict[str, Any]], ids: list[str]) -> None:
        for text, meta, doc_id in zip(texts, metadatas, ids):
            self._docs.append({"id": doc_id, "text": text, "metadata": meta})

    def similarity_search(self, query: str, k: int = 5) -> list[RetrievedChunk]:
        # Token-overlap heuristic (no embeddings required)
        q_tokens = set(query.lower().split())
        scored: list[RetrievedChunk] = []
        for doc in self._docs:
            tokens = set(doc["text"].lower().split())
            if not tokens:
                continue
            overlap = len(q_tokens & tokens) / max(len(q_tokens), 1)
            scored.append(
                RetrievedChunk(content=doc["text"], metadata=doc["metadata"], score=float(overlap))
            )
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:k]

    def delete_by_document_id(self, document_id: int) -> None:
        self._docs = [d for d in self._docs if d["metadata"].get("document_id") != document_id]


class ChromaVectorStore:
    """Persistent ChromaDB collection backed by SentenceTransformer embeddings."""

    COLLECTION_NAME = "opsflow_knowledge"

    def __init__(self) -> None:
        import chromadb
        from chromadb.utils import embedding_functions

        settings = get_settings()
        Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model
        )
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def add_texts(self, texts: list[str], metadatas: list[dict[str, Any]], ids: list[str]) -> None:
        if not texts:
            return
        # Chroma metadata values must be primitive types
        clean_metas = []
        for meta in metadatas:
            clean_metas.append({k: (v if isinstance(v, (str, int, float, bool)) else str(v)) for k, v in meta.items()})
        self._collection.add(documents=texts, metadatas=clean_metas, ids=ids)

    def similarity_search(self, query: str, k: int = 5) -> list[RetrievedChunk]:
        if self._collection.count() == 0:
            return []
        result = self._collection.query(query_texts=[query], n_results=min(k, self._collection.count()))
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]

        chunks: list[RetrievedChunk] = []
        for content, meta, dist in zip(docs, metas, dists):
            # Cosine distance → similarity score in [0, 1]
            score = max(0.0, 1.0 - float(dist))
            chunks.append(RetrievedChunk(content=content, metadata=meta or {}, score=score))
        return chunks

    def delete_by_document_id(self, document_id: int) -> None:
        self._collection.delete(where={"document_id": document_id})


_store_lock = threading.Lock()
_store_instance: ChromaVectorStore | InMemoryVectorStore | None = None


def get_vector_store() -> ChromaVectorStore | InMemoryVectorStore:
    """Lazy singleton vector store."""
    global _store_instance
    if _store_instance is not None:
        return _store_instance

    with _store_lock:
        if _store_instance is not None:
            return _store_instance
        settings = get_settings()
        try:
            if settings.vector_store.lower() == "chroma":
                _store_instance = ChromaVectorStore()
                logger.info("Initialised Chroma vector store at %s", settings.chroma_persist_dir)
            else:
                _store_instance = InMemoryVectorStore()
                logger.info("Initialised in-memory vector store")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Chroma unavailable (%s); falling back to in-memory store", exc)
            _store_instance = InMemoryVectorStore()
        return _store_instance


def reset_vector_store_for_tests() -> InMemoryVectorStore:
    """Force an in-memory store for unit tests."""
    global _store_instance
    _store_instance = InMemoryVectorStore()
    return _store_instance
