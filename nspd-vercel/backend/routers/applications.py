"""
Application (submission) endpoints.

submissions.php       -> GET /api/applications?page=&search=&rank=&status=&sort=&dir=
rank dropdown query   -> GET /api/applications/ranks
view-submission.php   -> GET /api/applications/{id}

v2 additions:
  PUT    /api/applications/{id}/status      (Reviewer+) review decision
  GET    /api/applications/{id}/comments
  POST   /api/applications/{id}/comments    (Reviewer+)
  DELETE /api/applications/comments/{id}    (author or Administrator)
  GET    /api/applications/{id}/documents
  POST   /api/applications/{id}/documents   (Reviewer+) multipart upload
"""

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from sqlalchemy.orm import Session

from ..auth import get_client_ip, get_current_user, require_role
from ..database import get_db
from ..schemas import (
    BulkStatusRequest,
    CertificationForm,
    CommentRequest,
    StatusUpdateRequest,
    VoyageForm,
)
from ..services import (
    application_service,
    audit_service,
    certification_service,
    document_service,
    email_service,
    storage_service,
    voyage_service,
)

router = APIRouter(prefix="/api/applications", tags=["Applications"])


@router.post("/bulk-status")
def bulk_status(
    body: BulkStatusRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Reviewer")),
):
    """Apply one review decision to up to 20 applications at once."""
    updated, skipped = [], []
    emails = {"sent": 0, "skipped": 0, "failed": 0}

    for application_id in dict.fromkeys(body.ids):  # dedupe, keep order
        application = application_service.get_application(db, application_id)
        if application is None or application.status == body.status:
            skipped.append(application_id)
            continue
        application_service.update_status(db, application, body.status, user)
        notification = email_service.notify_status_change(db, application, body.status)
        emails[notification.status if notification.status in emails else "failed"] += 1
        updated.append(application_id)

    audit_service.log(
        db,
        audit_service.BULK_STATUS,
        user=user,
        entity="applications",
        details=f"-> {body.status}: {len(updated)} updated (ids={updated}), {len(skipped)} skipped",
        ip=get_client_ip(request),
    )
    return {"updated": updated, "skipped": skipped, "emails": emails}


