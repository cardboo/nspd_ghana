"""
Outbound email notifications to applicants.

Uses the Resend HTTP API when RESEND_API_KEY is configured; otherwise the
message is recorded in the notifications table with status 'skipped' so
nothing is silently lost in development. Every attempt (sent / failed /
skipped) is logged to the notifications table.
"""

import logging

import requests
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Application, Notification

logger = logging.getLogger("nspd.email")

RESEND_ENDPOINT = "https://api.resend.com/emails"


def send_email(
    db: Session,
    recipient: str,
    subject: str,
    html_body: str,
    application_id: int = None,
) -> Notification:
    record = Notification(
        application_id=application_id,
        recipient=recipient,
        subject=subject[:200],
        body=html_body,
        status="pending",
    )

    if not settings.resend_api_key:
        record.status = "skipped"
        record.error = "RESEND_API_KEY not configured"
        logger.info("Email to %s skipped (no RESEND_API_KEY): %s", recipient, subject)
    else:
        try:
            response = requests.post(
                RESEND_ENDPOINT,
                json={
                    "from": settings.email_from,
                    "to": [recipient],
                    "subject": subject,
                    "html": html_body,
                },
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                timeout=10,
            )
            if response.status_code in (200, 201):
                record.status = "sent"
            else:
                record.status = "failed"
                record.error = f"HTTP {response.status_code}: {response.text[:250]}"
        except requests.RequestException as exc:
            record.status = "failed"
            record.error = str(exc)[:300]

    db.add(record)
    db.commit()
    return record


def notify_status_change(db: Session, application: Application, new_status: str) -> Notification:
    """Email the applicant when their application status changes."""
    full_name = f"{application.first_name} {application.surname}".strip()
    subject = f"NSPD Ghana — your application status is now: {new_status}"
    html_body = f"""
<p>Dear {full_name},</p>
<p>The status of your seafarer application (reference #{application.id})
with the National Seafarer Placement Database (NSPD) Ghana has been updated to:</p>
<p style="font-size:18px;font-weight:bold;">{new_status}</p>
<p>If you have any questions, please contact the Ghana Maritime Authority.</p>
<p>— NSPD Ghana, Ghana Maritime Authority</p>
"""
    return send_email(
        db,
        recipient=application.email,
        subject=subject,
        html_body=html_body,
        application_id=application.id,
    )
