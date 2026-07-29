"""
Meeting Agent — summarises transcripts into summary, decisions, and action items.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.agents.llm import invoke_json_llm, llm_available
from backend.models.schemas import ActionItem

logger = logging.getLogger(__name__)

MEETING_SYSTEM_PROMPT = """You are the OpsFlow AI Meeting Agent.
Analyse the meeting transcript and return STRICT JSON:
{
  "summary": "2-4 paragraph executive summary",
  "key_decisions": ["decision 1", "decision 2"],
  "action_items": [
    {
      "title": "string",
      "owner": "string",
      "deadline": "YYYY-MM-DD or null",
      "priority": "low|medium|high|critical"
    }
  ],
  "confidence": 0.0-1.0
}
Focus on operational clarity. Prefer concrete owners and deadlines when stated.
"""


def _heuristic_meeting(transcript: str, title: str) -> dict[str, Any]:
    lines = [ln.strip() for ln in transcript.splitlines() if ln.strip()]
    summary = " ".join(lines[:8])
    if len(summary) > 600:
        summary = summary[:597] + "..."

    decisions = [ln for ln in lines if re.search(r"\b(decid(ed|e)|agreed|approval)\b", ln, re.I)][:5]
    if not decisions:
        decisions = ["No explicit decisions detected in offline mode."]

    action_items: list[ActionItem] = []
    for ln in lines:
        if re.search(r"\b(action|todo|follow[- ]?up|will|assign)\b", ln, re.I):
            owner_match = re.search(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b", ln)
            action_items.append(
                ActionItem(
                    title=ln[:180],
                    owner=owner_match.group(1) if owner_match else "Unassigned",
                    deadline=None,
                    priority="medium",
                )
            )
        if len(action_items) >= 5:
            break

    if not action_items:
        action_items = [
            ActionItem(
                title=f"Review notes from {title}",
                owner="Unassigned",
                priority="medium",
            )
        ]

    return {
        "summary": summary or "Meeting transcript processed in offline mode.",
        "key_decisions": decisions,
        "action_items": action_items,
        "confidence": 0.55,
    }


def _parse_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


class MeetingAgent:
    name = "meeting"

    def summarise(self, transcript: str, title: str = "Meeting Summary") -> dict[str, Any]:
        if llm_available():
            try:
                raw = invoke_json_llm(
                    MEETING_SYSTEM_PROMPT,
                    f"Title: {title}\n\nTranscript:\n{transcript}",
                )
                data = _parse_json(raw)
                action_items = [
                    ActionItem(
                        title=str(item.get("title", "Untitled action"))[:255],
                        owner=str(item.get("owner", "Unassigned"))[:128],
                        deadline=item.get("deadline"),
                        priority=str(item.get("priority", "medium")).lower(),
                    )
                    for item in data.get("action_items", [])
                ]
                return {
                    "summary": str(data.get("summary", "")),
                    "key_decisions": [str(d) for d in data.get("key_decisions", [])],
                    "action_items": action_items,
                    "confidence": float(data.get("confidence", 0.75)),
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("MeetingAgent LLM failed: %s — heuristic fallback", exc)

        return _heuristic_meeting(transcript, title)
