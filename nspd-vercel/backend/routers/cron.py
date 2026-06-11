"""
Scheduled maintenance endpoints, invoked by Vercel Cron (see the "crons"
section of vercel.json). Vercel sends `Authorization: Bearer <CRON_SECRET>`
when the CRON_SECRET environment variable is set on the project.

GET /api/cron/cleanup-unverified  delete unverified portal accounts older
                                  than UNVERIFIED_RETENTION_DAYS
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..services import audit_service, certification_service, recovery_service

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
