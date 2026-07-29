"""Shared LLM client factory for OpsFlow agents."""

from __future__ import annotations

import logging
from functools import lru_cache

from backend.core.config import get_settings

logger = logging.getLogger(__name__)


def llm_available() -> bool:
    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    return bool(key) and not key.startswith("sk-your-")


@lru_cache
def get_chat_model():
    """Return a LangChain ChatOpenAI instance configured from settings."""
    if not llm_available():
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from langchain_openai import ChatOpenAI

    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        max_tokens=settings.openai_max_tokens,
        api_key=settings.openai_api_key,
    )


def invoke_json_llm(system_prompt: str, user_prompt: str) -> str:
    """Invoke the LLM and return raw text (expected to be JSON)."""
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = get_chat_model()
    response = llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    )
    return response.content if hasattr(response, "content") else str(response)
