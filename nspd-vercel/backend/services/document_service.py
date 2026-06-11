"""Document metadata records (file bytes live in storage_service drivers)."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Document

DOC_TYPES = ("Certificate", "Medical Report", "Passport Photo", "ID Document", "Other")


def serialize(document: Document) -> dict:
    return {
        "id": document.id,
        "application_id": document.application_id,
        "doc_type": document.doc_type,
        "original_name": document.original_name,
        "content_type": document.content_type,
        "size_bytes": document.size_bytes,
        "uploaded_by": document.uploaded_by,
        "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
    }


def list_for_application(db: Session, application_id: int) -> list:
    rows = (
        db.query(Document)
        .filter(Document.application_id == application_id)
        .order_by(Document.id.desc())
        .all()
    )
    return [serialize(d) for d in rows]


def create_record(
    db: Session,
    application_id: int,
    doc_type: str,
    original_name: str,
    content_type: str,
    size_bytes: int,
    storage_driver: str,
    storage_key: str,
    uploaded_by: int,
) -> Document:
    document = Document(
        application_id=application_id,
        doc_type=doc_type if doc_type in DOC_TYPES else "Other",
        original_name=original_name[:255],
        content_type=(content_type or "application/octet-stream")[:100],
        size_bytes=size_bytes,
        storage_driver=storage_driver,
        storage_key=storage_key,
        uploaded_by=uploaded_by,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_or_404(db: Session, document_id: int) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
