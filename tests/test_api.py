"""API-level unit tests."""

from __future__ import annotations

from io import BytesIO


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "OpsFlow AI"


def test_login_success(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "opsflow-admin-change-me"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_failure(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_create_and_list_tasks(client):
    create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Review incident playbook",
            "description": "Ensure SLA section is current",
            "priority": "high",
            "owner": "Alex",
            "source": "manual",
        },
    )
    assert create.status_code == 201
    task = create.json()
    assert task["title"] == "Review incident playbook"
    assert task["priority"] == "high"

    listed = client.get("/api/v1/tasks")
    assert listed.status_code == 200
    assert any(t["id"] == task["id"] for t in listed.json())


def test_task_extract_offline(client):
    response = client.post(
        "/api/v1/tasks/extract",
        json={"text": "Please create a task to update the onboarding checklist assigned to Priya by tomorrow"},
    )
    assert response.status_code == 201
    tasks = response.json()
    assert len(tasks) >= 1
    assert tasks[0]["owner"]


def test_document_upload_and_rag_chat(client):
    content = (
        b"OpsFlow Access Policy\n"
        b"Privileged access to production systems is granted via time-bound tickets only.\n"
        b"Shared admin accounts are prohibited.\n"
    )
    files = {"file": ("access_policy.txt", BytesIO(content), "text/plain")}
    upload = client.post("/api/v1/documents/upload", files=files)
    assert upload.status_code == 201
    doc = upload.json()
    assert doc["status"] == "indexed"
    assert doc["chunk_count"] >= 1

    chat = client.post(
        "/api/v1/chat",
        json={"message": "Are shared admin accounts allowed?", "use_rag": True},
    )
    assert chat.status_code == 200
    body = chat.json()
    assert body["agent_type"] == "knowledge"
    assert body["reply"]
    assert 0.0 <= body["confidence"] <= 1.0


def test_meeting_summarise(client):
    transcript = """
    Alice: We decided to migrate the billing batch to Sunday nights.
    Bob: I will prepare the rollback plan by Friday.
    Carol: Agreed — also create a task to notify finance.
    """
    response = client.post(
        "/api/v1/meetings/summarise",
        json={
            "transcript": transcript,
            "title": "Billing Migration Sync",
            "create_tasks": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]
    assert body["key_decisions"]
    assert body["action_items"]
    assert len(body["tasks_created"]) >= 1


def test_analytics_and_report(client):
    # Seed a bit of activity
    client.post(
        "/api/v1/tasks",
        json={"title": "Close open tickets", "priority": "medium", "owner": "Sam"},
    )
    analytics = client.get("/api/v1/analytics")
    assert analytics.status_code == 200
    data = analytics.json()
    assert "estimated_hours_saved" in data
    assert "common_request_types" in data

    report = client.post("/api/v1/reports/generate", json={"report_type": "weekly"})
    assert report.status_code == 200
    assert report.json()["content"]
