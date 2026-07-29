"""Additional security, validation, and onboarding edge-case tests."""

from __future__ import annotations

from io import BytesIO


def test_health_includes_backend_flags(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert "vector_backend" in body
    assert "llm_configured" in body
    assert "demo_auth_bypass" in body


def test_duplicate_employee_rejected(client):
    payload = {
        "full_name": "Sam Patel",
        "email": "sam.patel@company.com",
        "role": "Analyst",
        "department": "Operations",
    }
    first = client.post("/api/v1/onboarding/employees", json=payload)
    assert first.status_code == 201
    second = client.post("/api/v1/onboarding/employees", json=payload)
    assert second.status_code == 409


def test_invalid_employee_email(client):
    response = client.post(
        "/api/v1/onboarding/employees",
        json={
            "full_name": "Bad Email",
            "email": "not-an-email",
            "role": "Analyst",
            "department": "Operations",
        },
    )
    assert response.status_code == 422


def test_reject_unsupported_upload(client):
    files = {"file": ("malware.exe", BytesIO(b"not-a-document"), "application/octet-stream")}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400


def test_reject_empty_upload(client):
    files = {"file": ("empty.txt", BytesIO(b""), "text/plain")}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400


def test_task_status_validation(client):
    created = client.post(
        "/api/v1/tasks",
        json={"title": "Validate status", "priority": "medium", "owner": "Ops"},
    )
    task_id = created.json()["id"]
    bad = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "nope"})
    assert bad.status_code == 422
    good = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done"})
    assert good.status_code == 200
    assert good.json()["status"] == "done"


def test_password_hash_roundtrip():
    from backend.core.security import hash_password, verify_password

    hashed = hash_password("opsflow-admin-change-me")
    assert verify_password("opsflow-admin-change-me", hashed)
    assert not verify_password("wrong-password", hashed)


def test_conversation_history(client):
    chat = client.post(
        "/api/v1/chat",
        json={"message": "create a task to refresh the VPN certs assigned to Alex", "use_rag": False},
    )
    assert chat.status_code == 200
    convo_id = chat.json()["conversation_id"]
    listed = client.get("/api/v1/chat/conversations")
    assert listed.status_code == 200
    assert any(c["id"] == convo_id for c in listed.json())
    detail = client.get(f"/api/v1/chat/conversations/{convo_id}")
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) >= 2
