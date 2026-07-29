"""Analytics aggregation for the Operations dashboard."""

from __future__ import annotations

from collections import Counter

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.models.conversation import Message
from backend.models.document import Document
from backend.models.report import Report
from backend.models.schemas import AnalyticsSummary
from backend.models.task import Task


def build_analytics(db: Session) -> AnalyticsSummary:
    settings = get_settings()

    total_queries = (
        db.query(func.count(Message.id)).filter(Message.role == "user").scalar() or 0
    )
    assistant_msgs = db.query(Message).filter(Message.role == "assistant").all()
    total_tasks = db.query(func.count(Task.id)).scalar() or 0
    open_tasks = (
        db.query(func.count(Task.id)).filter(Task.status.in_(["open", "in_progress"])).scalar()
        or 0
    )
    completed_tasks = (
        db.query(func.count(Task.id)).filter(Task.status == "done").scalar() or 0
    )
    documents_indexed = (
        db.query(func.count(Document.id)).filter(Document.status == "indexed").scalar() or 0
    )
    reports_generated = db.query(func.count(Report.id)).scalar() or 0

    minutes_saved = (
        total_queries * settings.avg_minutes_saved_per_query
        + total_tasks * settings.avg_minutes_saved_per_task
    )
    hours_saved = round(minutes_saved / 60.0, 1)

    confidences = [m.confidence for m in assistant_msgs if m.confidence]
    avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

    agent_counter: Counter[str] = Counter(m.agent_type for m in assistant_msgs)
    queries_by_agent = dict(agent_counter)

    # Heuristic classification of common request themes from user messages
    user_msgs = db.query(Message).filter(Message.role == "user").all()
    theme_counter: Counter[str] = Counter()
    for msg in user_msgs:
        text = (msg.content or "").lower()
        if any(k in text for k in ("task", "todo", "assign", "deadline")):
            theme_counter["Task creation"] += 1
        elif any(k in text for k in ("meeting", "transcript", "action item")):
            theme_counter["Meeting follow-up"] += 1
        elif any(k in text for k in ("report", "weekly", "kpi", "metric")):
            theme_counter["Reporting"] += 1
        elif any(k in text for k in ("policy", "document", "how do", "what is", "where")):
            theme_counter["Knowledge lookup"] += 1
        else:
            theme_counter["General operations"] += 1

    common_request_types = [
        {"type": name, "count": count} for name, count in theme_counter.most_common(6)
    ]

    tasks = db.query(Task).all()
    tasks_by_priority = dict(Counter(t.priority for t in tasks))
    tasks_by_status = dict(Counter(t.status for t in tasks))

    return AnalyticsSummary(
        total_queries=total_queries,
        total_tasks=total_tasks,
        open_tasks=open_tasks,
        completed_tasks=completed_tasks,
        documents_indexed=documents_indexed,
        reports_generated=reports_generated,
        estimated_hours_saved=hours_saved,
        avg_confidence=avg_confidence,
        queries_by_agent=queries_by_agent,
        common_request_types=common_request_types,
        tasks_by_priority=tasks_by_priority,
        tasks_by_status=tasks_by_status,
    )
