"""API router package."""

from fastapi import APIRouter

from backend.api import analytics, auth, chat, demo, documents, meetings, onboarding, reports, tasks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(tasks.router)
api_router.include_router(chat.router)
api_router.include_router(meetings.router)
api_router.include_router(reports.router)
api_router.include_router(onboarding.router)
api_router.include_router(demo.router)
api_router.include_router(analytics.router)
