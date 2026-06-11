"""Pydantic request/response schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

ROLES = Literal["Administrator", "Reviewer", "Viewer"]
STATUSES = Literal["Pending", "Under Review", "Approved", "Rejected"]

# Lightweight email shape check (full validation happens at the mail provider)
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=255)


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    email: str
    must_change_password: bool = False


class StatusUpdateRequest(BaseModel):
    status: STATUSES


class CommentRequest(BaseModel):
    comment: str = Field(..., min_length=1, max_length=2000)


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
    full_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=150, pattern=EMAIL_PATTERN)
    role: ROLES = "Viewer"
    temp_password: str = Field(..., min_length=8, max_length=255)


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=150, pattern=EMAIL_PATTERN)
    role: Optional[ROLES] = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    temp_password: str = Field(..., min_length=8, max_length=255)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=255)
    new_password: str = Field(..., min_length=8, max_length=255)


# ──────────────────────────────────────────────
# Applicant portal
# ──────────────────────────────────────────────

YES_NO = Literal["Yes", "No"]


class PortalRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=150)
    email: str = Field(..., max_length=150, pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=8, max_length=255)


class PortalLoginRequest(BaseModel):
    email: str = Field(..., max_length=150, pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=1, max_length=255)


class ApplicationForm(BaseModel):
    """Fields a seafarer fills in — mirrors the applications table columns.

    The application's email is always the account email (set server-side),
    so it is not part of this schema.
    """

    surname: str = Field(..., min_length=1, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    other_names: Optional[str] = Field(None, max_length=100)
    telephone: str = Field(..., min_length=3, max_length=100)
    position_rank: str = Field(..., min_length=1, max_length=100)
    short_courses_rmu: YES_NO
    familiarisation_isps_gma: YES_NO
    attachment: YES_NO = "No"
    sea_experience: YES_NO = "No"
    medicals: YES_NO = "No"
    total_sea_experience_years: Optional[float] = Field(None, ge=0, le=999.9)
    last_ship_type: Optional[str] = Field(None, max_length=150)
