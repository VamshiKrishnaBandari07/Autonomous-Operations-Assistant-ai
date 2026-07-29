"""Operational report endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.agents.reporting_agent import ReportingAgent
from backend.core.deps import get_current_user, get_db
from backend.models.report import Report
from backend.models.schemas import ReportGenerateRequest, ReportOut
from backend.models.user import User

router = APIRouter(prefix="/reports", tags=["Reports"])
agent = ReportingAgent()


def _to_out(report: Report) -> ReportOut:
    try:
        bottlenecks = json.loads(report.bottlenecks or "[]")
    except json.JSONDecodeError:
        bottlenecks = []
    try:
        trends = json.loads(report.trends or "[]")
    except json.JSONDecodeError:
        trends = []
    return ReportOut(
        id=report.id,
        title=report.title,
        report_type=report.report_type,
        summary=report.summary,
        content=report.content,
        bottlenecks=bottlenecks,
        trends=trends,
        created_at=report.created_at,
    )


@router.post("/generate", response_model=ReportOut)
def generate_report(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportOut:
    result = agent.generate(db, report_type=payload.report_type)
    report = Report(
        title=payload.title or result["title"],
        report_type=payload.report_type,
        summary=result["summary"],
        content=result["content"],
        bottlenecks=json.dumps(result["bottlenecks"]),
        trends=json.dumps(result["trends"]),
        author_id=current_user.id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _to_out(report)


@router.get("", response_model=list[ReportOut])
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReportOut]:
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    return [_to_out(r) for r in reports]


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportOut:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_out(report)
