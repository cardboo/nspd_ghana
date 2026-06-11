"""
SQLAlchemy models mirroring the MySQL schema exactly
(see migrations/001_init.sql and 002_features.sql). Column names, types,
keys, and constraints are preserved from the PHP version's database, plus
the v2 feature tables (workflow, comments, documents, audit, throttling,
notifications).
"""

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)

from .database import Base

APPLICATION_STATUSES = ("Pending", "Under Review", "Approved", "Rejected")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(
        Enum("Administrator", "Reviewer", "Viewer", name="user_role"),
        nullable=False,
        default="Viewer",
    )
    email = Column(String(150), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    must_change_password = Column(Boolean, nullable=False, default=False)
    reset_token = Column(String(64), nullable=True)
    reset_token_expires = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    last_login = Column(TIMESTAMP, nullable=True)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submitted_at = Column(DateTime, nullable=False)
    surname = Column(String(100), nullable=False)
    first_name = Column(String(100), nullable=False)
    other_names = Column(String(100), nullable=True)
    short_courses_rmu = Column(Enum("Yes", "No", name="yes_no_rmu"), nullable=False)
    familiarisation_isps_gma = Column(Enum("Yes", "No", name="yes_no_isps"), nullable=False)
    position_rank = Column(String(100), nullable=False)
    telephone = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False)
    attachment = Column(Text, nullable=True)
    sea_experience = Column(Text, nullable=True)
    total_sea_experience_years = Column(Numeric(4, 1), nullable=True)
    last_ship_type = Column(String(150), nullable=True)
    medicals = Column(Text, nullable=True)
    status = Column(
        Enum(*APPLICATION_STATUSES, name="application_status"),
        nullable=False,
        default="Pending",
    )
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(TIMESTAMP, nullable=True)
    applicant_id = Column(Integer, ForeignKey("applicants.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())


class Applicant(Base):
    """Portal account for a seafarer — a separate auth realm from staff Users."""

    __tablename__ = "applicants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(150), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    email_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    verify_token = Column(String(64), nullable=True)
    reset_token = Column(String(64), nullable=True)
    reset_token_expires = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    last_login = Column(TIMESTAMP, nullable=True)


class ApplicationComment(Base):
    __tablename__ = "application_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Denormalised so the review trail survives user deactivation/deletion
    username = Column(String(50), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    doc_type = Column(String(50), nullable=False, default="Other")
    original_name = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_driver = Column(String(20), nullable=False)
    storage_key = Column(String(500), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(TIMESTAMP, server_default=func.current_timestamp())


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    entity = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    details = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False)
    ip_address = Column(String(45), nullable=True)
    success = Column(Boolean, nullable=False, default=False)
    attempted_at = Column(TIMESTAMP, server_default=func.current_timestamp())


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, nullable=True)
    recipient = Column(String(150), nullable=False)
    subject = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    error = Column(String(300), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
