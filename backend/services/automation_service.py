"""n8n webhook integration for OpsFlow automation workflows."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.core.config import get_settings

logger = logging.getLogger(__name__)


async def _post_webhook(path: str, payload: dict[str, Any]) -> bool:
    settings = get_settings()
    if not settings.n8n_enabled:
        logger.info("n8n disabled — skipping webhook %s", path)
        return False

    url = f"{settings.n8n_webhook_base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logger.info("n8n webhook succeeded: %s (%s)", url, response.status_code)
            return True
    except Exception as exc:  # noqa: BLE001
        # Automation failures must not break core API flows
        logger.warning("n8n webhook failed (%s): %s", url, exc)
        return False


async def trigger_task_created(payload: dict[str, Any]) -> bool:
    settings = get_settings()
    return await _post_webhook(settings.n8n_task_created_webhook, payload)


async def trigger_document_uploaded(payload: dict[str, Any]) -> bool:
    settings = get_settings()
    return await _post_webhook(settings.n8n_document_uploaded_webhook, payload)


async def trigger_meeting_summary(payload: dict[str, Any]) -> bool:
    settings = get_settings()
    return await _post_webhook(settings.n8n_meeting_summary_webhook, payload)


async def trigger_employee_onboarding(payload: dict[str, Any]) -> bool:
    """Notify n8n: accounts checklist + Slack for a new hire."""
    settings = get_settings()
    return await _post_webhook(settings.n8n_employee_onboarding_webhook, payload)
