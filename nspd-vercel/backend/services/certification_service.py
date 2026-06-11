"""
Certification & medical record lifecycle tracking.

The original registry stored only Yes/No flags; this gives each
certificate real issue/expiry dates so the system can drive a staff
expiry watchlist and automated applicant alerts.

Expiry status (computed against today's date):
  expired       expires_on in the past
  expiring_soon expires within EXPIRY_WARNING_DAYS
  valid         expires later than that
  no_expiry     no expiry date recorded
"""

import datetime as dt

from fastapi import HTTPException
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Application, Certification
from . import email_service

# Re-alert an applicant about the same certificate at most every 14 days
ALERT_REPEAT_DAYS = 14


def _status(cert: Certification, today: dt.date) -> str:
    if cert.expires_on is None:
        return "no_expiry"
    if cert.expires_on < today:
        return "expired"
    if cert.expires_on <= today + dt.timedelta(days=settings.expiry_warning_days):
        return "expiring_soon"
    return "valid"


def serialize(cert: Certification, today: dt.date = None) -> dict:
    today = today or dt.date.today()
    return {
        "id": cert.id,
        "application_id": cert.application_id,
        "cert_type": cert.cert_type,
        "title": cert.title,
        "issued_on": cert.issued_on.isoformat() if cert.issued_on else None,
        "expires_on": cert.expires_on.isoformat() if cert.expires_on else None,
        "issuer": cert.issuer,
        "added_by": cert.added_by,
        "status": _status(cert, today),
        "created_at": cert.created_at.isoformat() if cert.created_at else None,
    }


def list_for_application(db: Session, application_id: int) -> list:
    today = dt.date.today()
    rows = (
        db.query(Certification)
        .filter(Certification.application_id == application_id)
        .order_by(Certification.expires_on.is_(None), Certification.expires_on.asc())
        .all()
    )
    return [serialize(c, today) for c in rows]


def create(db: Session, application_id: int, form, added_by: int = None) -> Certification:
    if form.issued_on and form.expires_on and form.expires_on < form.issued_on:
        raise HTTPException(status_code=400, detail="Expiry date cannot be before the issue date")

    cert = Certification(
        application_id=application_id,
        cert_type=form.cert_type,
        title=form.title.strip(),
        issued_on=form.issued_on,
        expires_on=form.expires_on,
        issuer=(form.issuer or "").strip() or None,
        added_by=added_by,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


def get_or_404(db: Session, certification_id: int) -> Certification:
    cert = db.get(Certification, certification_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="Certification not found")
    return cert


def delete(db: Session, cert: Certification) -> None:
    db.delete(cert)
    db.commit()


def count_expiring(db: Session) -> int:
    """Certificates expired or expiring within the warning window (dashboard card)."""
    horizon = dt.date.today() + dt.timedelta(days=settings.expiry_warning_days)
    return (
        db.query(func.count(Certification.id))
        .filter(Certification.expires_on.isnot(None), Certification.expires_on <= horizon)
        .scalar()
        or 0
    )


def expiring_watchlist(db: Session, days: int) -> list:
    """Certificates expired or expiring within `days`, with seafarer context."""
    today = dt.date.today()
    horizon = today + dt.timedelta(days=days)
    rows = (
        db.query(Certification, Application)
        .join(Application, Certification.application_id == Application.id)
        .filter(Certification.expires_on.isnot(None), Certification.expires_on <= horizon)
        .order_by(Certification.expires_on.asc())
        .all()
    )
    items = []
    for cert, app in rows:
        entry = serialize(cert, today)
        entry["seafarer"] = {
            "application_id": app.id,
            "surname": app.surname,
            "first_name": app.first_name,
            "email": app.email,
            "position_rank": app.position_rank,
            "application_status": app.status,
        }
        items.append(entry)
    return items


def send_expiry_alerts(db: Session) -> dict:
    """Email applicants whose certificates are expired or expiring soon.

    Called by the weekly cron. Alerts repeat at most every ALERT_REPEAT_DAYS
    per certificate (tracked via last_alerted_at).
    """
    today = dt.date.today()
    horizon = today + dt.timedelta(days=settings.expiry_alert_days)

    due = (
        db.query(Certification, Application)
        .join(Application, Certification.application_id == Application.id)
        .filter(
            Certification.expires_on.isnot(None),
            Certification.expires_on <= horizon,
            (Certification.last_alerted_at.is_(None))
            | (Certification.last_alerted_at < text(f"NOW() - INTERVAL {ALERT_REPEAT_DAYS} DAY")),
        )
        .order_by(Certification.application_id, Certification.expires_on.asc())
        .all()
    )

    # Group by application so each seafarer gets one email listing everything
    grouped = {}
    for cert, app in due:
        grouped.setdefault(app.id, {"application": app, "certs": []})["certs"].append(cert)

    emails_sent = 0
    for entry in grouped.values():
        app = entry["application"]
        lines = []
        for cert in entry["certs"]:
            state = "EXPIRED" if cert.expires_on < today else "expires"
            lines.append(
                f"<li><strong>{cert.title}</strong> ({cert.cert_type}) — "
                f"{state} {cert.expires_on.strftime('%B %d, %Y')}</li>"
            )
        body = f"""
<p>Dear {app.first_name} {app.surname},</p>
<p>The following certificates on your NSPD Ghana record need attention:</p>
<ul>{''.join(lines)}</ul>
<p>Please renew them and upload the updated documents on the seafarer portal,
or contact the Ghana Maritime Authority for assistance.</p>
<p>— NSPD Ghana, Ghana Maritime Authority</p>
"""
        email_service.send_email(
            db,
            recipient=app.email,
            subject="NSPD Ghana — certificate expiry notice",
            html_body=body,
            application_id=app.id,
        )
        for cert in entry["certs"]:
            cert.last_alerted_at = func.now()
        db.commit()
        emails_sent += 1

    return {"applicants_notified": emails_sent, "certificates": len(due)}
