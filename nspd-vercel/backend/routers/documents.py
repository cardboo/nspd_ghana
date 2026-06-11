"""
Document download/delete by document id.

GET    /api/documents/{id}/download  (any authenticated user)
DELETE /api/documents/{id}           (Reviewer+)
"""

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import get_client_ip, get_current_user, require_role
from ..database import get_db
from ..services import audit_service, document_service, storage_service

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    document = document_service.get_or_404(db, document_id)

    if document.storage_driver == "vercel_blob":
        return RedirectResponse(url=document.storage_key)

    data = storage_service.load_local(document.storage_key)
    return Response(
        content=data,
        media_type=document.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{document.original_name}"'
        },
    )


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Reviewer")),
):
    document = document_service.get_or_404(db, document_id)

    storage_service.delete(document.storage_driver, document.storage_key)
    application_id = document.application_id
    original_name = document.original_name
    db.delete(document)
    db.commit()

    audit_service.log(
        db,
        audit_service.DOCUMENT_DELETED,
        user=user,
        entity="application",
        entity_id=application_id,
        details=original_name,
        ip=get_client_ip(request),
    )
    return {"message": "Document deleted"}
