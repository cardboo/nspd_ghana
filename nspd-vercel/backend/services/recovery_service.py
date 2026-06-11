"""
Account recovery: self-service password reset (staff + applicants),
verification email resend, and stale unverified-account cleanup.

Design notes:
  - Reset tokens are single-use, random (64 hex chars), and expire after
    RESET_TOKEN_MINUTES. Expiry is stored and compared with the database
    clock (NOW()) so app/DB timezone differences cannot break it.
  - "Forgot password" endpoints never reveal whether an account exists —
    callers always return the same generic message.
"""

import re
import secrets

from fastapi import HTTPException
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from ..auth import hash_password
from ..config import settings
from ..models import Applicant, Application, User
from . import email_service


def _expiry_clause():
    minutes = int(settings.reset_token_minutes)
    return text(f"NOW() + INTERVAL {minutes} MINUTE")


def _reset_email_body(full_name: str, link: str) -> str:
    return f"""
<p>Dear {full_name},</p>
<p>A password reset was requested for your NSPD Ghana account. Click the
link below to choose a new password (valid for {settings.reset_token_minutes} minutes):</p>
<p><a href="{link}">{link}</a></p>
<p>If you did not request this, you can safely ignore this message —
your password has not been changed.</p>
<p>— NSPD Ghana, Ghana Maritime Authority</p>
"""


# ──────────────────────────────────────────────
# Staff password reset
# ──────────────────────────────────────────────

def issue_staff_reset(db: Session, identifier: str, base_url: str):
    """Issue a reset token for a staff account by username or email.

    Returns the user, or None when no (active) account matches — callers
    must respond identically either way.
    """
    user = (
        db.query(User)
        .filter(or_(User.username == identifier, User.email == identifier))
        .first()
    )
    if user is None or not user.is_active:
        return None

    user.reset_token = secrets.token_hex(32)
    user.reset_token_expires = _expiry_clause()
    db.commit()
    db.refresh(user)

    link = f"{base_url}/reset-password.html?for=staff&token={user.reset_token}"
    email_service.send_email(
        db,
        recipient=user.email,
        subject="NSPD Ghana — password reset",
        html_body=_reset_email_body(user.full_name, link),
    )
    return user


def complete_staff_reset(db: Session, token: str, new_password: str) -> User:
    user = (
        db.query(User)
        .filter(
            User.reset_token == token,
            User.reset_token_expires > text("NOW()"),
            User.is_active.is_(True),
        )
        .first()
    )
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    user.password_hash = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    user.must_change_password = False
    db.commit()
    db.refresh(user)
    return user


# ──────────────────────────────────────────────
# Applicant password reset
# ──────────────────────────────────────────────

def issue_portal_reset(db: Session, email: str, base_url: str):
    applicant = db.query(Applicant).filter(Applicant.email == email).first()
    if applicant is None or not applicant.is_active:
        return None

    applicant.reset_token = secrets.token_hex(32)
    applicant.reset_token_expires = _expiry_clause()
    db.commit()
    db.refresh(applicant)

    link = f"{base_url}/reset-password.html?for=portal&token={applicant.reset_token}"
    email_service.send_email(
        db,
        recipient=applicant.email,
        subject="NSPD Ghana — password reset",
        html_body=_reset_email_body(applicant.full_name, link),
    )
    return applicant


def complete_portal_reset(db: Session, token: str, new_password: str) -> Applicant:
    applicant = (
        db.query(Applicant)
        .filter(
            Applicant.reset_token == token,
            Applicant.reset_token_expires > text("NOW()"),
            Applicant.is_active.is_(True),
        )
        .first()
    )
    if applicant is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    applicant.password_hash = hash_password(new_password)
    applicant.reset_token = None
    applicant.reset_token_expires = None
    # A successful email-based reset also proves mailbox ownership
    applicant.email_verified = True
    applicant.verify_token = None
    db.commit()
    db.refresh(applicant)
    return applicant


# ──────────────────────────────────────────────
# Portal invitations (staff-initiated outreach)
# ──────────────────────────────────────────────

EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def invite_for_application(db: Session, application, base_url: str) -> tuple:
    """Create (or refresh) a portal account for an application's email,
    link the record, and send a set-your-password invitation.

    Returns (applicant, resent) — resent is True when the invitation was
    re-issued for an account that hasn't been used yet. Raises 409 once
    the account has actually been used (they should use forgot-password).
    """
    email = (application.email or "").strip()
    if not EMAIL_SHAPE.fullmatch(email):
        raise HTTPException(
            status_code=400,
            detail="This record has no valid email address — correct it before inviting.",
        )

    applicant = db.query(Applicant).filter(Applicant.email == email).first()
    resent = applicant is not None

    if applicant is not None:
        if applicant.last_login is not None:
            raise HTTPException(
                status_code=409,
                detail="This seafarer already has an active portal account. "
                       "They can use Forgot Password to regain access.",
            )
        if not applicant.is_active:
            raise HTTPException(status_code=409, detail="This portal account has been deactivated.")
    else:
        full_name = f"{application.first_name or ''} {application.surname or ''}".strip() or email
        applicant = Applicant(
            email=email,
            # Unusable until the invitation link sets a real one
            password_hash=hash_password(secrets.token_hex(16)),
            full_name=full_name[:150],
            email_verified=False,
            is_active=True,
        )
        db.add(applicant)
        db.flush()

    # Link the record now: the only way into this account is the emailed
    # link, so mailbox ownership equals record ownership.
    if application.applicant_id is None:
        application.applicant_id = applicant.id
    elif application.applicant_id != applicant.id:
        raise HTTPException(status_code=409, detail="This record is linked to a different account.")

    days = int(settings.invite_expires_days)
    applicant.reset_token = secrets.token_hex(32)
    applicant.reset_token_expires = text(f"NOW() + INTERVAL {days} DAY")
    applicant.invited_at = func.now()
    db.commit()
    db.refresh(applicant)

    link = f"{base_url}/reset-password.html?for=portal&token={applicant.reset_token}"
    email_service.send_email(
        db,
        recipient=applicant.email,
        subject="NSPD Ghana — your seafarer portal account",
        html_body=f"""
<p>Dear {applicant.full_name},</p>
<p>The Ghana Maritime Authority has created a seafarer portal account for
you on the National Seafarer Placement Database (NSPD). Your existing
application (reference <strong>#{application.id}</strong>) is linked to it.</p>
<p>Click the link below to set your password (valid for {days} days):</p>
<p><a href="{link}">{link}</a></p>
<p>On the portal you can track your application status, upload documents
and certificate renewals, and record your sea service.</p>
<p>If the link has expired, contact the GMA or use Forgot Password on the
portal sign-in page.</p>
<p>— NSPD Ghana, Ghana Maritime Authority</p>
""",
        application_id=application.id,
    )
    return applicant, resent


# ──────────────────────────────────────────────
# Verification email resend
# ──────────────────────────────────────────────

def resend_verification(db: Session, email: str, base_url: str):
    """Re-send the verification link. Returns the applicant or None
    (callers respond identically either way)."""
    applicant = db.query(Applicant).filter(Applicant.email == email).first()
    if applicant is None or applicant.email_verified or not applicant.is_active:
        return None

    applicant.verify_token = secrets.token_hex(32)
    db.commit()
    db.refresh(applicant)

    link = f"{base_url}/verify.html?token={applicant.verify_token}"
    email_service.send_email(
        db,
        recipient=applicant.email,
        subject="NSPD Ghana — confirm your email address",
        html_body=f"""
<p>Dear {applicant.full_name},</p>
<p>Please confirm your email address for the NSPD Ghana seafarer portal:</p>
<p><a href="{link}">{link}</a></p>
<p>If you did not create this account, you can ignore this message.</p>
<p>— NSPD Ghana, Ghana Maritime Authority</p>
""",
    )
    return applicant


# ──────────────────────────────────────────────
# Stale unverified account cleanup (cron)
# ──────────────────────────────────────────────

def cleanup_unverified(db: Session) -> int:
    """Delete accounts never verified within the retention window.

    Unverified accounts cannot sign in, so they can't own an application;
    the ownership check is defence in depth.
    """
    days = int(settings.unverified_retention_days)
    stale = (
        db.query(Applicant)
        .filter(
            Applicant.email_verified.is_(False),
            Applicant.created_at < text(f"NOW() - INTERVAL {days} DAY"),
        )
        .all()
    )

    deleted = 0
    for applicant in stale:
        has_application = (
            db.query(Application.id)
            .filter(Application.applicant_id == applicant.id)
            .first()
        )
        if has_application:
            continue
        db.delete(applicant)
        deleted += 1

    db.commit()
    return deleted
