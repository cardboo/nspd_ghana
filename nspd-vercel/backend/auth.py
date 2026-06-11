"""
JWT authentication and role-based access control.

Replaces includes/auth.php. PHP server-side sessions cannot work on
stateless serverless functions, so the session is replaced by a signed JWT
stored in an httpOnly, SameSite=Strict cookie:

  - httpOnly        -> not readable from JavaScript (like PHP's httponly)
  - SameSite=Strict -> browsers won't attach it to cross-site requests,
                       which (together with JSON-only request bodies)
                       replaces the PHP CSRF token
  - no Max-Age      -> session cookie, expires when the browser closes
                       (like PHP's lifetime=0); the JWT `exp` claim caps
                       the total lifetime server-side

The role hierarchy (Administrator > Reviewer > Viewer) is preserved.
"""

import datetime as dt

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Response

from .config import settings

COOKIE_NAME = "access_token"

ROLE_HIERARCHY = {
    "Viewer": 1,
    "Reviewer": 2,
    "Administrator": 3,
}


# ──────────────────────────────────────────────
# Password hashing (bcrypt, PHP-compatible)
# ──────────────────────────────────────────────

def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash.

    PHP's password_hash() emits the `$2y$` bcrypt prefix while Python's
    bcrypt expects `$2b$`; the algorithms are identical, so existing user
    hashes keep working after normalising the prefix.
    """
    if not password_hash:
        return False
    if password_hash.startswith("$2y$"):
        password_hash = "$2b$" + password_hash[4:]
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def hash_password(plain_password: str) -> str:
    """Hash a password. The `$2b$` output is also accepted by PHP's password_verify()."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# ──────────────────────────────────────────────
# JWT tokens
# ──────────────────────────────────────────────

def create_access_token(user) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "realm": "staff",
        "sub": str(user.id),
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "email": user.email,
        "pwd_change": bool(user.must_change_password),
        "iat": now,
        "exp": now + dt.timedelta(hours=settings.jwt_expires_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


# ──────────────────────────────────────────────
# FastAPI dependencies (replace require_auth / require_role)
# ──────────────────────────────────────────────

# Endpoints a user may still call while a password change is being forced
PASSWORD_CHANGE_ALLOWED_PATHS = {
    "/api/auth/me",
    "/api/auth/logout",
    "/api/account/profile",
    "/api/account/password",
}


def get_current_user(request: Request) -> dict:
    """Return the authenticated staff user from the JWT cookie, or raise 401."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Applicant-realm tokens must never grant staff access
    if payload.get("realm", "staff") != "staff":
        raise HTTPException(status_code=401, detail="Unauthorized")

    must_change = bool(payload.get("pwd_change"))
    if must_change and request.url.path not in PASSWORD_CHANGE_ALLOWED_PATHS:
        raise HTTPException(status_code=403, detail="Password change required")

    return {
        "id": int(payload["sub"]),
        "username": payload.get("username", ""),
        "full_name": payload.get("full_name", "User"),
        "role": payload.get("role", "Viewer"),
        "email": payload.get("email", ""),
        "must_change_password": must_change,
    }


def get_client_ip(request: Request) -> str:
    """Client IP, honouring Vercel's x-forwarded-for header."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return (request.client.host if request.client else "")[:45]


# ──────────────────────────────────────────────
# Two-factor authentication (TOTP) pre-auth tokens
# ──────────────────────────────────────────────

PREAUTH_REALM = "2fa-pending"
PREAUTH_MINUTES = 5


def create_preauth_token(user) -> str:
    """Short-lived token proving the password step passed, pending TOTP.

    Grants no API access: get_current_user / get_current_applicant both
    reject this realm.
    """
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "realm": PREAUTH_REALM,
        "sub": str(user.id),
        "iat": now,
        "exp": now + dt.timedelta(minutes=PREAUTH_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_preauth_token(token: str) -> int:
    """Return the pending user id, or raise 401."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Sign-in session expired. Please log in again.")
    if payload.get("realm") != PREAUTH_REALM:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return int(payload["sub"])


# ──────────────────────────────────────────────
# Applicant portal realm (separate cookie + JWT realm so an applicant
# session can never be replayed against staff endpoints, and vice versa)
# ──────────────────────────────────────────────

PORTAL_COOKIE_NAME = "portal_token"


def create_portal_token(applicant) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "realm": "applicant",
        "sub": str(applicant.id),
        "email": applicant.email,
        "full_name": applicant.full_name,
        "iat": now,
        "exp": now + dt.timedelta(hours=settings.jwt_expires_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def set_portal_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=PORTAL_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


def clear_portal_cookie(response: Response) -> None:
    response.delete_cookie(key=PORTAL_COOKIE_NAME, path="/")


def get_current_applicant(request: Request) -> dict:
    """Return the authenticated applicant from the portal cookie, or raise 401."""
    token = request.cookies.get(PORTAL_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if payload.get("realm") != "applicant":
        raise HTTPException(status_code=401, detail="Unauthorized")

    return {
        "id": int(payload["sub"]),
        "email": payload.get("email", ""),
        "full_name": payload.get("full_name", ""),
    }


def require_role(minimum_role: str):
    """Dependency factory enforcing a minimum role, like PHP's require_role()."""

    def dependency(user: dict = Depends(get_current_user)) -> dict:
        user_level = ROLE_HIERARCHY.get(user["role"], 0)
        required = ROLE_HIERARCHY.get(minimum_role, 0)
        if user_level < required:
            raise HTTPException(
                status_code=403,
                detail="Access denied. You do not have the required permissions.",
            )
        return user

    return dependency
