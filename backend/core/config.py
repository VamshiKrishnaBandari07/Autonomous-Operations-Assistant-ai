"""
OpsFlow AI — Application configuration.

All runtime settings are loaded from environment variables (see .env.example).
This module is the single source of truth for configuration across backend services.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for OpsFlow AI."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "OpsFlow AI"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60

    # Database
    database_url: str = "sqlite:///./data/opsflow.db"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2
    openai_max_tokens: int = 2048

    # Embeddings / Vector Store
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_store: str = "chroma"
    chroma_persist_dir: str = "./data/chroma"
    chunk_size: int = 800
    chunk_overlap: int = 150
    top_k_retrieval: int = 5
    rag_score_threshold: float = 0.25

    # Uploads
    upload_dir: str = "./documents"
    max_upload_size_mb: int = 25
    allowed_extensions: str = "pdf,docx,txt"

    # Auth defaults
    admin_username: str = "admin"
    admin_password: str = "opsflow-admin-change-me"
    admin_email: str = "admin@opsflow.ai"
    # Local demos only — never enable in production
    demo_auth_bypass: bool = True

    # n8n
    n8n_webhook_base_url: str = "http://localhost:5678/webhook"
    n8n_enabled: bool = False
    n8n_task_created_webhook: str = "task-created"
    n8n_document_uploaded_webhook: str = "document-uploaded"
    n8n_meeting_summary_webhook: str = "meeting-summary"
    n8n_employee_onboarding_webhook: str = "employee-onboarding"

    # Analytics
    avg_minutes_saved_per_query: int = 8
    avg_minutes_saved_per_task: int = 15

    # CORS
    cors_origins: str = "http://localhost:8501,http://127.0.0.1:8501"

    # Frontend
    backend_api_url: str = "http://localhost:8000"

    @property
    def allowed_extension_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",") if ext.strip()]

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
