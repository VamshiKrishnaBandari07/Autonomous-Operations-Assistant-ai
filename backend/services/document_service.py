"""Document ingestion service — secure upload + RAG indexing."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.models.document import Document
from backend.models.user import User
from backend.rag.ingest import extract_text, index_document_text
from backend.services.automation_service import trigger_document_uploaded

logger = logging.getLogger(__name__)


def _safe_filename(name: str) -> str:
    """Strip path components and unsafe characters from uploaded filenames."""
    base = Path(name).name
    cleaned = re.sub(r"[^\w.\- ]+", "_", base).strip()
    return cleaned or f"upload_{uuid.uuid4().hex[:8]}"


async def save_and_index_document(
    db: Session,
    file: UploadFile,
    owner: User,
) -> Document:
    """Validate, persist, extract text, and index a company document."""
    settings = get_settings()
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename")

    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext not in settings.allowed_extension_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {settings.allowed_extension_list}",
        )

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_size_mb} MB limit",
        )
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}_{_safe_filename(file.filename)}"
    file_path = upload_dir / stored_name
    file_path.write_bytes(content)

    doc = Document(
        filename=stored_name,
        original_name=file.filename,
        file_type=ext,
        file_path=str(file_path),
        file_size=len(content),
        status="pending",
        owner_id=owner.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        text = extract_text(str(file_path), ext)
        if not text.strip():
            raise ValueError("No extractable text found in document")

        chunk_count, summary = index_document_text(
            document_id=doc.id,
            document_name=doc.original_name,
            text=text,
        )
        doc.chunk_count = chunk_count
        doc.summary = summary
        doc.status = "indexed"
        doc.indexed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(doc)

        # Fire-and-forget automation hook (document → vector DB update → notify)
        await trigger_document_uploaded(
            {
                "document_id": doc.id,
                "name": doc.original_name,
                "chunks": doc.chunk_count,
                "status": doc.status,
            }
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Document indexing failed for id=%s", doc.id)
        doc.status = "failed"
        doc.summary = f"Indexing failed: {exc}"
        db.commit()
        db.refresh(doc)

    return doc


def list_documents(db: Session, owner_id: int | None = None) -> list[Document]:
    query = db.query(Document).order_by(Document.created_at.desc())
    if owner_id is not None:
        query = query.filter(Document.owner_id == owner_id)
    return query.all()


def get_document(db: Session, document_id: int) -> Document | None:
    return db.query(Document).filter(Document.id == document_id).first()


def delete_document(db: Session, document_id: int) -> bool:
    from backend.rag.vector_store import get_vector_store

    doc = get_document(db, document_id)
    if not doc:
        return False

    path = Path(doc.file_path)
    if path.exists():
        path.unlink()

    try:
        get_vector_store().delete_by_document_id(doc.id)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to remove vectors for document %s", doc.id)

    db.delete(doc)
    db.commit()
    return True
