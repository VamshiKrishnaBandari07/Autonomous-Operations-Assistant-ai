"""
Task Agent — converts natural language into structured actionable tasks.

Extracts: title, priority, deadline, owner, description + confidence.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.agents.llm import invoke_json_llm, llm_available
from backend.models.schemas import TaskCreate

logger = logging.getLogger(__name__)

TASK_SYSTEM_PROMPT = """You are the OpsFlow AI Task Agent.
Extract actionable operational tasks from the user message.
Return STRICT JSON with this schema:
{
  "tasks": [
    {
      "title": "string",
      "description": "string",
      "priority": "low|medium|high|critical",
      "owner": "string",
      "deadline_days": null or integer days from today,
      "confidence": 0.0-1.0
    }
  ]
}
If no actionable task exists, return {"tasks": []}.
"""


def _heuristic_extract(text: str) -> list[dict[str, Any]]:
    """Offline fallback when no OpenAI key is configured."""
    lowered = text.lower()
    priority = "medium"
    if any(w in lowered for w in ("urgent", "asap", "critical", "immediately")):
        priority = "critical"
    elif any(w in lowered for w in ("high priority", "important")):
        priority = "high"
    elif "low priority" in lowered:
        priority = "low"

    owner = "Unassigned"
    owner_match = re.search(r"(?:assign(?:ed)? to|owner[:\s]+)\s*([A-Za-z][\w .'-]{1,40})", text, re.I)
    if owner_match:
        owner = owner_match.group(1).strip()

    deadline_days = None
    if "tomorrow" in lowered:
        deadline_days = 1
    elif "next week" in lowered:
        deadline_days = 7
    elif m := re.search(r"in (\d+)\s*days?", lowered):
        deadline_days = int(m.group(1))

    title = text.strip().split("\n")[0][:120]
    title = re.sub(r"^(please\s+)?(create|add|make)\s+(a\s+)?task\s*(to|for)?\s*", "", title, flags=re.I)
    title = title.strip(" .:") or "Untitled operations task"

    return [
        {
            "title": title[:255],
            "description": text.strip(),
            "priority": priority,
            "owner": owner,
            "deadline_days": deadline_days,
            "confidence": 0.62,
        }
    ]


def _parse_llm_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    # Strip markdown fences if the model wraps JSON
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


class TaskAgent:
    name = "task"

    def extract(self, text: str) -> list[TaskCreate]:
        items: list[dict[str, Any]]
        if llm_available():
            try:
                raw = invoke_json_llm(TASK_SYSTEM_PROMPT, text)
                payload = _parse_llm_json(raw)
                items = payload.get("tasks", [])
            except Exception as exc:  # noqa: BLE001
                logger.warning("TaskAgent LLM extraction failed: %s — using heuristic", exc)
                items = _heuristic_extract(text)
        else:
            items = _heuristic_extract(text)

        tasks: list[TaskCreate] = []
        for item in items:
            deadline = None
            days = item.get("deadline_days")
            if isinstance(days, int) and days >= 0:
                deadline = datetime.now(timezone.utc) + timedelta(days=days)

            priority = str(item.get("priority", "medium")).lower()
            if priority not in {"low", "medium", "high", "critical"}:
                priority = "medium"

            tasks.append(
                TaskCreate(
                    title=str(item.get("title", "Untitled task"))[:255],
                    description=str(item.get("description", text))[:4000],
                    priority=priority,
                    owner=str(item.get("owner", "Unassigned"))[:128],
                    deadline=deadline,
                    source="chat",
                    confidence=float(item.get("confidence", 0.7)),
                )
            )
        return tasks

    def run(self, text: str) -> dict[str, Any]:
        tasks = self.extract(text)
        if not tasks:
            return {
                "agent_type": self.name,
                "reply": "I could not identify a clear actionable task in that message.",
                "confidence": 0.4,
                "citations": [],
                "extracted_tasks": [],
            }

        lines = []
        for t in tasks:
            deadline = t.deadline.strftime("%Y-%m-%d") if t.deadline else "None"
            lines.append(
                f"- **{t.title}** | priority={t.priority} | owner={t.owner} | "
                f"deadline={deadline} | confidence={t.confidence:.0%}"
            )
        reply = "I extracted the following task(s):\n" + "\n".join(lines)
        avg_conf = sum(t.confidence for t in tasks) / len(tasks)
        return {
            "agent_type": self.name,
            "reply": reply,
            "confidence": round(avg_conf, 3),
            "citations": [],
            "extracted_tasks": tasks,
        }
