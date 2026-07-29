"""Pydantic request/response schemas for OpsFlow AI APIs."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    is_admin: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


class DocumentOut(BaseModel):
    id: int
    original_name: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    summary: str
    created_at: datetime
    indexed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: List[DocumentOut]
    total: int


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    priority: str = "medium"
    owner: str = "Unassigned"
    deadline: Optional[datetime] = None
    source: str = "manual"
    confidence: float = 1.0

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        value = v.lower().strip()
        if value not in allowed:
            raise ValueError(f"priority must be one of {allowed}")
        return value


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    deadline: Optional[datetime] = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    priority: str
    status: str
    owner: str
    deadline: Optional[datetime] = None
    source: str
    confidence: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskExtractRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=8000)


# ---------------------------------------------------------------------------
# Chat / RAG
# ---------------------------------------------------------------------------


class Citation(BaseModel):
    document_name: str
    chunk_id: str = ""
    excerpt: str
    score: float = 0.0


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    conversation_id: Optional[int] = None
    use_rag: bool = True


class ChatResponse(BaseModel):
    conversation_id: int
    reply: str
    agent_type: str
    confidence: float
    citations: List[Citation] = []
    tasks_created: List[TaskOut] = []


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    agent_type: str
    confidence: float
    citations: List[Citation] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageOut] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Meetings
# ---------------------------------------------------------------------------


class MeetingSummariseRequest(BaseModel):
    transcript: str = Field(..., min_length=20, max_length=100_000)
    title: str = "Meeting Summary"
    create_tasks: bool = True


class ActionItem(BaseModel):
    title: str
    owner: str = "Unassigned"
    deadline: Optional[str] = None
    priority: str = "medium"


class MeetingSummaryResponse(BaseModel):
    title: str
    summary: str
    key_decisions: List[str]
    action_items: List[ActionItem]
    confidence: float
    tasks_created: List[TaskOut] = []


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


class ReportGenerateRequest(BaseModel):
    report_type: str = "weekly"
    title: Optional[str] = None


class ReportOut(BaseModel):
    id: int
    title: str
    report_type: str
    summary: str
    content: str
    bottlenecks: List[Any] = []
    trends: List[Any] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Onboarding / Employees
# ---------------------------------------------------------------------------


class EmployeeCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=128)
    email: str = Field(..., min_length=5, max_length=255)
    role: str = Field(default="Employee", max_length=128)
    department: str = Field(default="Operations", max_length=128)
    start_date: str = Field(default="", max_length=32)
    manager: str = Field(default="Unassigned", max_length=128)


class WelcomeEmailOut(BaseModel):
    subject: str
    body: str
    confidence: float = 0.0


class AccountChecklistItem(BaseModel):
    item: str
    system: str
    owner: str
    employee: str = ""
    employee_email: str = ""
    status: str = "pending"


class EmployeeOut(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    department: str
    start_date: str
    manager: str
    status: str
    welcome_email_subject: str
    welcome_email_body: str
    accounts_checklist: List[AccountChecklistItem] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class OnboardingResponse(BaseModel):
    employee: EmployeeOut
    welcome_email: WelcomeEmailOut
    accounts_checklist: List[AccountChecklistItem]
    tasks_created: List[TaskOut]
    n8n_triggered: bool
    slack_message: str
    confidence: float
    pipeline: List[str]


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class AnalyticsSummary(BaseModel):
    total_queries: int
    total_tasks: int
    open_tasks: int
    completed_tasks: int
    documents_indexed: int
    reports_generated: int
    estimated_hours_saved: float
    avg_confidence: float
    queries_by_agent: dict[str, int]
    common_request_types: List[dict[str, Any]]
    tasks_by_priority: dict[str, int]
    tasks_by_status: dict[str, int]


# ---------------------------------------------------------------------------
# Settings / Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    vector_store: str
    n8n_enabled: bool


class SystemSettingsOut(BaseModel):
    app_name: str
    openai_model: str
    embedding_model: str
    vector_store: str
    chunk_size: int
    top_k_retrieval: int
    n8n_enabled: bool
    max_upload_size_mb: int
    allowed_extensions: List[str]
