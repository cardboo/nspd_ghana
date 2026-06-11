"""
Applicant portal endpoints — a separate auth realm from staff.

POST   /api/portal/register        create a seafarer account (email verification)
GET    /api/portal/verify          confirm email via token
POST   /api/portal/login           portal session (portal_token cookie)
POST   /api/portal/logout
GET    /api/portal/me              account + application status summary
GET    /api/portal/ranks           rank options for the form (public)
GET    /api/portal/application     own application
POST   /api/portal/application     submit (one per account)
PUT    /api/portal/application     edit while Pending; resubmit after Rejected
GET    /api/portal/documents       own documents
POST   /api/portal/documents       upload to own application
DELETE /api/portal/documents/{id}  delete own (self-uploaded) document
"""

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import (
    clear_portal_cookie,
    create_portal_token,
    get_client_ip,
    get_current_applicant,
    set_portal_cookie,
    verify_password,
)
from ..config import settings
from ..database import get_db
from ..models import Applicant, Document
from ..schemas import (
    ApplicationForm,
    CertificationForm,
    CompleteResetRequest,
    ForgotPasswordRequest,
    PortalLoginRequest,
    PortalRegisterRequest,
    ResendVerificationRequest,
)
from ..services import (
    application_service,
    audit_service,
    certification_service,
    document_service,
    portal_service,
    recovery_service,
    storage_service,
    throttle_service,
)

GENERIC_RESET_MESSAGE = (
    "If an account with that email exists, a password reset link has been sent."
)
GENERIC_VERIFY_MESSAGE = (
    "If an unverified account with that email exists, a new verification link has been sent."
)


def _rate_limit_public(db: Session, request: Request, prefix: str) -> str:
    """Per-IP throttle for unauthenticated portal endpoints; returns the IP."""
    from ..config import settings as cfg

    ip = get_client_ip(request)
    identity = throttle_service.ip_identity(prefix, ip)
    if throttle_service.is_rate_limited(db, identity, cfg.lockout_max_attempts):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    throttle_service.record_event(db, identity, ip)
    return ip

router = APIRouter(prefix="/api/portal", tags=["Applicant Portal"])


def _base_url(request: Request) -> str:
    """Public base URL for links in emails, honouring Vercel's proxy headers."""
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}"


def _get_applicant_or_401(db: Session, applicant_claims: dict) -> Applicant:
    applicant = db.get(Applicant, applicant_claims["id"])
    if applicant is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return applicant


# ──────────────────────────────────────────────
# Accounts
# ──────────────────────────────────────────────

@router.post("/register", status_code=201)
def register(
    body: PortalRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _rate_limit_public(db, request, "register")
    applicant = portal_service.register(db, body, _base_url(request))
    audit_service.log(
        db,
        audit_service.PORTAL_REGISTERED,
        username=throttle_service.portal_identity(applicant.email),
        entity="applicant",
        entity_id=applicant.id,
        ip=get_client_ip(request),
    )
    return {
        "applicant": portal_service.serialize_applicant(applicant),
        "verification_required": not applicant.email_verified,
    }


@router.get("/verify")
def verify(
    token: str = Query("", max_length=64),
    db: Session = Depends(get_db),
):
    applicant = portal_service.verify_email(db, token.strip())
    audit_service.log(
        db,
        audit_service.PORTAL_VERIFIED,
        username=throttle_service.portal_identity(applicant.email),
        entity="applicant",
        entity_id=applicant.id,
    )
    return {"message": "Email verified. You can now sign in."}


@router.post("/login")
def login(
    credentials: PortalLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    ip = get_client_ip(request)
    identity = throttle_service.portal_identity(credentials.email)

    if throttle_service.is_locked_out(db, identity, ip):
        audit_service.log(db, audit_service.PORTAL_LOGIN_LOCKED, username=identity, ip=ip)
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many failed login attempts. "
                f"Please try again in {settings.lockout_window_minutes} minutes."
            ),
        )

    applicant = db.query(Applicant).filter(Applicant.email == credentials.email).first()

    if applicant is None or not verify_password(credentials.password, applicant.password_hash):
        throttle_service.record_failure(db, identity, ip)
        audit_service.log(db, audit_service.PORTAL_LOGIN_FAILED, username=identity, ip=ip)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not applicant.is_active:
        raise HTTPException(
            status_code=401,
            detail="This account has been deactivated. Contact the Ghana Maritime Authority.",
        )

    if not applicant.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email address first — check your inbox for the confirmation link.",
        )

    throttle_service.record_success(db, identity, ip)
    applicant.last_login = func.now()
    db.commit()

    audit_service.log(
        db,
        audit_service.PORTAL_LOGIN_SUCCESS,
        username=identity,
        entity="applicant",
        entity_id=applicant.id,
        ip=ip,
    )

    set_portal_cookie(response, create_portal_token(applicant))
    return {"applicant": portal_service.serialize_applicant(applicant)}


