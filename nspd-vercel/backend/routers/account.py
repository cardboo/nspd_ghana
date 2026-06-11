"""
Self-service account endpoints (any authenticated user).

GET  /api/account/profile      fresh profile from the database
POST /api/account/password     change own password
POST /api/account/2fa/setup    generate a TOTP secret (returns otpauth URI)
POST /api/account/2fa/enable   confirm a code and switch 2FA on
POST /api/account/2fa/disable  password + code to switch 2FA off
"""

import pyotp
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
from ..schemas import PasswordChangeRequest, TotpCodeRequest, TotpDisableRequest
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


# ──────────────────────────────────────────────
# Two-factor authentication (TOTP)
# ──────────────────────────────────────────────

def _fresh_user_or_401(db: Session, user: dict) -> User:
    fresh = db.get(User, user["id"])
    if fresh is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return fresh


@router.post("/2fa/setup")
def totp_setup(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Generate a new TOTP secret. 2FA stays off until /2fa/enable confirms a code."""
    fresh = _fresh_user_or_401(db, user)
    if fresh.totp_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is already enabled")

    fresh.totp_secret = pyotp.random_base32()
    db.commit()

    uri = pyotp.TOTP(fresh.totp_secret).provisioning_uri(
        name=fresh.email, issuer_name="NSPD Ghana"
    )
    return {"secret": fresh.totp_secret, "otpauth_uri": uri}


@router.post("/2fa/enable")
def totp_enable(
    body: TotpCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    fresh = _fresh_user_or_401(db, user)
    if fresh.totp_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is already enabled")
    if not fresh.totp_secret:
        raise HTTPException(status_code=400, detail="Run setup first to generate a secret")

    if not pyotp.TOTP(fresh.totp_secret).verify(body.code.strip(), valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid authentication code — try again")

    fresh.totp_enabled = True
    db.commit()
    audit_service.log(
        db,
        audit_service.TOTP_ENABLED,
        user=user,
        entity="user",
        entity_id=fresh.id,
        ip=get_client_ip(request),
    )
    return {"message": "Two-factor authentication enabled", "user": user_service.serialize(fresh)}


@router.post("/2fa/disable")
def totp_disable(
    body: TotpDisableRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    fresh = _fresh_user_or_401(db, user)
    if not fresh.totp_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")

    if not verify_password(body.password, fresh.password_hash):
        raise HTTPException(status_code=400, detail="Password is incorrect")
    if not pyotp.TOTP(fresh.totp_secret).verify(body.code.strip(), valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid authentication code")

    fresh.totp_enabled = False
    fresh.totp_secret = None
    db.commit()
    audit_service.log(
        db,
        audit_service.TOTP_DISABLED,
        user=user,
        entity="user",
        entity_id=fresh.id,
        ip=get_client_ip(request),
    )
    return {"message": "Two-factor authentication disabled", "user": user_service.serialize(fresh)}
