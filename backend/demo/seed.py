"""
OpsFlow AI — Public portfolio demo mode.

When DEMO_MODE=true:
  - Seed sample documents into the RAG knowledge base
  - Seed sample tasks / demo employees
  - Simulate n8n workflow execution (no Slack/SMTP required)
  - Expose recruiter-friendly demo metrics
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.models.document import Document
from backend.models.employee import Employee
from backend.models.task import Task
from backend.models.user import User
from backend.rag.ingest import index_document_text
from backend.rag.loaders import extract_text

logger = logging.getLogger(__name__)

DEMO_DOCUMENTS = [
    "employee_handbook.txt",
    "company_policy.txt",
    "company_policy.pdf",
    "sample_meeting_transcript.txt",
]

# Recruiter-facing baseline metrics (blended with live activity)
DEMO_METRICS_BASELINE = {
    "ai_queries_completed": 245,
    "automated_tasks_created": 128,
    "estimated_hours_saved": 42.0,
    "workflow_success_rate": 96.0,
    "documents_indexed_demo": 3,
    "onboardings_completed": 18,
}


def demo_data_dir() -> Path:
    settings = get_settings()
    return Path(settings.demo_data_dir)


def workflow_log_path() -> Path:
    path = Path("data/demo_workflow_log.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def append_workflow_simulation(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist a simulated automation run for the demo UI."""
    entry = {
        "event": event,
        "simulated": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "notification": payload.get("slack_message")
        or payload.get("notification")
        or f"[Demo] Simulated n8n workflow: {event}",
        "summary": {
            k: payload.get(k)
            for k in ("employee", "welcome_email", "accounts_checklist", "hr_tasks", "title")
            if k in payload
        },
    }
    path = workflow_log_path()
    existing: list[dict[str, Any]] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []
    existing.insert(0, entry)
    path.write_text(json.dumps(existing[:50], indent=2, default=str), encoding="utf-8")
    logger.info("Demo workflow simulated: %s", event)
    return entry


def list_workflow_simulations(limit: int = 10) -> list[dict[str, Any]]:
    path = workflow_log_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data[:limit]
    except json.JSONDecodeError:
        return []


