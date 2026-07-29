"""Meeting summarisation endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.agents.meeting_agent import MeetingAgent
from backend.core.deps import get_current_user, get_db
from backend.models.schemas import MeetingSummariseRequest, MeetingSummaryResponse, TaskCreate, TaskOut
from backend.models.user import User
from backend.services.automation_service import trigger_meeting_summary
from backend.services.task_service import create_task_and_notify

router = APIRouter(prefix="/meetings", tags=["Meetings"])
agent = MeetingAgent()


@router.post("/summarise", response_model=MeetingSummaryResponse)
async def summarise_meeting(
    payload: MeetingSummariseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeetingSummaryResponse:
    result = agent.summarise(payload.transcript, title=payload.title)

    created: list[TaskOut] = []
    if payload.create_tasks:
        for item in result["action_items"]:
            deadline = None
            if item.deadline:
                try:
                    deadline = datetime.fromisoformat(item.deadline)
                except ValueError:
                    deadline = None
            priority = item.priority if item.priority in {"low", "medium", "high", "critical"} else "medium"
            task = await create_task_and_notify(
                db,
                TaskCreate(
                    title=item.title,
                    description=f"Action item from meeting: {payload.title}",
                    priority=priority,
                    owner=item.owner,
                    deadline=deadline,
                    source="meeting",
                    confidence=result["confidence"],
                ),
                current_user,
            )
            created.append(TaskOut.model_validate(task))

    await trigger_meeting_summary(
        {
            "title": payload.title,
            "summary": result["summary"],
            "key_decisions": result["key_decisions"],
            "action_items": [a.model_dump() for a in result["action_items"]],
            "tasks_created": len(created),
        }
    )

    return MeetingSummaryResponse(
        title=payload.title,
        summary=result["summary"],
        key_decisions=result["key_decisions"],
        action_items=result["action_items"],
        confidence=result["confidence"],
        tasks_created=created,
    )
