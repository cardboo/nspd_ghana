"""
Applicant portal business logic: registration, email verification, and
the one-application-per-account lifecycle.

Lifecycle rules:
  - an applicant owns at most one application (applications.applicant_id)
  - the application's email always equals the account email
  - editable while status is Pending or Rejected
  - editing a Rejected application resubmits it: status returns to
    Pending and the previous review decision fields are cleared
    (the audit log keeps the history)
"""

import secrets

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import hash_password
from ..config import settings
from ..models import Applicant, Application
from . import email_service

EDITABLE_STATUSES = ("Pending", "Rejected")

MAX_PORTAL_DOCUMENTS = 10


def serialize_applicant(applicant: Applicant) -> dict:
    return {
        "id": applicant.id,
        "email": applicant.email,
        "full_name": applicant.full_name,
        "email_verified": bool(applicant.email_verified),
        "created_at": applicant.created_at.isoformat() if applicant.created_at else None,
    }


def serialize_portal_application(app: Application) -> dict:
    """Applicant-facing view: their own data + status, no staff identities."""
    return {
        "id": app.id,
        "surname": app.surname,
        "first_name": app.first_name,
        "other_names": app.other_names,
        "telephone": app.telephone,
        "ghana_card_number": app.ghana_card_number,
        "email": app.email,
        "position_rank": app.position_rank,
        "short_courses_rmu": app.short_courses_rmu,
        "familiarisation_isps_gma": app.familiarisation_isps_gma,
        "attachment": app.attachment,
        "sea_experience": app.sea_experience,
        "medicals": app.medicals,
        "total_sea_experience_years": (
            float(app.total_sea_experience_years)
            if app.total_sea_experience_years is not None
            else None
        ),
        "last_ship_type": app.last_ship_type,
        "status": app.status,
        "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
        "editable": app.status in EDITABLE_STATUSES,
    }


# ──────────────────────────────────────────────
# Accounts
# ──────────────────────────────────────────────

def register(db: Session, data, base_url: str) -> Applicant:
    existing = db.query(Applicant).filter(Applicant.email == data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    # Without an email service there is no way to deliver the verification
    # link, so development environments auto-verify (recorded in the
    # notifications log either way).
    auto_verify = not settings.resend_api_key

    applicant = Applicant(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        email_verified=auto_verify,
        verify_token=None if auto_verify else secrets.token_hex(32),
    )
    db.add(applicant)
    db.commit()
    db.refresh(applicant)

    verify_link = f"{base_url}/verify.html?token={applicant.verify_token}"
    body = f"""
<p>Dear {applicant.full_name},</p>
<p>Welcome to the NSPD Ghana seafarer portal. Please confirm your email
address by clicking the link below:</p>
<p><a href="{verify_link}">{verify_link}</a></p>
<p>If you did not create this account, you can ignore this message.</p>
<p>— NSPD Ghana, Ghana Maritime Authority</p>
"""
    email_service.send_email(
        db,
        recipient=applicant.email,
        subject="NSPD Ghana — confirm your email address",
        html_body=body,
    )
    return applicant


def verify_email(db: Session, token: str) -> Applicant:
    if not token:
        raise HTTPException(status_code=400, detail="Verification token is required")
    applicant = db.query(Applicant).filter(Applicant.verify_token == token).first()
    if applicant is None:
        raise HTTPException(status_code=400, detail="Invalid or already-used verification link")
    applicant.email_verified = True
    applicant.verify_token = None
    db.commit()
    return applicant


# ──────────────────────────────────────────────
# Application lifecycle
# ──────────────────────────────────────────────

def get_my_application(db: Session, applicant_id: int):
    return (
        db.query(Application)
        .filter(Application.applicant_id == applicant_id)
        .order_by(Application.id.desc())
        .first()
    )


def _check_ghana_card_unique(db: Session, card_number: str, exclude_id: int = None) -> None:
    query = db.query(Application.id).filter(Application.ghana_card_number == card_number)
    if exclude_id is not None:
        query = query.filter(Application.id != exclude_id)
    if query.first() is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "An application with this Ghana Card number already exists. "
                "Contact the Ghana Maritime Authority if you believe it is yours."
            ),
        )


def _apply_form(app: Application, form) -> None:
    app.surname = form.surname.strip()
    app.first_name = form.first_name.strip()
    app.other_names = (form.other_names or "").strip() or None
    app.telephone = form.telephone.strip()
    app.ghana_card_number = form.ghana_card_number
    app.position_rank = form.position_rank.strip()
    app.short_courses_rmu = form.short_courses_rmu
    app.familiarisation_isps_gma = form.familiarisation_isps_gma
    app.attachment = form.attachment
    app.sea_experience = form.sea_experience
    app.medicals = form.medicals
    app.total_sea_experience_years = form.total_sea_experience_years
    app.last_ship_type = (form.last_ship_type or "").strip() or None


def create_application(db: Session, applicant: Applicant, form) -> Application:
    if get_my_application(db, applicant.id) is not None:
        raise HTTPException(
            status_code=409,
            detail="You already have an application. Edit it instead of submitting a new one.",
        )
    _check_ghana_card_unique(db, form.ghana_card_number)

    app = Application(
        applicant_id=applicant.id,
        email=applicant.email,
        submitted_at=func.now(),
        status="Pending",
    )
    _apply_form(app, form)
    db.add(app)
    db.commit()
    db.refresh(app)

    body = f"""
<p>Dear {app.first_name} {app.surname},</p>
<p>Your seafarer application has been received by the National Seafarer
Placement Database (NSPD) Ghana.</p>
<p>Your reference number is <strong>#{app.id}</strong>.</p>
<p>You will be notified by email when the status of your application changes.
You can also sign in to the portal at any time to track it.</p>
<p>— NSPD Ghana, Ghana Maritime Authority</p>
"""
    email_service.send_email(
        db,
        recipient=app.email,
        subject=f"NSPD Ghana — application received (ref #{app.id})",
        html_body=body,
        application_id=app.id,
    )
    return app


def update_application(db: Session, app: Application, form) -> tuple:
    """Update an editable application; returns (application, resubmitted)."""
    if app.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=403,
            detail=f"Your application is {app.status} and can no longer be edited.",
        )
    _check_ghana_card_unique(db, form.ghana_card_number, exclude_id=app.id)

    resubmitted = app.status == "Rejected"
    _apply_form(app, form)
    if resubmitted:
        app.status = "Pending"
        app.reviewed_by = None
        app.reviewed_at = None
        app.submitted_at = func.now()

    db.commit()
    db.refresh(app)
    return app, resubmitted
