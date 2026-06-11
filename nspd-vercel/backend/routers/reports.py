"""
Reports/analytics endpoints.

api/reports-data.php            -> GET /api/reports/data  (+ date range)
filter dropdowns (reports.php)  -> GET /api/reports/filters
data quality (new)              -> GET /api/reports/duplicates  (Reviewer+)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_role
from ..database import get_db
from ..services import application_service, report_service

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/data")
def report_data(
    rank: str = Query("", max_length=100),
    course: str = Query("", max_length=10),
    medical: str = Query("", max_length=10),
    ship_type: str = Query("", max_length=150),
    date_from: str = Query("", max_length=10),
    date_to: str = Query("", max_length=10),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return report_service.get_report_data(
        db,
        rank=rank,
        course=course,
        medical=medical,
        ship_type=ship_type,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/filters")
def report_filters(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return report_service.get_filter_options(db)


@router.get("/duplicates")
def duplicate_report(
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Reviewer")),
):
    return application_service.find_duplicates(db)