def _copy_and_index_doc(db: Session, owner: User, filename: str) -> Document | None:
    settings = get_settings()
    src = demo_data_dir() / filename
    if not src.exists():
        logger.warning("Demo file missing: %s", src)
        return None

    existing = (
        db.query(Document)
        .filter(Document.original_name == filename, Document.status == "indexed")
        .first()
    )
    if existing:
        return existing

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest_name = f"demo_{filename}"
    dest = upload_dir / dest_name
    shutil.copy2(src, dest)

    ext = src.suffix.lower().lstrip(".")
    doc = Document(
        filename=dest_name,
        original_name=filename,
        file_type=ext if ext != "pdf" else "pdf",
        file_path=str(dest),
        file_size=dest.stat().st_size,
        status="pending",
        owner_id=owner.id,
        summary="",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        # Prefer sibling .txt for PDF so RAG works without PDF text extraction issues
        if ext == "pdf":
            txt_sibling = demo_data_dir() / "company_policy.txt"
            text = txt_sibling.read_text(encoding="utf-8") if txt_sibling.exists() else extract_text(str(dest), "pdf")
        else:
            text = extract_text(str(dest), ext)
        chunk_count, summary = index_document_text(doc.id, doc.original_name, text)
        doc.chunk_count = chunk_count
        doc.summary = summary
        doc.status = "indexed"
        doc.indexed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(doc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Demo document index failed: %s", filename)
        doc.status = "failed"
        doc.summary = f"Demo indexing failed: {exc}"
        db.commit()
    return doc


def _seed_tasks(db: Session, owner: User) -> int:
    tasks_file = demo_data_dir() / "sample_tasks.json"
    if not tasks_file.exists():
        return 0
    raw = json.loads(tasks_file.read_text(encoding="utf-8"))
    created = 0
    for item in raw:
        exists = (
            db.query(Task)
            .filter(Task.title == item["title"], Task.source == "demo")
            .first()
        )
        if exists:
            continue
        task = Task(
            title=item["title"],
            description="Seeded demo task for portfolio showcase",
            priority=item.get("priority", "medium"),
            status=item.get("status", "open"),
            owner=item.get("owner", "Operations"),
            source="demo",
            confidence=0.9,
            creator_id=owner.id,
        )
        db.add(task)
        created += 1
    if created:
        db.commit()
    return created


def _seed_employees(db: Session, owner: User) -> int:
    samples = [
        {
            "full_name": "Aisha Rahman",
            "email": "aisha.rahman@opsflow-demo.ai",
            "role": "Operations Analyst",
            "department": "Operations",
            "manager": "Jordan Lee",
            "start_date": "2026-08-04",
        },
        {
            "full_name": "Marcus Chen",
            "email": "marcus.chen@opsflow-demo.ai",
            "role": "IT Support Specialist",
            "department": "IT",
            "manager": "Priya Shah",
            "start_date": "2026-08-11",
        },
    ]
    created = 0
    for sample in samples:
        if db.query(Employee).filter(Employee.email == sample["email"]).first():
            continue
        emp = Employee(
            full_name=sample["full_name"],
            email=sample["email"],
            role=sample["role"],
            department=sample["department"],
            manager=sample["manager"],
            start_date=sample["start_date"],
            status="demo_seeded",
            welcome_email_subject=f"Welcome to the team, {sample['full_name']}!",
            welcome_email_body=(
                f"Hi {sample['full_name']},\n\n"
                "Welcome to OpsFlow Technologies (demo). "
                "Your accounts checklist and HR tasks are ready.\n\n"
                "— People Operations"
            ),
            accounts_checklist=json.dumps(
                [
                    {"item": "Corporate email", "system": "Google Workspace", "owner": "IT", "status": "pending"},
                    {"item": "Slack invite", "system": "Slack", "owner": "IT", "status": "pending"},
                    {"item": "HRIS profile", "system": "HRIS", "owner": "HR", "status": "pending"},
                ]
            ),
            created_by_id=owner.id,
        )
        db.add(emp)
        created += 1
    if created:
        db.commit()
    return created


def seed_demo_environment(db: Session, owner: User) -> dict[str, Any]:
    """Idempotent demo seed used on startup when DEMO_MODE=true."""
    settings = get_settings()
    if not settings.demo_mode:
        return {"seeded": False, "reason": "DEMO_MODE disabled"}

    docs = []
    for name in DEMO_DOCUMENTS:
        doc = _copy_and_index_doc(db, owner, name)
        if doc:
            docs.append({"id": doc.id, "name": doc.original_name, "status": doc.status})

    tasks_created = _seed_tasks(db, owner)
    employees_created = _seed_employees(db, owner)

    result = {
        "seeded": True,
        "documents": docs,
        "tasks_created": tasks_created,
        "employees_created": employees_created,
        "demo_prompts": [
            "How many annual leave days do employees receive?",
            "Are shared admin accounts allowed?",
            "How quickly must production incidents be acknowledged?",
        ],
    }
    logger.info("Demo environment ready: %s", result)
    return result


def blend_demo_analytics(live: dict[str, Any]) -> dict[str, Any]:
    """Overlay recruiter-friendly demo KPIs while preserving live counters."""
    base = DEMO_METRICS_BASELINE
    return {
        **live,
        "demo_mode": True,
        "ai_queries_completed": max(live.get("total_queries", 0), base["ai_queries_completed"]),
        "automated_tasks_created": max(live.get("total_tasks", 0), base["automated_tasks_created"]),
        "estimated_hours_saved": max(
            float(live.get("estimated_hours_saved", 0)), base["estimated_hours_saved"]
        ),
        "workflow_success_rate": base["workflow_success_rate"],
        "onboardings_completed": max(
            live.get("reports_generated", 0), base["onboardings_completed"]
        ),
        "demo_highlights": [
            "Knowledge Agent answers policy questions with citations",
            "Onboarding Agent drafts welcome emails in seconds",
            "Task Agent converts meetings into owned action items",
            "n8n workflows simulated for Slack/email without credentials",
        ],
    }
