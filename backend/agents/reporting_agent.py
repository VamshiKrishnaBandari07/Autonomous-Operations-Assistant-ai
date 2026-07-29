"""
Reporting Agent — weekly operational reports with bottlenecks and trends.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from backend.agents.llm import invoke_json_llm, llm_available
from backend.services.analytics_service import build_analytics

logger = logging.getLogger(__name__)

REPORT_SYSTEM_PROMPT = """You are the OpsFlow AI Reporting Agent.
Given operational metrics JSON, produce a weekly operations report as STRICT JSON:
{
  "title": "string",
  "summary": "executive summary",
  "content": "markdown report body with sections",
  "bottlenecks": ["bottleneck 1", "..."],
  "trends": ["trend 1", "..."],
  "confidence": 0.0-1.0
}
Be analytical, practical, and suitable for an operations leadership audience.
"""


def _offline_report(metrics: dict[str, Any], report_type: str) -> dict[str, Any]:
    open_tasks = metrics.get("open_tasks", 0)
    completed = metrics.get("completed_tasks", 0)
    queries = metrics.get("total_queries", 0)
    hours = metrics.get("estimated_hours_saved", 0)

    bottlenecks = []
    if open_tasks > completed:
        bottlenecks.append("Open task backlog exceeds completed work — review ownership and deadlines.")
    if metrics.get("tasks_by_priority", {}).get("critical", 0):
        bottlenecks.append("Critical-priority tasks are present and need escalation.")
    if not bottlenecks:
        bottlenecks.append("No major bottlenecks detected from current metrics.")

    trends = [
        f"Knowledge queries handled: {queries}",
        f"Estimated operational hours saved: {hours}",
        f"Task completion ratio: {completed}:{open_tasks} (done:open)",
    ]

    content = (
        f"## {report_type.title()} Operations Report\n\n"
        f"### Snapshot\n"
        f"- Queries: {queries}\n"
        f"- Tasks open / done: {open_tasks} / {completed}\n"
        f"- Documents indexed: {metrics.get('documents_indexed', 0)}\n"
        f"- Hours saved (est.): {hours}\n\n"
        f"### Bottlenecks\n"
        + "\n".join(f"- {b}" for b in bottlenecks)
        + "\n\n### Trends\n"
        + "\n".join(f"- {t}" for t in trends)
    )

    return {
        "title": f"{report_type.title()} Operational Report",
        "summary": (
            f"OpsFlow processed {queries} queries and tracked {open_tasks + completed} tasks, "
            f"saving an estimated {hours} hours."
        ),
        "content": content,
        "bottlenecks": bottlenecks,
        "trends": trends,
        "confidence": 0.7,
    }


def _parse_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


class ReportingAgent:
    name = "reporting"

    def generate(self, db: Session, report_type: str = "weekly") -> dict[str, Any]:
        analytics = build_analytics(db)
        metrics = analytics.model_dump()

        if llm_available():
            try:
                raw = invoke_json_llm(
                    REPORT_SYSTEM_PROMPT,
                    f"Report type: {report_type}\nMetrics:\n{json.dumps(metrics, default=str)}",
                )
                data = _parse_json(raw)
                return {
                    "title": str(data.get("title", f"{report_type.title()} Operational Report")),
                    "summary": str(data.get("summary", "")),
                    "content": str(data.get("content", "")),
                    "bottlenecks": list(data.get("bottlenecks", [])),
                    "trends": list(data.get("trends", [])),
                    "confidence": float(data.get("confidence", 0.8)),
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("ReportingAgent LLM failed: %s — offline report", exc)

        return _offline_report(metrics, report_type)
