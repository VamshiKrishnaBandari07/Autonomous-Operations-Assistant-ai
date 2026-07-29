"""Task management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.agents.task_agent import TaskAgent
from backend.core.deps import get_current_user, get_db
from backend.models.schemas import TaskCreate, TaskExtractRequest, TaskOut, TaskUpdate
from backend.models.task import Task
from backend.models.user import User
from backend.services import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=list[TaskOut])
def list_tasks(
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Task]:
    return task_service.list_tasks(db, status=status_filter, priority=priority)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    return await task_service.create_task_and_notify(db, payload, current_user)


@router.post("/extract", response_model=list[TaskOut], status_code=status.HTTP_201_CREATED)
async def extract_tasks_from_text(
    payload: TaskExtractRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Task]:
    agent = TaskAgent()
    extracted = agent.extract(payload.text)
    created: list[Task] = []
    for item in extracted:
        item.source = "chat"
        created.append(await task_service.create_task_and_notify(db, item, current_user))
    return created


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    task = task_service.update_task(db, task_id, payload)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if not task_service.delete_task(db, task_id):
        raise HTTPException(status_code=404, detail="Task not found")
