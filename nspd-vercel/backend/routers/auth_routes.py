"""
Authentication endpoints.

login.php (POST)  -> POST /api/auth/login   (now with DB-backed lockout)
logout.php        -> POST /api/auth/logout
session check     -> GET  /api/auth/me
"""

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import (
    clear_auth_cookie,
    create_access_token,
    create_preauth_token,
    decode_preauth_token,
    get_client_ip,
    get_current_user,
    set_auth_cookie,
    verify_password,
)
from ..config import settings
from ..database import get_db
from ..models import User
from ..schemas import (
    CompleteResetRequest,
    ForgotPasswordRequest,
    LoginRequest,
    TotpLoginRequest,
    UserOut,
)
from ..services import audit_service, recovery_service, throttle_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

GENERIC_RESET_MESSAGE = (
    "If an account with that username or email exists, a password reset link has been sent."
)


def _base_url(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}"


@router.post("/login")
def login(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    ip = get_client_ip(request)

    # DB-backed rate limiting (serverless functions cannot keep
    # in-memory counters between invocations)
    if throttle_service.is_locked_out(db, credentials.username, ip):
        audit_service.log(
            db, audit_service.LOGIN_LOCKED, username=credentials.username, ip=ip
        )
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many failed login attempts. "
                f"Please try again in {settings.lockout_window_minutes} minutes."
            ),
        )

    user = db.query(User).filter(User.username == credentials.username).first()

    if user is None or not verify_password(credentials.password, user.password_hash):
        throttle_service.record_failure(db, credentials.username, ip)
        audit_service.log(
            db, audit_service.LOGIN_FAILED, username=credentials.username, ip=ip
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        audit_service.log(
            db, audit_service.LOGIN_DISABLED, username=credentials.username, ip=ip
        )
        raise HTTPException(status_code=401, detail="This account has been deactivated")

    # Two-factor: password accepted, but the session is only issued after
    # the TOTP step. The failure counter is NOT cleared yet.
    if user.totp_enabled and user.totp_secret:
        return {"totp_required": True, "pre_auth_token": create_preauth_token(user)}

    return _complete_login(db, user, ip, response)


def _complete_login(db: Session, user: User, ip: str, response: Response) -> dict:
    """Shared final step of login: clear failures, stamp last_login, set cookie."""
    throttle_service.record_success(db, user.username, ip)
    user.last_login = func.now()
    db.commit()

    audit_service.log(
        db,
        audit_service.LOGIN_SUCCESS,
        user={"id": user.id, "username": user.username},
        ip=ip,
    )

    token = create_access_token(user)
    set_auth_cookie(response, token)

    return {
        "user": UserOut(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            email=user.email,
            must_change_password=bool(user.must_change_password),
        )
    }


@router.post("/totp")
def totp_login(
    body: TotpLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Complete a two-factor login with the authenticator code."""
    ip = get_client_ip(request)
    user_id = decode_preauth_token(body.pre_auth_token.strip())

    user = db.get(User, user_id)
    if user is None or not user.is_active or not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Failed codes count toward the same lockout as failed passwords
    if throttle_service.is_locked_out(db, user.username, ip):
        audit_service.log(db, audit_service.LOGIN_LOCKED, username=user.username, ip=ip)
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many failed login attempts. "
                f"Please try again in {settings.lockout_window_minutes} minutes."
            ),
        )

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(body.code.strip(), valid_window=1):
        throttle_service.record_failure(db, user.username, ip)
        audit_service.log(db, audit_service.LOGIN_TOTP_FAILED, username=user.username, ip=ip)
        raise HTTPException(status_code=401, detail="Invalid authentication code")

    return _complete_login(db, user, ip, response)


@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = get_client_ip(request)
    identity = throttle_service.ip_identity("pwreset", ip)
    if throttle_service.is_rate_limited(db, identity, settings.lockout_max_attempts):
        raise HTTPException(status_code=429, detail="Too many reset requests. Please try again later.")
    throttle_service.record_event(db, identity, ip)

    user = recovery_service.issue_staff_reset(db, body.identifier.strip(), _base_url(request))
    if user is not None:
        audit_service.log(
            db,
            audit_service.PASSWORD_RESET_REQUESTED,
            username=user.username,
            entity="user",
            entity_id=user.id,
            ip=ip,
        )
    # Identical response whether or not the account exists
    return {"message": GENERIC_RESET_MESSAGE}


@router.post("/reset-password")
def reset_password(
    body: CompleteResetRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = recovery_service.complete_staff_reset(db, body.token.strip(), body.new_password)
    audit_service.log(
        db,
        audit_service.PASSWORD_RESET_COMPLETED,
        username=user.username,
        entity="user",
        entity_id=user.id,
        ip=get_client_ip(request),
    )
    return {"message": "Password reset successfully. You can now sign in."}


@router.post("/logout")
def logout(response: Response):
    clear_auth_cookie(response)
    return {"message": "Logged out successfully"}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {"user": user}
