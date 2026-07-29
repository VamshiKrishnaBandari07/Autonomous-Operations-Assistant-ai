"""
RAG retrieval + grounded answer generation.

AI workflow:
1. Embed the user query.
2. Retrieve top-k similar chunks from the company knowledge base.
3. Filter by similarity threshold.
4. Prompt the LLM with retrieved context + instructions to cite sources.
5. Compute a confidence score from retrieval similarity + answer grounding.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.core.config import get_settings
from backend.models.schemas import Citation
from backend.rag.vector_store import RetrievedChunk, get_vector_store
from backend.agents.llm import get_chat_model, llm_available

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """You are the OpsFlow AI Knowledge Agent for enterprise operations.
Answer ONLY using the provided context excerpts from company documents.
If the context is insufficient, say you do not have enough information and suggest uploading the relevant policy/document.
Be concise, accurate, and operational. Cite document names inline when helpful.
"""


def retrieve(query: str, k: int | None = None) -> list[RetrievedChunk]:
    settings = get_settings()
    top_k = k or settings.top_k_retrieval
    store = get_vector_store()
    results = store.similarity_search(query, k=top_k)
    threshold = settings.rag_score_threshold
    filtered = [r for r in results if r.score >= threshold]
    return filtered or results[: min(2, len(results))]


def chunks_to_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    citations: list[Citation] = []
    for chunk in chunks:
        meta = chunk.metadata or {}
        excerpt = chunk.content.strip()
        if len(excerpt) > 240:
            excerpt = excerpt[:237] + "..."
        citations.append(
            Citation(
                document_name=str(meta.get("document_name", "Unknown")),
                chunk_id=str(meta.get("chunk_id", "")),
                excerpt=excerpt,
                score=round(float(chunk.score), 3),
            )
        )
    return citations


def compute_confidence(chunks: list[RetrievedChunk], answer: str) -> float:
    """Blend retrieval quality with a simple grounding heuristic."""
    if not chunks:
        return 0.25
    avg_score = sum(c.score for c in chunks) / len(chunks)
    top_score = chunks[0].score
    grounded_penalty = 0.15 if "do not have enough information" in answer.lower() else 0.0
    confidence = 0.55 * top_score + 0.35 * avg_score + 0.10 - grounded_penalty
    return round(max(0.05, min(0.99, confidence)), 3)


def build_context_block(chunks: list[RetrievedChunk]) -> str:
    blocks: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        name = (chunk.metadata or {}).get("document_name", "Unknown")
        blocks.append(f"[{i}] Source: {name} (score={chunk.score:.2f})\n{chunk.content}")
    return "\n\n".join(blocks)


def answer_with_rag(query: str) -> dict[str, Any]:
    """
    End-to-end RAG QA.

    Returns dict with keys: answer, confidence, citations, chunks_used
    """
    chunks = retrieve(query)
    citations = chunks_to_citations(chunks)

    if not chunks:
        answer = (
            "I could not find relevant information in the company knowledge base. "
            "Please upload the related policy or operations document and try again."
        )
        return {
            "answer": answer,
            "confidence": 0.2,
            "citations": [],
            "chunks_used": 0,
        }

    context = build_context_block(chunks)

    if not llm_available():
        # Deterministic fallback for demos without an API key
        answer = (
            "Based on retrieved company documents:\n\n"
            + "\n\n".join(f"- ({c.document_name}) {c.excerpt}" for c in citations[:3])
            + "\n\n[Offline mode: set OPENAI_API_KEY for full LLM answers.]"
        )
        return {
            "answer": answer,
            "confidence": compute_confidence(chunks, answer),
            "citations": citations,
            "chunks_used": len(chunks),
        }

    llm = get_chat_model()
    user_prompt = (
        f"Context:\n{context}\n\n"
        f"Question: {query}\n\n"
        "Provide a clear answer for an operations employee. "
        "If useful, list steps or owners briefly."
    )

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        response = llm.invoke(
            [SystemMessage(content=RAG_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
        )
        answer = response.content if hasattr(response, "content") else str(response)
    except Exception as exc:  # noqa: BLE001
        logger.exception("LLM RAG call failed")
        answer = (
            f"Retrieved context was found, but the language model call failed ({exc}). "
            "Showing top excerpts instead:\n\n"
            + "\n\n".join(f"- ({c.document_name}) {c.excerpt}" for c in citations[:3])
        )

    return {
        "answer": answer,
        "confidence": compute_confidence(chunks, answer),
        "citations": citations,
        "chunks_used": len(chunks),
    }
