"""
Export endpoints — restricted to Reviewer and Administrator roles,
matching require_role('Reviewer') in the PHP version. Every export is
written to the audit log (CSV/PDF exports contain applicant PII).

api/export-all-csv.php -> GET /api/exports/csv?search=&rank=&status=
api/export-pdf.php     -> GET /api/exports/pdf/{id}
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from ..auth import get_client_ip, require_role
from ..database import get_db
from ..services import application_service, audit_service, export_service

router = APIRouter(prefix="/api/exports", tags=["Exports"])


@router.get("/csv")
def export_csv(
    request: Request,
    search: str = Query("", max_length=200),
    rank: str = Query("", max_length=100),
    status: str = Query("", max_length=20),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Reviewer")),
):
    applications = application_service.fetch_for_export(
        db, search.strip(), rank.strip(), status.strip()
    )
    if not applications:
        raise HTTPException(status_code=404, detail="No submissions found matching the criteria.")

    csv_text = export_service.generate_csv(applications)
    filename = "nspd_submissions_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"

    audit_service.log(
        db,
        audit_service.EXPORT_CSV,
        user=user,
        entity="applications",
        details=f"rows={len(applications)} search='{search}' rank='{rank}' status='{status}'",
        ip=get_client_ip(request),
    )

    return Response(
        content=csv_text.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/pdf/{application_id}")
def export_pdf(
    application_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Reviewer")),
):
    if application_id <= 0:
        raise HTTPException(status_code=400, detail="Valid application ID is required")

    application = application_service.get_application(db, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    pdf_bytes = export_service.generate_submission_pdf(application)

    audit_service.log(
        db,
        audit_service.EXPORT_PDF,
        user=user,
        entity="application",
        entity_id=application_id,
        ip=get_client_ip(request),
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="submission_{application_id}.pdf"'
        },
    )
