"""Demo mode API tests."""

from __future__ import annotations


def test_demo_status_and_seed(client):
    status = client.get("/api/v1/demo/status")
    assert status.status_code == 200
    body = status.json()
    assert body["demo_mode"] is True
    assert body["seeded"] is True
    assert body["sample_prompts"]
    assert any("leave" in p.lower() for p in body["sample_prompts"])


def test_demo_metrics(client):
    metrics = client.get("/api/v1/demo/metrics")
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["ai_queries_completed"] >= 245
    assert body["automated_tasks_created"] >= 128
    assert body["estimated_hours_saved"] >= 42
    assert body["workflow_success_rate"] == 96.0


def test_health_includes_demo_mode(client):
    health = client.get("/api/v1/health").json()
    assert "demo_mode" in health


def test_rag_answers_annual_leave(client):
    # Ensure demo docs seeded
    client.get("/api/v1/demo/status")
    chat = client.post(
        "/api/v1/chat",
        json={"message": "How many annual leave days do employees receive?", "use_rag": True},
    )
    assert chat.status_code == 200
    body = chat.json()
    assert body["agent_type"] == "knowledge"
    assert "25" in body["reply"] or body["citations"]
