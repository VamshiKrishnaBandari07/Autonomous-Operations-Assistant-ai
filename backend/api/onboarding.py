"""Employee onboarding API — new hire automation pipeline."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.deps import get_current_user, get_db
from backend.models.employee import Employee
from backend.models.schemas import (
    AccountChecklistItem,
    EmployeeCreate,
    EmployeeOut,
    OnboardingResponse,
    TaskOut,
    WelcomeEmailOut,
)
from backend.models.user import User
from backend.services import onboarding_service

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


def _employee_to_out(employee: Employee) -> EmployeeOut:
    try:
        checklist_raw = json.loads(employee.accounts_checklist or "[]")
        checklist = [AccountChecklistItem(**item) for item in checklist_raw]
    except (json.JSONDecodeError, TypeError, ValueError):
        checklist = []
    return EmployeeOut(
        id=employee.id,
        full_name=employee.full_name,
        email=employee.email,
        role=employee.role,
        department=employee.department,
        start_date=employee.start_date,
        manager=employee.manager,
        status=employee.status,
        welcome_email_subject=employee.welcome_email_subject,
        welcome_email_body=employee.welcome_email_body,
        accounts_checklist=checklist,
        created_at=employee.created_at,
    )


@router.post(
    "/employees",
    response_model=OnboardingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger new-employee onboarding pipeline",
)
async def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingResponse:
    """
    Pipeline:
      New employee added → welcome email (AI) → accounts checklist
      → Task Agent assigns HR tasks → n8n Slack/email notification
    """
    existing = (
        db.query(Employee).filter(Employee.email == payload.email.strip().lower()).first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Employee with email '{payload.email}' already exists",
        )

    result = await onboarding_service.OnboardingService().onboard_employee(
        db,
        current_user,
        payload.model_dump(),
    )
    employee = result["employee"]
    return OnboardingResponse(
        employee=_employee_to_out(employee),
        welcome_email=WelcomeEmailOut(**result["welcome_email"]),
        accounts_checklist=[AccountChecklistItem(**i) for i in result["accounts_checklist"]],
        tasks_created=[TaskOut.model_validate(t) for t in result["tasks"]],
        n8n_triggered=result["n8n_triggered"],
        slack_message=result["slack_message"],
        confidence=float(result["confidence"]),
        pipeline=[
            "1. New employee added",
            "2. AI Agent: create welcome email",
            "3. Build accounts checklist (n8n provisions)",
            "4. Task Agent: assign HR tasks",
            "5. Notification: send Slack message",
        ],
    )


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmployeeOut]:
    return [_employee_to_out(e) for e in onboarding_service.list_employees(db)]


@router.get("/employees/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployeeOut:
    employee = onboarding_service.get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return _employee_to_out(employee)
