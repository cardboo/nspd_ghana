"""
User administration — Administrator only.

GET  /api/users                      list users
POST /api/users                      create user (temp password, forced change)
PUT  /api/users/{id}                 update name/email/role/active
POST /api/users/{id}/reset-password  set a temp password (forced change)
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..auth import get_client_ip, require_role
from ..database import get_db
from ..schemas import ResetPasswordRequest, UserCreateRequest, UserUpdateRequest
from ..services import audit_service, user_service

router = APIRouter(prefix="/api/users", tags=["User Management"])

admin_required = Depends(require_role("Administrator"))


@router.get("")
def list_users(
    db: Session = Depends(get_db),
    user: dict = admin_required,
):
    return {"users": user_service.list_users(db)}


@router.post("", status_code=201)
def create_user(
    body: UserCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = admin_required,
):
    created = user_service.create_user(db, body)
    audit_service.log(
        db,
        audit_service.USER_CREATED,
        user=user,
        entity="user",
        entity_id=created.id,
        details=f"{created.username} ({created.role})",
        ip=get_client_ip(request),
    )
    return {"user": user_service.serialize(created)}


@router.put("/{user_id}")
def update_user(
    user_id: int,
    body: UserUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = admin_required,
):
    updated = user_service.update_user(db, user_id, body, user)
    changes = body.model_dump(exclude_none=True)
    audit_service.log(
        db,
        audit_service.USER_UPDATED,
        user=user,
        entity="user",
        entity_id=updated.id,
        details=f"{updated.username}: {changes}",
        ip=get_client_ip(request),
    )
    return {"user": user_service.serialize(updated)}


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: int,
    body: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = admin_required,
):
    updated = user_service.reset_password(db, user_id, body.temp_password)
    audit_service.log(
        db,
        audit_service.USER_PASSWORD_RESET,
        user=user,
        entity="user",
        entity_id=updated.id,
        details=updated.username,
        ip=get_client_ip(request),
    )
    return {"user": user_service.serialize(updated)}
