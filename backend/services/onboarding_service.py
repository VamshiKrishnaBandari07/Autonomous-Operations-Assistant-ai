"""
Employee onboarding orchestration service.

Pipeline:
  New employee added
    → Onboarding Agent: create welcome email
    → n8n: create accounts checklist (+ Slack notify)
    → Task Agent: assign HR tasks
    → Notification payload confirmed
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from backend.agents.onboarding_agent import OnboardingAgent
from backend.agents.task_agent import TaskAgent
from backend.models.employee import Employee
from backend.models.schemas import TaskCreate
from backend.models.task import Task
from backend.models.user import User
from backend.services.automation_service import trigger_employee_onboarding
from backend.services.task_service import create_task_and_notify

logger = logging.getLogger(__name__)

# Canonical HR onboarding tasks (Task Agent expands / personalises these)
HR_TASK_SEEDS = [
    {
        "title": "Send welcome pack and first-week agenda",
        "priority": "high",
        "owner": "HR",
        "deadline_days": 1,
    },
    {
        "title": "Schedule new-hire orientation",
        "priority": "high",
        "owner": "HR",
        "deadline_days": 2,
    },
    {
        "title": "Complete HRIS profile and payroll setup",
        "priority": "high",
        "owner": "HR",
        "deadline_days": 3,
    },
    {
        "title": "Confirm benefits enrollment invitation",
        "priority": "medium",
        "owner": "HR",
        "deadline_days": 5,
    },
    {
        "title": "Assign buddy / onboarding buddy intro",
        "priority": "medium",
        "owner": "HR",
        "deadline_days": 2,
    },
]


def _hr_task_prompt(employee: dict[str, Any]) -> str:
    seeds = "\n".join(
        f"- {s['title']} (owner={s['owner']}, priority={s['priority']}, due in {s['deadline_days']} days)"
        for s in HR_TASK_SEEDS
    )
    return (
        f"New employee onboarding for {employee['full_name']} "
        f"({employee.get('role')}, {employee.get('department')}, "
        f"manager={employee.get('manager')}, start={employee.get('start_date')}).\n"
        f"Create HR onboarding tasks based on this checklist:\n{seeds}\n"
        "Personalise task titles to include the employee name where useful."
    )


class OnboardingService:
    def __init__(self) -> None:
        self.onboarding_agent = OnboardingAgent()
        self.task_agent = TaskAgent()

    async def onboard_employee(
        self,
        db: Session,
        creator: User,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Run the full onboarding automation pipeline."""
        employee = Employee(
            full_name=payload["full_name"],
            email=payload["email"],
            role=payload.get("role") or "Employee",
            department=payload.get("department") or "Operations",
            start_date=payload.get("start_date") or "",
            manager=payload.get("manager") or "Unassigned",
            status="onboarding",
            created_by_id=creator.id,
        )
        db.add(employee)
        db.commit()
        db.refresh(employee)

        employee_dict = {
            "id": employee.id,
            "full_name": employee.full_name,
            "email": employee.email,
            "role": employee.role,
            "department": employee.department,
            "start_date": employee.start_date,
            "manager": employee.manager,
        }

        # 1) AI Agent → welcome email
        welcome = self.onboarding_agent.create_welcome_email(employee_dict)
        employee.welcome_email_subject = welcome["subject"]
        employee.welcome_email_body = welcome["body"]

        # 2) Accounts checklist (sent to n8n)
        checklist = self.onboarding_agent.build_accounts_checklist(employee_dict)
        employee.accounts_checklist = json.dumps(checklist)
        db.commit()
        db.refresh(employee)

        # 3) Task Agent → assign HR tasks
        created_tasks: list[Task] = []
        from backend.agents.llm import llm_available
        from datetime import datetime, timedelta, timezone

        if llm_available():
            extracted = self.task_agent.extract(_hr_task_prompt(employee_dict))
        else:
            extracted = []

        if not extracted:
            # Deterministic HR pack when LLM is offline or returns nothing
            for seed in HR_TASK_SEEDS:
                extracted.append(
                    TaskCreate(
                        title=f"{seed['title']} — {employee.full_name}",
                        description=f"Onboarding HR task for {employee.full_name} ({employee.email})",
                        priority=seed["priority"],
                        owner=seed["owner"],
                        deadline=datetime.now(timezone.utc) + timedelta(days=seed["deadline_days"]),
                        source="onboarding",
                        confidence=0.8,
                    )
                )

        for item in extracted:
            item.source = "onboarding"
            if item.owner.lower() in {"unassigned", ""}:
                item.owner = "HR"
            task = await create_task_and_notify(db, item, creator)
            created_tasks.append(task)

        # 4) n8n → accounts checklist workflow + Slack notification
        n8n_payload = {
            "event": "employee.created",
            "employee": employee_dict,
            "welcome_email": {
                "subject": welcome["subject"],
                "body": welcome["body"],
                "to": employee.email,
            },
            "accounts_checklist": checklist,
            "hr_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "owner": t.owner,
                    "priority": t.priority,
                    "deadline": t.deadline.isoformat() if t.deadline else None,
                }
                for t in created_tasks
            ],
            "slack_message": (
                f"🎉 New hire onboarding started for *{employee.full_name}* "
                f"({employee.role}, {employee.department}). "
                f"Welcome email drafted · {len(checklist)} account items · "
                f"{len(created_tasks)} HR tasks assigned."
            ),
        }
        n8n_ok = await trigger_employee_onboarding(n8n_payload)

        employee.status = "onboarding_triggered"
        db.commit()
        db.refresh(employee)

        logger.info(
            "Onboarding pipeline complete employee_id=%s tasks=%s n8n=%s",
            employee.id,
            len(created_tasks),
            n8n_ok,
        )

        return {
            "employee": employee,
            "welcome_email": welcome,
            "accounts_checklist": checklist,
            "tasks": created_tasks,
            "n8n_triggered": n8n_ok,
            "slack_message": n8n_payload["slack_message"],
            "confidence": welcome.get("confidence", 0.7),
        }


def list_employees(db: Session) -> list[Employee]:
    return db.query(Employee).order_by(Employee.created_at.desc()).all()


def get_employee(db: Session, employee_id: int) -> Employee | None:
    return db.query(Employee).filter(Employee.id == employee_id).first()
