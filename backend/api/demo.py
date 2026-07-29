"""Public demo status and showcase endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.deps import get_current_user, get_db
from backend.demo.seed import (
    DEMO_METRICS_BASELINE,
    blend_demo_analytics,
    list_workflow_simulations,
    seed_demo_environment,
)
from backend.models.user import User
from backend.services.analytics_service import build_analytics
from backend.services.user_service import ensure_admin_user

router = APIRouter(prefix="/demo", tags=["Demo"])


class DemoStatus(BaseModel):
    demo_mode: bool
    seeded: bool = False
    documents: list[dict[str, Any]] = Field(default_factory=list)
    sample_prompts: list[str] = Field(default_factory=list)
    workflow_simulations: list[dict[str, Any]] = Field(default_factory=list)
    metrics_baseline: dict[str, Any] = Field(default_factory=dict)
    safety_notes: list[str] = Field(default_factory=list)


class DemoMetrics(BaseModel):
    demo_mode: bool
    ai_queries_completed: int
    automated_tasks_created: int
    estimated_hours_saved: float
    workflow_success_rate: float
    onboardings_completed: int
    live_total_queries: int
    live_total_tasks: int
    demo_highlights: list[str]
    queries_by_agent: dict[str, int]
    common_request_types: list[dict[str, Any]]
    tasks_by_priority: dict[str, int]
    tasks_by_status: dict[str, int]


@router.get("/status", response_model=DemoStatus)
def demo_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DemoStatus:
    settings = get_settings()
    if not settings.demo_mode:
        return DemoStatus(
            demo_mode=False,
            safety_notes=["DEMO_MODE is disabled. Live data only."],
        )

    # Ensure seed has run (idempotent)
    result = seed_demo_environment(db, current_user)
    return DemoStatus(
        demo_mode=True,
        seeded=bool(result.get("seeded")),
        documents=result.get("documents", []),
        sample_prompts=result.get("demo_prompts", []),
        workflow_simulations=list_workflow_simulations(8),
        metrics_baseline=DEMO_METRICS_BASELINE,
        safety_notes=[
            "Portfolio demo uses fictional OpsFlow Technologies data only.",
            "No real Slack/email credentials required — workflows are simulated.",
            "API keys stay in environment variables and are never returned by the API.",
            "Do not upload confidential company documents to a public demo instance.",
        ],
    )


@router.post("/seed", response_model=DemoStatus)
def reseeds_demo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DemoStatus:
    result = seed_demo_environment(db, current_user or ensure_admin_user(db))
    settings = get_settings()
    return DemoStatus(
        demo_mode=settings.demo_mode,
        seeded=bool(result.get("seeded")),
        documents=result.get("documents", []),
        sample_prompts=result.get("demo_prompts", []),
        workflow_simulations=list_workflow_simulations(8),
        metrics_baseline=DEMO_METRICS_BASELINE,
        safety_notes=["Demo data re-seeded (idempotent)."],
    )


@router.get("/metrics", response_model=DemoMetrics)
def demo_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DemoMetrics:
    live = build_analytics(db).model_dump()
    settings = get_settings()
    if settings.demo_mode:
        blended = blend_demo_analytics(live)
    else:
        blended = {
            **live,
            "demo_mode": False,
            "ai_queries_completed": live["total_queries"],
            "automated_tasks_created": live["total_tasks"],
            "workflow_success_rate": 100.0 if live["total_tasks"] else 0.0,
            "onboardings_completed": 0,
            "demo_highlights": [],
        }
    return DemoMetrics(
        demo_mode=bool(blended.get("demo_mode")),
        ai_queries_completed=int(blended["ai_queries_completed"]),
        automated_tasks_created=int(blended["automated_tasks_created"]),
        estimated_hours_saved=float(blended["estimated_hours_saved"]),
        workflow_success_rate=float(blended["workflow_success_rate"]),
        onboardings_completed=int(blended.get("onboardings_completed", 0)),
        live_total_queries=live["total_queries"],
        live_total_tasks=live["total_tasks"],
        demo_highlights=list(blended.get("demo_highlights", [])),
        queries_by_agent=live.get("queries_by_agent") or {"knowledge": 98, "task": 64, "meeting": 47, "reporting": 36},
        common_request_types=live.get("common_request_types")
        or [
            {"type": "Knowledge lookup", "count": 112},
            {"type": "Task creation", "count": 64},
            {"type": "Meeting follow-up", "count": 47},
            {"type": "Onboarding", "count": 22},
        ],
        tasks_by_priority=live.get("tasks_by_priority")
        or {"high": 34, "medium": 61, "low": 22, "critical": 11},
        tasks_by_status=live.get("tasks_by_status")
        or {"open": 48, "in_progress": 29, "done": 51},
    )
