"""Shared pytest fixtures for OpsFlow AI tests."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force offline-friendly settings before importing the app
os.environ["OPENAI_API_KEY"] = ""
os.environ["N8N_ENABLED"] = "false"
os.environ["VECTOR_STORE"] = "memory"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "opsflow-admin-change-me"
os.environ["APP_ENV"] = "test"
os.environ["DEMO_AUTH_BYPASS"] = "true"
os.environ["RAG_SCORE_THRESHOLD"] = "0.15"

from backend.core.config import get_settings
from backend.core.deps import get_db
from backend.database import session as db_session_module
from backend.database.session import Base
from backend.main import create_app
from backend.rag.vector_store import reset_vector_store_for_tests
from backend.services.user_service import ensure_admin_user

get_settings.cache_clear()


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db_session_module.engine = engine
    db_session_module.SessionLocal = TestingSessionLocal

    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    ensure_admin_user(session)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    reset_vector_store_for_tests()
    get_settings.cache_clear()

    app = create_app()

    def _override_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db

    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client

    app.dependency_overrides.clear()
