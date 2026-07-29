"""
OpsFlow AI — FastAPI application entrypoint.

Run:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import api_router
from backend.core.config import get_settings
from backend.database.session import SessionLocal, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("opsflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.demo_data_dir).mkdir(parents=True, exist_ok=True)
    init_db()

    if settings.demo_mode:
        db = SessionLocal()
        try:
            from backend.demo.seed import seed_demo_environment
            from backend.services.user_service import ensure_admin_user

            owner = ensure_admin_user(db)
            seed_demo_environment(db, owner)
            logger.info("DEMO_MODE active — sample knowledge base seeded")
        except Exception:  # noqa: BLE001
            logger.exception("Demo seed failed (non-fatal)")
        finally:
            db.close()

    logger.info(
        "%s started (env=%s demo_mode=%s)",
        settings.app_name,
        settings.app_env,
        settings.demo_mode,
    )
    yield
    logger.info("%s shutting down", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=(
            "AI-first operations automation platform combining RAG, multi-agent "
            "orchestration, and n8n workflow automation."
            + (" [PUBLIC DEMO MODE]" if settings.demo_mode else "")
        ),
        version="1.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):  # noqa: ARG001
        logger.exception("Unhandled error")
        detail = str(exc) if settings.app_debug or settings.demo_mode else "Internal server error"
        return JSONResponse(status_code=500, content={"detail": detail})

    @app.get("/")
    def root():
        return {
            "name": settings.app_name,
            "version": "1.1.0",
            "demo_mode": settings.demo_mode,
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", get_settings().app_port))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
