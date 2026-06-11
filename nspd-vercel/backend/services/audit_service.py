"""
Audit logging.

Records who did what and when — particularly PII-relevant operations
(CSV/PDF exports), review decisions, user administration, and auth events.
Each entry commits immediately so audit rows survive later failures in
the same request.
"""

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import AuditLog

# Action vocabulary (kept as plain strings in the DB for easy querying)
LOGIN_SUCCESS = "login_success"
LOGIN_FAILED = "login_failed"
LOGIN_LOCKED = "login_locked"
LOGIN_DISABLED = "login_disabled"
PASSWORD_CHANGED = "password_changed"
EXPORT_CSV = "export_csv"
EXPORT_PDF = "export_pdf"
STATUS_CHANGED = "status_changed"
COMMENT_ADDED = "comment_added"
COMMENT_DELETED = "comment_deleted"
DOCUMENT_UPLOADED = "document_uploaded"
DOCUMENT_DELETED = "document_deleted"
USER_CREATED = "user_created"
USER_UPDATED = "user_updated"
USER_PASSWORD_RESET = "user_password_reset"
PORTAL_REGISTERED = "portal_registered"
PORTAL_VERIFIED = "portal_verified"
PORTAL_LOGIN_SUCCESS = "portal_login_success"
PORTAL_LOGIN_FAILED = "portal_login_failed"
PORTAL_LOGIN_LOCKED = "portal_login_locked"
APPLICATION_SUBMITTED = "application_submitted"
APPLICATION_UPDATED = "application_updated"
APPLICATION_RESUBMITTED = "application_resubmitted"
PASSWORD_RESET_REQUESTED = "password_reset_requested"
PASSWORD_RESET_COMPLETED = "password_reset_completed"
VERIFICATION_RESENT = "verification_resent"
APPLICANT_UPDATED = "applicant_updated"
UNVERIFIED_CLEANUP = "unverified_cleanup"
CERT_ADDED = "certification_added"
CERT_DELETED = "certification_deleted"
EXPIRY_ALERTS = "expiry_alerts_sent"
VOYAGE_ADDED = "voyage_added"
VOYAGE_DELETED = "voyage_deleted"
APPLICATION_CLAIMED = "application_claimed"
DOCUMENT_VERIFIED = "document_verified"
BULK_STATUS = "bulk_status_change"
TOTP_ENABLED = "totp_enabled"
TOTP_DISABLED = "totp_disabled"
LOGIN_TOTP_FAILED = "login_totp_failed"
WEEKLY_DIGEST = "weekly_digest_sent"


def log(
    db: Session,
    action: str,
    user: Optional[dict] = None,
    username: Optional[str] = None,
    entity: Optional[str] = None,
    entity_id: Optional[int] = None,
    details: Optional[str] = None,
    ip: Optional[str] = None,
) -> None:
    entry = AuditLog(
        user_id=user["id"] if user else None,
        username=(user["username"] if user else username) or "-",
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=(details or "")[:500] or None,
        ip_address=ip,
    )
    db.add(entry)
    db.commit()


def serialize(entry: AuditLog) -> dict:
    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "username": entry.username,
        "action": entry.action,
        "entity": entry.entity,
        "entity_id": entry.entity_id,
        "details": entry.details,
        "ip_address": entry.ip_address,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


def list_entries(db: Session, page: int, action: str, username: str, per_page: int = 25) -> dict:
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if username:
        filters.append(AuditLog.username.like(f"%{username}%"))

    total = db.query(func.count(AuditLog.id)).filter(*filters).scalar() or 0
    total_pages = max(1, -(-total // per_page))
    page = min(max(1, page), total_pages)

    rows = (
        db.query(AuditLog)
        .filter(*filters)
        .order_by(AuditLog.id.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
        .all()
    )

    actions = [r[0] for r in db.query(AuditLog.action).distinct().order_by(AuditLog.action).all()]

    return {
        "items": [serialize(r) for r in rows],
        "total": int(total),
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "actions": actions,
    }
