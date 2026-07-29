"""Text chunking utilities for the RAG pipeline."""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.core.config import get_settings


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    settings = get_settings()
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def split_text(text: str) -> list[str]:
    splitter = get_text_splitter()
    chunks = splitter.split_text(text)
    return [c.strip() for c in chunks if c and c.strip()]