@router.get("")
def list_applications(
    page: int = Query(1, ge=1),
    search: str = Query("", max_length=200),
    rank: str = Query("", max_length=100),
    status: str = Query("", max_length=20),
    sort: str = Query("date", max_length=10),
    dir: str = Query("desc", max_length=4),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return application_service.list_applications(
        db,
        page=page,
        search=search.strip(),
        rank=rank.strip(),
        status=status.strip(),
        sort=sort,
        direction=dir,
    )


@router.get("/ranks")
def list_ranks(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return {"ranks": application_service.distinct_ranks(db)}


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    comment = application_service.delete_comment(db, comment_id, user)
    audit_service.log(
        db,
        audit_service.COMMENT_DELETED,
        user=user,
        entity="application",
        entity_id=comment.application_id,
        details=f"comment #{comment_id}",
        ip=get_client_ip(request),
    )
    return {"message": "Comment deleted"}


@router.get("/{application_id}")
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    application = _get_or_404(db, application_id)
    reviewer_name = application_service.get_reviewer_name(db, application)
    return {
        "application": application_service.serialize_detail(application, reviewer_name),
        "portal_account": _portal_account_state(db, application),
    }


def _portal_account_state(db: Session, application) -> dict:
    """How the seafarer relates to the portal: none / invited / active / unlinked."""
    from ..models import Applicant

    applicant = None
    if application.applicant_id:
        applicant = db.get(Applicant, application.applicant_id)
    if applicant is None and application.email:
        applicant = db.query(Applicant).filter(Applicant.email == application.email).first()

    if applicant is None:
        return {"status": "none"}

    if applicant.last_login is not None:
        status = "active"
    elif applicant.invited_at is not None:
        status = "invited"
    else:
        status = "registered_unused"
    return {
        "status": status,
        "linked": application.applicant_id == applicant.id,
        "email": applicant.email,
        "invited_at": applicant.invited_at.isoformat() if applicant.invited_at else None,
        "last_login": applicant.last_login.isoformat() if applicant.last_login else None,
    }


@router.put("/{application_id}/status")
def update_status(
    application_id: int,
    body: StatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Reviewer")),
):
    application = _get_or_404(db, application_id)
    previous_status = application.status

    application = application_service.update_status(db, application, body.status, user)

    audit_service.log(
        db,
        audit_service.STATUS_CHANGED,
        user=user,
        entity="application",
        entity_id=application.id,
        details=f"{previous_status} -> {body.status}",
        ip=get_client_ip(request),
    )

    notification = None
    if body.status != previous_status:
        notification = email_service.notify_status_change(db, application, body.status)

    return {
        "application": application_service.serialize_detail(application, user["full_name"]),
        "notification": {
            "status": notification.status if notification else "not_required",
            "recipient": notification.recipient if notification else None,
        },
    }


@router.get("/{application_id}/comments")
def list_comments(
    application_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _get_or_404(db, application_id)
    return {"comments": application_service.list_comments(db, application_id)}


@router.post("/{application_id}/comments", status_code=201)
def add_comment(
    application_id: int,
    body: CommentRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Reviewer")),
):
    _get_or_404(db, application_id)
    comment = application_service.add_comment(db, application_id, user, body.comment.strip())
    audit_service.log(
        db,
        audit_service.COMMENT_ADDED,
        user=user,
        entity="application",
        entity_id=application_id,
        ip=get_client_ip(request),
    )
    return {"comment": application_service.serialize_comment(comment)}


@router.get("/{application_id}/history")
def status_history(
    application_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    application = _get_or_404(db, application_id)
    return {"history": application_service.get_status_history(db, application)}


@router.get("/{application_id}/certifications")
def list_certifications(
    application_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _get_or_404(db, application_id)
    return {"certifications": certification_service.list_for_application(db, application_id)}


@router.post("/{application_id}/certifications", status_code=201)
def add_certification(
    application_id: int,
    body: CertificationForm,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Reviewer")),
):
    _get_or_404(db, application_id)
    cert = certification_service.create(db, application_id, body, added_by=user["id"])
    audit_service.log(
        db,
        audit_service.CERT_ADDED,
        user=user,
        entity="application",
        entity_id=application_id,
        details=f"{cert.cert_type}: {cert.title}",
        ip=get_client_ip(request),
    )
    return {"certification": certification_service.serialize(cert)}


@router.delete("/certifications/{certification_id}")
def delete_certification(
    certification_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Reviewer")),
):
    cert = certification_service.get_or_404(db, certification_id)
    application_id, title = cert.application_id, cert.title
    certification_service.delete(db, cert)
    audit_service.log(
        db,
        audit_service.CERT_DELETED,
        user=user,
        entity="application",
        entity_id=application_id,
        details=title,
        ip=get_client_ip(request),
    )
    return {"message": "Certification deleted"}


@router.get("/{application_id}/voyages")
def list_voyages(
    application_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _get_or_404(db, application_id)
    return voyage_service.list_for_application(db, application_id)


@router.post("/{application_id}/voyages", status_code=201)
def add_voyage(
    application_id: int,
    body: VoyageForm,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Reviewer")),
):
    _get_or_404(db, application_id)
    voyage = voyage_service.create(db, application_id, body, added_by=user["id"])
    audit_service.log(
        db,
        audit_service.VOYAGE_ADDED,
        user=user,
        entity="application",
        entity_id=application_id,
        details=f"{voyage.vessel_name} ({voyage.employer or 'no employer'})",
        ip=get_client_ip(request),
    )
    return {"voyage": voyage_service.serialize(voyage)}


@router.delete("/voyages/{voyage_id}")
def delete_voyage(
    voyage_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Reviewer")),
):
    voyage = voyage_service.get_or_404(db, voyage_id)
    application_id, vessel = voyage.application_id, voyage.vessel_name
    voyage_service.delete(db, voyage)
    audit_service.log(
        db,
        audit_service.VOYAGE_DELETED,
        user=user,
        entity="application",
        entity_id=application_id,
        details=vessel,
        ip=get_client_ip(request),
    )
    return {"message": "Voyage deleted"}


@router.get("/{application_id}/documents")
def list_documents(
    application_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _get_or_404(db, application_id)
    return {"documents": document_service.list_for_application(db, application_id)}


@router.post("/{application_id}/documents", status_code=201)
async def upload_document(
    application_id: int,
    request: Request,
    file: UploadFile = File(...),
    doc_type: str = Form("Other"),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Reviewer")),
):
    _get_or_404(db, application_id)

    data = await file.read()
    storage_service.validate_upload(file.filename or "", len(data))

    driver, storage_key = storage_service.save(
        application_id, file.filename or "upload", file.content_type or "", data
    )
    document = document_service.create_record(
        db,
        application_id=application_id,
        doc_type=doc_type,
        original_name=file.filename or "upload",
        content_type=file.content_type or "",
        size_bytes=len(data),
        storage_driver=driver,
        storage_key=storage_key,
        uploaded_by=user["id"],
    )
    audit_service.log(
        db,
        audit_service.DOCUMENT_UPLOADED,
        user=user,
        entity="application",
        entity_id=application_id,
        details=f"{document.doc_type}: {document.original_name} ({len(data)} bytes)",
        ip=get_client_ip(request),
    )
    return {"document": document_service.serialize(document)}


def _get_or_404(db: Session, application_id: int):
    if application_id <= 0:
        raise HTTPException(status_code=400, detail="Valid application ID is required")
    application = application_service.get_application(db, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application
