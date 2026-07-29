"""Chat / Operations AI endpoints with conversation history."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.agents.orchestrator import OpsOrchestrator
from backend.core.deps import get_current_user, get_db
from backend.models.schemas import (
    ChatRequest,
    ChatResponse,
    Citation,
    ConversationOut,
    MessageOut,
    TaskOut,
)
from backend.models.user import User
from backend.services import conversation_service

router = APIRouter(prefix="/chat", tags=["Chat"])
orchestrator = OpsOrchestrator()


def _message_to_out(msg) -> MessageOut:
    try:
        citations_raw = json.loads(msg.citations or "[]")
        citations = [Citation(**c) for c in citations_raw]
    except Exception:  # noqa: BLE001
        citations = []
    return MessageOut(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        agent_type=msg.agent_type,
        confidence=msg.confidence,
        citations=citations,
        created_at=msg.created_at,
    )


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    if payload.conversation_id:
        conversation = conversation_service.get_conversation(db, payload.conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        title = payload.message.strip()[:60] or "Operations Chat"
        conversation = conversation_service.create_conversation(db, current_user, title=title)

    conversation_service.add_message(
        db, conversation, role="user", content=payload.message, agent_type="user"
    )

    result = await orchestrator.handle_chat(
        message=payload.message,
        db=db,
        user=current_user,
        use_rag=payload.use_rag,
    )

    citations = result.get("citations") or []
    conversation_service.add_message(
        db,
        conversation,
        role="assistant",
        content=result["reply"],
        agent_type=result.get("agent_type", "orchestrator"),
        confidence=float(result.get("confidence", 0.0)),
        citations=citations,
    )

    tasks = [TaskOut.model_validate(t) for t in result.get("tasks_created", [])]
    return ChatResponse(
        conversation_id=conversation.id,
        reply=result["reply"],
        agent_type=result.get("agent_type", "orchestrator"),
        confidence=float(result.get("confidence", 0.0)),
        citations=citations,
        tasks_created=tasks,
    )


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationOut]:
    convos = conversation_service.list_conversations(db, current_user.id)
    out: list[ConversationOut] = []
    for c in convos:
        out.append(
            ConversationOut(
                id=c.id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
                messages=[_message_to_out(m) for m in c.messages],
            )
        )
    return out


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationOut:
    convo = conversation_service.get_conversation(db, conversation_id)
    if not convo or convo.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationOut(
        id=convo.id,
        title=convo.title,
        created_at=convo.created_at,
        updated_at=convo.updated_at,
        messages=[_message_to_out(m) for m in convo.messages],
    )
