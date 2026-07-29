"""
Onboarding Agent — generates personalised welcome emails for new hires.

AI workflow:
  New employee payload → LLM (or template fallback) → subject + HTML/text body
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.agents.llm import invoke_json_llm, llm_available

logger = logging.getLogger(__name__)

WELCOME_SYSTEM_PROMPT = """You are the OpsFlow AI Onboarding Agent for enterprise HR/operations.
Write a warm, professional welcome email for a new employee.
Return STRICT JSON:
{
  "subject": "string",
  "body": "plain-text email body with short paragraphs and a clear next-steps section",
  "confidence": 0.0-1.0
}
Tone: friendly, concise, operational. Mention first-week orientation, manager, and IT accounts setup.
Do not invent company legal policies.
"""

# Standard IT / SaaS accounts checklist used by n8n + Task Agent
DEFAULT_ACCOUNTS_CHECKLIST = [
    {"item": "Corporate email account", "system": "Google Workspace / Microsoft 365", "owner": "IT"},
    {"item": "Slack workspace invite", "system": "Slack", "owner": "IT"},
    {"item": "HRIS / payroll profile", "system": "HRIS", "owner": "HR"},
    {"item": "VPN access", "system": "VPN", "owner": "IT"},
    {"item": "GitHub / GitLab access", "system": "Source control", "owner": "Engineering Ops"},
    {"item": "Laptop / equipment request", "system": "Asset management", "owner": "IT"},
    {"item": "Benefits enrollment link", "system": "Benefits portal", "owner": "HR"},
]


def _template_welcome(employee: dict[str, Any]) -> dict[str, Any]:
    name = employee.get("full_name", "there")
    role = employee.get("role", "team member")
    department = employee.get("department", "your department")
    manager = employee.get("manager", "your manager")
    start = employee.get("start_date") or "your start date"

    subject = f"Welcome to the team, {name}!"
    body = (
        f"Hi {name},\n\n"
        f"Welcome aboard! We're excited to have you join as {role} in {department}.\n\n"
        f"Your first day is scheduled for {start}. "
        f"Your manager, {manager}, will guide you through orientation.\n\n"
        "Next steps:\n"
        "1. Check your inbox for account setup instructions (email, Slack, VPN).\n"
        "2. Complete HR paperwork and benefits enrollment.\n"
        "3. Join the new-hire orientation session in your calendar.\n\n"
        "If you need help, reply to this email or message #people-ops on Slack.\n\n"
        "Welcome to OpsFlow!\n"
        "People Operations"
    )
    return {"subject": subject, "body": body, "confidence": 0.72}


def _parse_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


class OnboardingAgent:
    """Creates welcome emails and the accounts provisioning checklist."""

    name = "onboarding"

    def create_welcome_email(self, employee: dict[str, Any]) -> dict[str, Any]:
        if llm_available():
            try:
                raw = invoke_json_llm(
                    WELCOME_SYSTEM_PROMPT,
                    json.dumps(employee, default=str),
                )
                data = _parse_json(raw)
                return {
                    "subject": str(data.get("subject", f"Welcome, {employee.get('full_name', '')}!")),
                    "body": str(data.get("body", "")),
                    "confidence": float(data.get("confidence", 0.85)),
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("OnboardingAgent LLM failed: %s — using template", exc)
        return _template_welcome(employee)

    def build_accounts_checklist(self, employee: dict[str, Any]) -> list[dict[str, str]]:
        """Checklist payload consumed by n8n for account provisioning."""
        name = employee.get("full_name", "New hire")
        checklist = []
        for row in DEFAULT_ACCOUNTS_CHECKLIST:
            checklist.append(
                {
                    **row,
                    "employee": name,
                    "employee_email": str(employee.get("email", "")),
                    "status": "pending",
                }
            )
        return checklist
