"""Analytics and system settings endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.agents.llm import llm_available
from backend.core.config import get_settings
from backend.core.deps import get_current_user, get_db
from backend.models.schemas import AnalyticsSummary, HealthResponse, SystemSettingsOut
from backend.models.user import User
from backend.rag.vector_store import get_vector_store
from backend.services.analytics_service import build_analytics

router = APIRouter(tags=["System"])


def _active_vector_backend() -> str:
    store = get_vector_store()
    return type(store).__name__.replace("VectorStore", "").lower()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.app_env,
        vector_store=settings.vector_store,
        vector_backend=_active_vector_backend(),
        llm_configured=llm_available(),
        n8n_enabled=settings.n8n_enabled,
        demo_auth_bypass=settings.demo_auth_bypass,
        demo_mode=settings.demo_mode,
    )


@router.get("/analytics", response_model=AnalyticsSummary)
def analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsSummary:
    return build_analytics(db)


@router.get("/settings", response_model=SystemSettingsOut)
def system_settings(
    current_user: User = Depends(get_current_user),
) -> SystemSettingsOut:
    settings = get_settings()
    return SystemSettingsOut(
        app_name=settings.app_name,
        openai_model=settings.openai_model,
        embedding_model=settings.embedding_model,
        vector_store=settings.vector_store,
        chunk_size=settings.chunk_size,
        top_k_retrieval=settings.top_k_retrieval,
        n8n_enabled=settings.n8n_enabled,
        max_upload_size_mb=settings.max_upload_size_mb,
        allowed_extensions=settings.allowed_extension_list,
        demo_auth_bypass=settings.demo_auth_bypass,
        llm_configured=llm_available(),
        demo_mode=settings.demo_mode,
        demo_data_dir=settings.demo_data_dir,
    )
