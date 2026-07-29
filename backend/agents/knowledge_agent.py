"""
Knowledge Agent — RAG-backed company Q&A with citations and confidence.
"""

from __future__ import annotations

from typing import Any

from backend.rag.pipeline import answer_with_rag


class KnowledgeAgent:
    """Retrieves grounded answers from the company document corpus."""

    name = "knowledge"

    def run(self, query: str) -> dict[str, Any]:
        result = answer_with_rag(query)
        return {
            "agent_type": self.name,
            "reply": result["answer"],
            "confidence": result["confidence"],
            "citations": result["citations"],
            "tasks_created": [],
        }
