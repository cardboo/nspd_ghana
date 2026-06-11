"""
Dashboard statistics.

dashboard.php (PHP-side queries) -> GET /api/dashboard/stats
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..services import application_service

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return application_service.get_dashboard_stats(db)
