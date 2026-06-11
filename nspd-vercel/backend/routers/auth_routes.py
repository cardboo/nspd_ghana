"""
Authentication endpoints.

login.php (POST)  -> POST /api/auth/login   (now with DB-backed lockout)
logout.php        -> POST /api/auth/logout
session check     -> GET  /api/auth/me
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import (
    clear_auth_cookie,
    create_access_token,
    get_client_ip,
    get_current_user,
    set_auth_cookie,
    verify_password,
)
from ..config import settings
from ..database import get_db
from ..models import User
from ..schemas import CompleteResetRequest, ForgotPasswordRequest, LoginRequest, UserOut
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

    # Successful login: clear the failure counter, update last_login
    throttle_service.record_success(db, credentials.username, ip)
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
