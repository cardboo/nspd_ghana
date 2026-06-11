"""
DB-backed login throttling shared by the staff login and the applicant
portal (serverless functions cannot keep in-memory counters between
invocations).

Failures are keyed by an identity string (staff username, or the
"portal:<email>" form for applicants). The per-IP limit is 4x the
per-identity one so a single attacked account doesn't lock out every
user behind a shared office NAT, while password-spraying from one
address is still cut off.
"""

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ..config import settings
from ..models import LoginAttempt


def _window_clause():
    # settings value is an int from config; safe to inline
    minutes = int(settings.lockout_window_minutes)
    return text(f"NOW() - INTERVAL {minutes} MINUTE")


def is_locked_out(db: Session, identity: str, ip: str) -> bool:
    window = _window_clause()

    identity_failures = (
        db.query(func.count(LoginAttempt.id))
        .filter(
            LoginAttempt.success.is_(False),
            LoginAttempt.username == identity,
            LoginAttempt.attempted_at >= window,
        )
        .scalar()
        or 0
    )
    if identity_failures >= settings.lockout_max_attempts:
        return True

    if not ip:
        return False
    ip_failures = (
        db.query(func.count(LoginAttempt.id))
        .filter(
            LoginAttempt.success.is_(False),
            LoginAttempt.ip_address == ip,
            LoginAttempt.attempted_at >= window,
        )
        .scalar()
        or 0
    )
    return ip_failures >= settings.lockout_max_attempts * 4


def record_failure(db: Session, identity: str, ip: str) -> None:
    db.add(LoginAttempt(username=identity, ip_address=ip or None, success=False))
    db.commit()


def record_success(db: Session, identity: str, ip: str) -> None:
    """Clear the failure counter for this identity and log the success."""
    db.query(LoginAttempt).filter(
        LoginAttempt.username == identity,
        LoginAttempt.success.is_(False),
    ).delete()
    db.add(LoginAttempt(username=identity, ip_address=ip or None, success=True))
    db.commit()


def portal_identity(email: str) -> str:
    """Identity key for applicant logins (fits the 50-char username column)."""
    return ("portal:" + email)[:50]
