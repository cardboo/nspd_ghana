"""
Audit log browsing — Administrator only.

GET /api/audit?page=&action=&username=
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..services import audit_service

router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("")
def list_audit_entries(
    page: int = Query(1, ge=1),
    action: str = Query("", max_length=50),
    username: str = Query("", max_length=50),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Administrator")),
):
    return audit_service.list_entries(db, page=page, action=action.strip(), username=username.strip())
