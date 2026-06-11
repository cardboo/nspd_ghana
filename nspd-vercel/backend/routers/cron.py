"""
Scheduled maintenance endpoints, invoked by Vercel Cron (see the "crons"
section of vercel.json). Vercel sends `Authorization: Bearer <CRON_SECRET>`
when the CRON_SECRET environment variable is set on the project.

GET /api/cron/cleanup-unverified  delete unverified portal accounts older
                                  than UNVERIFIED_RETENTION_DAYS
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from sqlalchemy import func, text

from ..config import settings
from ..database import get_db
from ..models import Application, User
from ..services import (
    application_service,
    audit_service,
    certification_service,
    email_service,
    recovery_service,
)

router = APIRouter(prefix="/api/cron", tags=["Scheduled Jobs"])


def _check_cron_auth(request: Request) -> None:
    if settings.cron_secret:
        header = request.headers.get("authorization", "")
        if header != f"Bearer {settings.cron_secret}":
            raise HTTPException(status_code=401, detail="Unauthorized")
    elif settings.is_vercel:
        # Never expose an unauthenticated maintenance endpoint in production
        raise HTTPException(status_code=503, detail="CRON_SECRET is not configured")
    # Local development without a secret: allowed


@router.get("/cleanup-unverified")
def cleanup_unverified(
    request: Request,
    db: Session = Depends(get_db),
):
    _check_cron_auth(request)
    deleted = recovery_service.cleanup_unverified(db)
    if deleted:
        audit_service.log(
            db,
            audit_service.UNVERIFIED_CLEANUP,
            username="cron",
            entity="applicant",
            details=f"deleted {deleted} unverified accounts older than "
                    f"{settings.unverified_retention_days} days",
        )
    return {"deleted": deleted, "retention_days": settings.unverified_retention_days}


@router.get("/weekly-digest")
def weekly_digest(
    request: Request,
    db: Session = Depends(get_db),
):
    """Weekly: email every active Administrator a registry summary."""
    _check_cron_auth(request)

    stats = application_service.get_dashboard_stats(db)
    new_last_week = (
        db.query(func.count(Application.id))
        .filter(Application.submitted_at >= text("NOW() - INTERVAL 7 DAY"))
        .scalar()
        or 0
    )
    status_counts = stats["status_counts"]

    rows = "".join(
        f"<tr><td style='padding:4px 12px 4px 0;'>{label}</td>"
        f"<td style='padding:4px 0;'><strong>{value}</strong></td></tr>"
        for label, value in [
            ("New submissions (last 7 days)", new_last_week),
            ("Total submissions", stats["total_submissions"]),
            ("Pending review", stats["pending_review"]),
            ("Approved", status_counts.get("Approved", 0)),
            ("Rejected", status_counts.get("Rejected", 0)),
            (f"Certificates expiring (≤{settings.expiry_warning_days}d)", stats["expiring_certs"]),
            ("Seafarers currently on board", stats["onboard_count"]),
        ]
    )
    body = f"""
<p>Hello,</p>
<p>Here is this week's NSPD Ghana registry summary:</p>
<table>{rows}</table>
<p>Sign in to the dashboard for details.</p>
<p>— NSPD Ghana, automated weekly digest</p>
"""

    admins = (
        db.query(User)
        .filter(User.role == "Administrator", User.is_active.is_(True))
        .all()
    )
    for admin in admins:
        email_service.send_email(
            db,
            recipient=admin.email,
            subject="NSPD Ghana — weekly registry digest",
            html_body=body,
        )

    if admins:
        audit_service.log(
            db,
            audit_service.WEEKLY_DIGEST,
            username="cron",
            details=f"sent to {len(admins)} administrators",
        )
    return {"recipients": len(admins), "new_last_week": int(new_last_week)}


@router.get("/expiry-alerts")
def expiry_alerts(
    request: Request,
    db: Session = Depends(get_db),
):
    """Weekly: email applicants whose certificates are expired or expiring soon."""
    _check_cron_auth(request)
    result = certification_service.send_expiry_alerts(db)
    if result["applicants_notified"]:
        audit_service.log(
            db,
            audit_service.EXPIRY_ALERTS,
            username="cron",
            entity="certifications",
            details=(
                f"notified {result['applicants_notified']} applicants about "
                f"{result['certificates']} certificates"
            ),
        )
    return result