@router.post("/logout")
def logout(response: Response):
    clear_portal_cookie(response)
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = _rate_limit_public(db, request, "pwreset")
    applicant = recovery_service.issue_portal_reset(db, body.identifier.strip(), _base_url(request))
    if applicant is not None:
        audit_service.log(
            db,
            audit_service.PASSWORD_RESET_REQUESTED,
            username=throttle_service.portal_identity(applicant.email),
            entity="applicant",
            entity_id=applicant.id,
            ip=ip,
        )
    return {"message": GENERIC_RESET_MESSAGE}


@router.post("/reset-password")
def reset_password(
    body: CompleteResetRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    applicant = recovery_service.complete_portal_reset(db, body.token.strip(), body.new_password)
    audit_service.log(
        db,
        audit_service.PASSWORD_RESET_COMPLETED,
        username=throttle_service.portal_identity(applicant.email),
        entity="applicant",
        entity_id=applicant.id,
        ip=get_client_ip(request),
    )
    return {"message": "Password reset successfully. You can now sign in."}


@router.post("/resend-verification")
def resend_verification(
    body: ResendVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = _rate_limit_public(db, request, "verify")
    applicant = recovery_service.resend_verification(db, body.email.strip(), _base_url(request))
    if applicant is not None:
        audit_service.log(
            db,
            audit_service.VERIFICATION_RESENT,
            username=throttle_service.portal_identity(applicant.email),
            entity="applicant",
            entity_id=applicant.id,
            ip=ip,
        )
    return {"message": GENERIC_VERIFY_MESSAGE}


@router.get("/me")
def me(
    claims: dict = Depends(get_current_applicant),
    db: Session = Depends(get_db),
):
    applicant = _get_applicant_or_401(db, claims)
    application = portal_service.get_my_application(db, applicant.id)
    return {
        "applicant": portal_service.serialize_applicant(applicant),
        "application_status": application.status if application else None,
        "application_id": application.id if application else None,
    }


# ──────────────────────────────────────────────
# Application form
# ──────────────────────────────────────────────

@router.get("/ranks")
def ranks(db: Session = Depends(get_db)):
    """Rank options for the public application form (no PII exposed)."""
    return {"ranks": application_service.distinct_ranks(db)}


@router.get("/application")
def get_application(
    claims: dict = Depends(get_current_applicant),
    db: Session = Depends(get_db),
):
    application = portal_service.get_my_application(db, claims["id"])
    if application is None:
        raise HTTPException(status_code=404, detail="You have not submitted an application yet")
    return {"application": portal_service.serialize_portal_application(application)}


@router.post("/application", status_code=201)
def submit_application(
    body: ApplicationForm,
    request: Request,
    claims: dict = Depends(get_current_applicant),
    db: Session = Depends(get_db),
):
    applicant = _get_applicant_or_401(db, claims)
    application = portal_service.create_application(db, applicant, body)
    audit_service.log(
        db,
        audit_service.APPLICATION_SUBMITTED,
        username=throttle_service.portal_identity(applicant.email),
        entity="application",
        entity_id=application.id,
        ip=get_client_ip(request),
    )
    return {"application": portal_service.serialize_portal_application(application)}


@router.put("/application")
def update_application(
    body: ApplicationForm,
    request: Request,
    claims: dict = Depends(get_current_applicant),
    db: Session = Depends(get_db),
):
    applicant = _get_applicant_or_401(db, claims)
    application = portal_service.get_my_application(db, applicant.id)
    if application is None:
        raise HTTPException(status_code=404, detail="You have not submitted an application yet")

    application, resubmitted = portal_service.update_application(db, application, body)
    audit_service.log(
        db,
        audit_service.APPLICATION_RESUBMITTED if resubmitted else audit_service.APPLICATION_UPDATED,
        username=throttle_service.portal_identity(applicant.email),
        entity="application",
        entity_id=application.id,
        ip=get_client_ip(request),
    )
    return {"application": portal_service.serialize_portal_application(application)}


@router.get("/application/history")
def application_history(
    claims: dict = Depends(get_current_applicant),
    db: Session = Depends(get_db),
):
    application = portal_service.get_my_application(db, claims["id"])
    if application is None:
        raise HTTPException(status_code=404, detail="You have not submitted an application yet")
    # Applicants see the timeline without staff usernames
    return {
        "history": application_service.get_status_history(db, application, include_usernames=False)
    }


# ──────────────────────────────────────────────
# Certifications (own application only)
# ──────────────────────────────────────────────

@router.get("/certifications")
def list_certifications(
    claims: dict = Depends(get_current_applicant),
    db: Session = Depends(get_db),
):
    application = _get_own_application_or_404(db, claims["id"])
    return {"certifications": certification_service.list_for_application(db, application.id)}


@router.post("/certifications", status_code=201)
def add_certification(
    body: CertificationForm,
    request: Request,
    claims: dict = Depends(get_current_applicant),
    db: Session = Depends(get_db),
):
    application = _get_own_application_or_404(db, claims["id"])
    if application.status not in portal_service.EDITABLE_STATUSES:
        raise HTTPException(
            status_code=403,
            detail=f"Your application is {application.status} and certifications can no longer be changed.",
        )
    cert = certification_service.create(db, application.id, body, added_by=None)
    audit_service.log(
        db,
        audit_service.CERT_ADDED,
        username=throttle_service.portal_identity(claims["email"]),
        entity="application",
        entity_id=application.id,
        details=f"{cert.cert_type}: {cert.title}",
        ip=get_client_ip(request),
    )
    return {"certification": certification_service.serialize(cert)}


@router.delete("/certifications/{certification_id}")
def delete_certification(
    certification_id: int,
    request: Request,
    claims: dict = Depends(get_current_applicant),
    db: Session = Depends(get_db),
):
    application = _get_own_application_or_404(db, claims["id"])
    cert = certification_service.get_or_404(db, certification_id)

    if cert.application_id != application.id:
        raise HTTPException(status_code=404, detail="Certification not found")
    if cert.added_by is not None:
        raise HTTPException(status_code=403, detail="Records added by GMA staff cannot be removed")
    if application.status not in portal_service.EDITABLE_STATUSES:
        raise HTTPException(
            status_code=403,
            detail=f"Your application is {application.status} and certifications can no longer be changed.",
        )

    title = cert.title
    certification_service.delete(db, cert)
    audit_service.log(
        db,
        audit_service.CERT_DELETED,
        username=throttle_service.portal_identity(claims["email"]),
        entity="application",
        entity_id=application.id,
        details=title,
        ip=get_client_ip(request),
    )
    return {"message": "Certification deleted"}


# ──────────────────────────────────────────────
# Documents (own application only)
# ──────────────────────────────────────────────

def _get_own_application_or_404(db: Session, applicant_id: int):
    application = portal_service.get_my_application(db, applicant_id)
    if application is None:
        raise HTTPException(status_code=404, detail="You have not submitted an application yet")
    return application


@router.get("/documents")
def list_documents(
    claims: dict = Depends(get_current_applicant),
    db: Session = Depends(get_db),
):
    application = _get_own_application_or_404(db, claims["id"])
    return {"documents": document_service.list_for_application(db, application.id)}


@router.post("/documents", status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    doc_type: str = Form("Other"),
    claims: dict = Depends(get_current_applicant),
    db: Session = Depends(get_db),
):
    application = _get_own_application_or_404(db, claims["id"])
    if application.status not in portal_service.EDITABLE_STATUSES:
        raise HTTPException(
            status_code=403,
            detail=f"Your application is {application.status} and documents can no longer be changed.",
        )

    existing = db.query(func.count(Document.id)).filter(
        Document.application_id == application.id
    ).scalar() or 0
    if existing >= portal_service.MAX_PORTAL_DOCUMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"A maximum of {portal_service.MAX_PORTAL_DOCUMENTS} documents is allowed.",
        )

    data = await file.read()
    storage_service.validate_upload(file.filename or "", len(data))

    driver, storage_key = storage_service.save(
        application.id, file.filename or "upload", file.content_type or "", data
    )
    document = document_service.create_record(
        db,
        application_id=application.id,
        doc_type=doc_type,
        original_name=file.filename or "upload",
        content_type=file.content_type or "",
        size_bytes=len(data),
        storage_driver=driver,
        storage_key=storage_key,
        uploaded_by=None,  # applicant upload (uploaded_by references staff users)
    )
    audit_service.log(
        db,
        audit_service.DOCUMENT_UPLOADED,
        username=throttle_service.portal_identity(claims["email"]),
        entity="application",
        entity_id=application.id,
        details=f"{document.doc_type}: {document.original_name} ({len(data)} bytes)",
        ip=get_client_ip(request),
    )
    return {"document": document_service.serialize(document)}


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    request: Request,
    claims: dict = Depends(get_current_applicant),
    db: Session = Depends(get_db),
):
    application = _get_own_application_or_404(db, claims["id"])
    document = document_service.get_or_404(db, document_id)

    if document.application_id != application.id:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.uploaded_by is not None:
        raise HTTPException(status_code=403, detail="Documents added by GMA staff cannot be removed")
    if application.status not in portal_service.EDITABLE_STATUSES:
        raise HTTPException(
            status_code=403,
            detail=f"Your application is {application.status} and documents can no longer be changed.",
        )

    storage_service.delete(document.storage_driver, document.storage_key)
    original_name = document.original_name
    db.delete(document)
    db.commit()

    audit_service.log(
        db,
        audit_service.DOCUMENT_DELETED,
        username=throttle_service.portal_identity(claims["email"]),
        entity="application",
        entity_id=application.id,
        details=original_name,
        ip=get_client_ip(request),
    )
    return {"message": "Document deleted"}
