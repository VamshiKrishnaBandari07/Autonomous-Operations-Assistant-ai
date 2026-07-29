"""Task CRUD and persistence helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models.schemas import TaskCreate, TaskUpdate
from backend.models.task import Task
from backend.models.user import User
from backend.services.automation_service import trigger_task_created


def create_task(db: Session, payload: TaskCreate, creator: User) -> Task:
    task = Task(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        owner=payload.owner,
        deadline=payload.deadline,
        source=payload.source,
        confidence=payload.confidence,
        creator_id=creator.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


async def create_task_and_notify(db: Session, payload: TaskCreate, creator: User) -> Task:
    task = create_task(db, payload, creator)
    await trigger_task_created(
        {
            "task_id": task.id,
            "title": task.title,
            "priority": task.priority,
            "owner": task.owner,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "source": task.source,
        }
    )
    return task


def list_tasks(
    db: Session,
    status: str | None = None,
    priority: str | None = None,
) -> list[Task]:
    query = db.query(Task).order_by(Task.created_at.desc())
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    return query.all()


def get_task(db: Session, task_id: int) -> Task | None:
    return db.query(Task).filter(Task.id == task_id).first()


def update_task(db: Session, task_id: int, payload: TaskUpdate) -> Task | None:
    task = get_task(db, task_id)
    if not task:
        return None
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(task, key, value)
    task.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: int) -> bool:
    task = get_task(db, task_id)
    if not task:
        return False
    db.delete(task)
    db.commit()
    return True
