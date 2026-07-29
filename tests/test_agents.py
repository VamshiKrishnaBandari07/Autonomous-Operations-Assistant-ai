"""Unit tests for agents and RAG helpers (offline / no API key)."""

from __future__ import annotations

from backend.agents.orchestrator import classify_intent
from backend.agents.task_agent import TaskAgent
from backend.agents.meeting_agent import MeetingAgent
from backend.rag.chunking import split_text
from backend.rag.pipeline import answer_with_rag, compute_confidence
from backend.rag.vector_store import RetrievedChunk, reset_vector_store_for_tests
from backend.rag.ingest import index_document_text


def test_classify_intent_task():
    assert classify_intent("Please create a task to renew SSL certificates") == "task"


def test_classify_intent_knowledge():
    assert classify_intent("What is the incident acknowledgement SLA?") == "knowledge"


def test_classify_intent_meeting():
    assert classify_intent("Summarise this meeting transcript for the ops team") == "meeting"


def test_classify_intent_reporting():
    assert classify_intent("Generate the weekly operations report please") == "reporting"


def test_task_agent_heuristic():
    agent = TaskAgent()
    tasks = agent.extract(
        "Create a high priority task assigned to Jordan to patch the VPN gateway in 3 days"
    )
    assert len(tasks) == 1
    assert tasks[0].priority in {"high", "critical", "medium"}
    assert "Jordan" in tasks[0].owner or tasks[0].owner == "Unassigned"
    assert tasks[0].deadline is not None


def test_meeting_agent_heuristic():
    agent = MeetingAgent()
    result = agent.summarise(
        "We decided to freeze deploys on Friday.\nAlice will follow up on vendor quotes.",
        title="Freeze Review",
    )
    assert result["summary"]
    assert result["key_decisions"]
    assert result["action_items"]
    assert 0 < result["confidence"] <= 1


def test_chunking_and_rag_pipeline():
    store = reset_vector_store_for_tests()
    text = (
        "Incident Response Policy. "
        "All production incidents must be acknowledged within 15 minutes. "
        "Severity 1 incidents require an incident commander."
    )
    chunks = split_text(text)
    assert len(chunks) >= 1

    count, summary = index_document_text(1, "incident_policy.txt", text)
    assert count >= 1
    assert summary

    result = answer_with_rag("How quickly must incidents be acknowledged?")
    assert result["answer"]
    assert result["chunks_used"] >= 1
    assert result["citations"]

    conf = compute_confidence(
        [RetrievedChunk(content="ack in 15 minutes", metadata={}, score=0.9)],
        result["answer"],
    )
    assert 0.0 < conf <= 1.0
    assert store.similarity_search("incident", k=1)
