"""
Document ingestion pipeline:

  raw file → text extraction → chunking → embedding → ChromaDB
"""

from __future__ import annotations

import logging
import uuid

from backend.rag.chunking import split_text
from backend.rag.loaders import extract_text
from backend.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def _short_summary(text: str, limit: int = 280) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def index_document_text(
    document_id: int,
    document_name: str,
    text: str,
) -> tuple[int, str]:
    """
    Chunk and index document text into the vector store.

    Returns:
        (chunk_count, short_summary)
    """
    chunks = split_text(text)
    if not chunks:
        raise ValueError("Document produced zero chunks after splitting")

    ids = [f"doc{document_id}_{uuid.uuid4().hex[:12]}" for _ in chunks]
    metadatas = [
        {
            "document_id": document_id,
            "document_name": document_name,
            "chunk_index": idx,
            "chunk_id": ids[idx],
        }
        for idx in range(len(chunks))
    ]

    store = get_vector_store()
    store.add_texts(texts=chunks, metadatas=metadatas, ids=ids)
    logger.info("Indexed document_id=%s with %s chunks", document_id, len(chunks))
    return len(chunks), _short_summary(text)


# Re-export for convenience
__all__ = ["extract_text", "index_document_text"]
