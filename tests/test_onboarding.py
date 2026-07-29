"""Tests for the employee onboarding automation pipeline."""

from __future__ import annotations


def test_employee_onboarding_pipeline(client):
    response = client.post(
        "/api/v1/onboarding/employees",
        json={
            "full_name": "Aisha Rahman",
            "email": "aisha.rahman@company.com",
            "role": "Operations Analyst",
            "department": "Operations",
            "start_date": "2026-08-04",
            "manager": "Jordan Lee",
        },
    )
    assert response.status_code == 201
    body = response.json()

    assert body["employee"]["full_name"] == "Aisha Rahman"
    assert body["welcome_email"]["subject"]
    assert body["welcome_email"]["body"]
    assert len(body["accounts_checklist"]) >= 5
    assert len(body["tasks_created"]) >= 5
    assert all(t["source"] == "onboarding" for t in body["tasks_created"])
    assert "Slack" in body["slack_message"] or "onboarding" in body["slack_message"].lower()
    assert body["pipeline"][0].startswith("1.")
    assert len(body["pipeline"]) == 5

    listed = client.get("/api/v1/onboarding/employees")
    assert listed.status_code == 200
    assert any(e["email"] == "aisha.rahman@company.com" for e in listed.json())
