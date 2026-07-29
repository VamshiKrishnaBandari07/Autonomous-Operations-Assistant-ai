"""Employee ORM model for onboarding automation."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    role: Mapped[str] = mapped_column(String(128), default="Employee")
    department: Mapped[str] = mapped_column(String(128), default="Operations")
    start_date: Mapped[str] = mapped_column(String(32), default="")
    manager: Mapped[str] = mapped_column(String(128), default="Unassigned")
    status: Mapped[str] = mapped_column(String(32), default="onboarding")
    welcome_email_subject: Mapped[str] = mapped_column(String(255), default="")
    welcome_email_body: Mapped[str] = mapped_column(Text, default="")
    accounts_checklist: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
