"""
OpsFlow AI Orchestrator

Routes each user message to the most suitable specialist agent:

  knowledge  → RAG Q&A over company documents
  task       → structured task extraction
  meeting    → transcript summarisation cues
  reporting  → operational report generation cues

Uses a lightweight intent classifier (LLM when available, keyword rules otherwise).
Optionally integrates with LangGraph when installed for graph-style routing.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from sqlalchemy.orm import Session

from backend.agents.knowledge_agent import KnowledgeAgent
from backend.agents.llm import invoke_json_llm, llm_available
from backend.agents.meeting_agent import MeetingAgent
from backend.agents.reporting_agent import ReportingAgent
from backend.agents.task_agent import TaskAgent
from backend.models.schemas import TaskCreate
from backend.models.user import User
from backend.services.task_service import create_task_and_notify

logger = logging.getLogger(__name__)

AgentName = Literal["knowledge", "task", "meeting", "reporting"]


def classify_intent(message: str) -> AgentName:
    """Rule-based intent router with optional LLM refinement."""
    text = message.lower().strip()

    # Strong keyword signals first (fast path)
    if any(k in text for k in ("create a task", "add a task", "todo:", "assign to", "remind me to")):
        return "task"
    if any(k in text for k in ("meeting transcript", "summarise this meeting", "action items from")):
        return "meeting"
    if any(k in text for k in ("weekly report", "generate report", "operations report", "bottleneck")):
        return "reporting"

    if llm_available():
        try:
            raw = invoke_json_llm(
                "Classify the user message into one label: knowledge, task, meeting, reporting. "
                'Return JSON: {"intent": "...", "confidence": 0-1}',
                message,
            )
            match = re.search(r'"(knowledge|task|meeting|reporting)"', raw.lower())
            if match:
                return match.group(1)  # type: ignore[return-value]
        except Exception as exc:  # noqa: BLE001
            logger.debug("Intent LLM classification failed: %s", exc)

    # Soft keyword fallback
    if any(k in text for k in ("task", "deadline", "assign", "owner")):
        return "task"
    if any(k in text for k in ("meeting", "transcript", "standup")):
        return "meeting"
    if any(k in text for k in ("report", "kpi", "trend", "analytics")):
        return "reporting"
    return "knowledge"


class OpsOrchestrator:
    """Coordinates specialist agents for chat interactions."""

    def __init__(self) -> None:
        self.knowledge = KnowledgeAgent()
        self.task = TaskAgent()
        self.meeting = MeetingAgent()
        self.reporting = ReportingAgent()

    async def handle_chat(
        self,
        message: str,
        db: Session,
        user: User,
        use_rag: bool = True,
    ) -> dict[str, Any]:
        intent = classify_intent(message)
        logger.info("Routed message to agent=%s", intent)

        if intent == "task":
            result = self.task.run(message)
            created = []
            for item in result.get("extracted_tasks", []):
                if not isinstance(item, TaskCreate):
                    continue
                task = await create_task_and_notify(db, item, user)
                created.append(task)
            result["tasks_created"] = created
            result.pop("extracted_tasks", None)
            return result

        if intent == "meeting":
            summarised = self.meeting.summarise(message, title="Chat Meeting Notes")
            reply_parts = [
                "### Meeting Summary",
                summarised["summary"],
                "",
                "### Key Decisions",
                *[f"- {d}" for d in summarised["key_decisions"]],
                "",
                "### Action Items",
                *[
                    f"- {a.title} (owner={a.owner}, priority={a.priority})"
                    for a in summarised["action_items"]
                ],
            ]
            created = []
            for item in summarised["action_items"]:
                payload = TaskCreate(
                    title=item.title,
                    description=f"From meeting notes: {item.title}",
                    priority=item.priority if item.priority in {"low", "medium", "high", "critical"} else "medium",
                    owner=item.owner,
                    source="meeting",
                    confidence=summarised["confidence"],
                )
                task = await create_task_and_notify(db, payload, user)
                created.append(task)
            return {
                "agent_type": "meeting",
                "reply": "\n".join(reply_parts),
                "confidence": summarised["confidence"],
                "citations": [],
                "tasks_created": created,
            }

        if intent == "reporting":
            report = self.reporting.generate(db, report_type="weekly")
            return {
                "agent_type": "reporting",
                "reply": f"**{report['title']}**\n\n{report['summary']}\n\n{report['content']}",
                "confidence": report["confidence"],
                "citations": [],
                "tasks_created": [],
            }

        # Default: knowledge / RAG
        if use_rag:
            return self.knowledge.run(message)

        return {
            "agent_type": "knowledge",
            "reply": (
                "RAG is disabled for this turn. Enable document retrieval to answer from "
                "company knowledge, or ask me to create a task / summarise a meeting."
            ),
            "confidence": 0.3,
            "citations": [],
            "tasks_created": [],
        }


# Optional LangGraph wiring for portfolio clarity / extensibility
def build_langgraph_router():
    """
    Build a LangGraph StateGraph for agent routing when langgraph is available.

    Graph:
      START → classify → (knowledge|task|meeting|reporting) → END
    """
    try:
        from typing import TypedDict

        from langgraph.graph import END, StateGraph

        class GraphState(TypedDict):
            message: str
            intent: str
            result: dict

        orchestrator = OpsOrchestrator()

        def classify_node(state: GraphState) -> GraphState:
            state["intent"] = classify_intent(state["message"])
            return state

        def knowledge_node(state: GraphState) -> GraphState:
            state["result"] = orchestrator.knowledge.run(state["message"])
            return state

        def task_node(state: GraphState) -> GraphState:
            state["result"] = orchestrator.task.run(state["message"])
            return state

        def meeting_node(state: GraphState) -> GraphState:
            summarised = orchestrator.meeting.summarise(state["message"])
            state["result"] = {"agent_type": "meeting", **summarised}
            return state

        def reporting_node(state: GraphState) -> GraphState:
            # DB-less stub for graph visualisation / unit tests
            state["result"] = {
                "agent_type": "reporting",
                "reply": "Reporting node requires an active DB session via OpsOrchestrator.handle_chat.",
            }
            return state

        def route(state: GraphState) -> str:
            return state.get("intent", "knowledge")

        graph = StateGraph(GraphState)
        graph.add_node("classify", classify_node)
        graph.add_node("knowledge", knowledge_node)
        graph.add_node("task", task_node)
        graph.add_node("meeting", meeting_node)
        graph.add_node("reporting", reporting_node)
        graph.set_entry_point("classify")
        graph.add_conditional_edges(
            "classify",
            route,
            {
                "knowledge": "knowledge",
                "task": "task",
                "meeting": "meeting",
                "reporting": "reporting",
            },
        )
        for node in ("knowledge", "task", "meeting", "reporting"):
            graph.add_edge(node, END)
        return graph.compile()
    except Exception as exc:  # noqa: BLE001
        logger.info("LangGraph router unavailable: %s", exc)
        return None
