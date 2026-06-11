"""
Applicant (seafarer) account administration — Administrator only.

The portal created a new account type; this gives staff visibility and
control over it:

GET  /api/applicants                          paginated list with search
PUT  /api/applicants/{id}                     activate / deactivate
POST /api/applicants/{id}/resend-verification re-send the verification email
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..auth import get_client_ip, require_role
from ..database import get_db
from ..models import Applicant, Application
from ..schemas import ApplicantUpdateRequest, ClaimRequest, InviteBatchRequest
from ..services import audit_service, recovery_service, throttle_service

router = APIRouter(prefix="/api/applicants", tags=["Applicant Administration"])

admin_required = Depends(require_role("Administrator"))
reviewer_required = Depends(require_role("Reviewer"))

PER_PAGE = 25


def _serialize(applicant: Applicant, application: Application = None) -> dict:
    return {
        "id": applicant.id,
        "email": applicant.email,
        "full_name": applicant.full_name,
        "email_verified": bool(applicant.email_verified),
        "is_active": bool(applicant.is_active),
        "invited_at": applicant.invited_at.isoformat() if applicant.invited_at else None,
        "created_at": applicant.created_at.isoformat() if applicant.created_at else None,
        "last_login": applicant.last_login.isoformat() if applicant.last_login else None,
        "application_id": application.id if application else None,
        "application_status": application.status if application else None,
    }


def _uninvited_email_count(db: Session) -> int:
    """Distinct emails of unclaimed applications with no portal account yet."""
    return (
        db.query(func.count(func.distinct(Application.email)))
        .filter(
            Application.applicant_id.is_(None),
            Application.email != "",
            ~Application.email.in_(db.query(Applicant.email)),
        )
        .scalar()
        or 0
    )


def _base_url(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}"


@router.get("")
def list_applicants(
    page: int = Query(1, ge=1),
    search: str = Query("", max_length=150),
    db: Session = Depends(get_db),
    user: dict = admin_required,
):
    filters = []
    if search.strip():
        like = f"%{search.strip()}%"
        filters.append(or_(Applicant.email.like(like), Applicant.full_name.like(like)))

    total = db.query(func.count(Applicant.id)).filter(*filters).scalar() or 0
    total_pages = max(1, -(-total // PER_PAGE))
    page = min(max(1, page), total_pages)

    rows = (
        db.query(Applicant)
        .filter(*filters)
        .order_by(Applicant.id.desc())
        .limit(PER_PAGE)
        .offset((page - 1) * PER_PAGE)
        .all()
    )

    # Map each applicant on this page to their application (if any)
    ids = [a.id for a in rows]
    applications = {}
    if ids:
        for app in db.query(Application).filter(Application.applicant_id.in_(ids)).all():
            applications[app.applicant_id] = app

    return {
        "items": [_serialize(a, applications.get(a.id)) for a in rows],
        "total": int(total),
        "page": page,
        "per_page": PER_PAGE,
        "total_pages": total_pages,
        "uninvited_unclaimed": _uninvited_email_count(db),
    }


@router.post("/invite")
def invite_applicant(
    body: ClaimRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = reviewer_required,
):
    """Create/refresh a portal account for one application's email and
    send (or resend) the set-your-password invitation."""
    application = db.get(Application, body.application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    def _base_url():
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
        return f"{proto}://{host}"

    applicant, resent = recovery_service.invite_for_application(db, application, _base_url())
    audit_service.log(
        db,
        audit_service.APPLICANT_INVITED,
        user=user,
        entity="application",
        entity_id=application.id,
        details=f"{'resent to' if resent else 'invited'} {applicant.email}",
        ip=get_client_ip(request),
    )
    application_row = (
        db.query(Application).filter(Application.applicant_id == applicant.id).first()
    )
    return {"applicant": _serialize(applicant, application_row), "resent": resent}


@router.post("/invite-batch")
def invite_batch(
    body: InviteBatchRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = admin_required,
):
    """Invite the next batch of seafarers without portal accounts.

    Processes distinct emails (the most recent unclaimed application per
    email) so duplicate submissions yield a single account. Capped so the
    invitation emails fit one serverless invocation.
    """
    def _base_url():
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
        return f"{proto}://{host}"

    candidates = (
        db.query(Application)
        .filter(
            Application.applicant_id.is_(None),
            Application.email != "",
            ~Application.email.in_(db.query(Applicant.email)),
        )
        .order_by(Application.email, Application.submitted_at.desc())
        .all()
    )

    invited, skipped = [], []
    seen_emails = set()
    base_url = _base_url()
    for application in candidates:
        if len(invited) >= body.limit:
            break
        if application.email in seen_emails:
            continue
        seen_emails.add(application.email)
        try:
            applicant, _ = recovery_service.invite_for_application(db, application, base_url)
            invited.append(application.id)
            audit_service.log(
                db,
                audit_service.APPLICANT_INVITED,
                user=user,
                entity="application",
                entity_id=application.id,
                details=f"invited {applicant.email} (batch)",
                ip=get_client_ip(request),
            )
        except HTTPException as exc:
            # e.g. malformed email on the record — skip and keep going
            skipped.append({"application_id": application.id, "reason": exc.detail})
            db.rollback()

    return {
        "invited": invited,
        "skipped": skipped,
        "remaining": _uninvited_email_count(db),
    }


@router.put("/{applicant_id}")
def update_applicant(
    applicant_id: int,
    body: ApplicantUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = admin_required,
):
    applicant = db.get(Applicant, applicant_id)
    if applicant is None:
        raise HTTPException(status_code=404, detail="Applicant not found")

    applicant.is_active = body.is_active
    db.commit()
    db.refresh(applicant)

    audit_service.log(
        db,
        audit_service.APPLICANT_UPDATED,
        user=user,
        entity="applicant",
        entity_id=applicant.id,
        details=f"{applicant.email}: is_active={body.is_active}",
        ip=get_client_ip(request),
    )

    application = (
        db.query(Application).filter(Application.applicant_id == applicant.id).first()
    )
    return {"applicant": _serialize(applicant, application)}


@router.post("/{applicant_id}/resend-verification")
def resend_verification(
    applicant_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = admin_required,
):
    applicant = db.get(Applicant, applicant_id)
    if applicant is None:
        raise HTTPException(status_code=404, detail="Applicant not found")
    if applicant.email_verified:
        raise HTTPException(status_code=400, detail="This account is already verified")

    recovery_service.resend_verification(db, applicant.email, _base_url(request))
    audit_service.log(
        db,
        audit_service.VERIFICATION_RESENT,
        user=user,
        entity="applicant",
        entity_id=applicant.id,
        details=applicant.email,
        ip=get_client_ip(request),
    )
    return {"message": f"Verification email sent to {applicant.email}"}
