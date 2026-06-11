"""
Self-service account endpoints (any authenticated user).

GET  /api/account/profile   fresh profile from the database
POST /api/account/password  change own password
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..auth import (
    create_access_token,
    get_client_ip,
    get_current_user,
    hash_password,
    set_auth_cookie,
    verify_password,
)
from ..database import get_db
from ..models import User
from ..schemas import PasswordChangeRequest
from ..services import audit_service, user_service

router = APIRouter(prefix="/api/account", tags=["Account"])


@router.get("/profile")
def profile(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    fresh = db.get(User, user["id"])
    if fresh is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"user": user_service.serialize(fresh)}


@router.post("/password")
def change_password(
    body: PasswordChangeRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    fresh = db.get(User, user["id"])
    if fresh is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not verify_password(body.current_password, fresh.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if body.new_password == body.current_password:
        raise HTTPException(status_code=400, detail="New password must be different from the current one")

    fresh.password_hash = hash_password(body.new_password)
    fresh.must_change_password = False
    db.commit()

    audit_service.log(
        db,
        audit_service.PASSWORD_CHANGED,
        user=user,
        entity="user",
        entity_id=fresh.id,
        ip=get_client_ip(request),
    )

    # Re-issue the JWT so the pwd_change claim is cleared immediately
    token = create_access_token(fresh)
    set_auth_cookie(response, token)

    return {"message": "Password changed successfully", "user": user_service.serialize(fresh)}
