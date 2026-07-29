"""Conversation persistence for chat history."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from backend.models.conversation import Conversation, Message
from backend.models.schemas import Citation
from backend.models.user import User


def create_conversation(db: Session, user: User, title: str = "Operations Chat") -> Conversation:
    convo = Conversation(title=title[:255], user_id=user.id)
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


def get_conversation(db: Session, conversation_id: int) -> Conversation | None:
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def list_conversations(db: Session, user_id: int) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def add_message(
    db: Session,
    conversation: Conversation,
    role: str,
    content: str,
    agent_type: str = "orchestrator",
    confidence: float = 0.0,
    citations: list[Citation] | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation.id,
        role=role,
        content=content,
        agent_type=agent_type,
        confidence=confidence,
        citations=json.dumps([c.model_dump() for c in (citations or [])]),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def parse_citations(raw: str) -> list[Citation]:
    try:
        data = json.loads(raw or "[]")
        return [Citation(**item) for item in data]
    except (json.JSONDecodeError, TypeError, ValueError):
        return []
