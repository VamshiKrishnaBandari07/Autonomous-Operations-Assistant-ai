"""
RAG document loaders and text extraction.

Supports PDF, DOCX, and TXT with secure local file handling.
"""

from __future__ import annotations

from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader


def extract_text_from_pdf(path: str) -> str:
    reader = PdfReader(path)
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text)
    return "\n\n".join(parts)


def extract_text_from_docx(path: str) -> str:
    doc = DocxDocument(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text and p.text.strip())


def extract_text_from_txt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def extract_text(path: str, file_type: str) -> str:
    """Route extraction by file extension."""
    file_type = file_type.lower().lstrip(".")
    if file_type == "pdf":
        return extract_text_from_pdf(path)
    if file_type == "docx":
        return extract_text_from_docx(path)
    if file_type == "txt":
        return extract_text_from_txt(path)
    raise ValueError(f"Unsupported file type for extraction: {file_type}")
