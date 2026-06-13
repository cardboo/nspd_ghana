"""
Application configuration.

All credentials and secrets come from environment variables (set in the
Vercel dashboard in production, or a local .env file for development).
Replaces the hardcoded constants from the PHP includes/db.php.
"""

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Loads a local .env file if present; a no-op on Vercel where env vars
# are injected directly.
load_dotenv()


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _build_database_url() -> str:
    """Build a SQLAlchemy URL from DB_* parts when DATABASE_URL is not set."""
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "3306")
    user = quote_plus(os.environ.get("DB_USER", "root"))
    password = quote_plus(os.environ.get("DB_PASS", ""))
    name = os.environ.get("DB_NAME", "nspd_db")
    auth = f"{user}:{password}" if password else user
    return f"mysql+pymysql://{auth}@{host}:{port}/{name}?charset=utf8mb4"


class Settings:
    def __init__(self) -> None:
        self.database_url: str = os.environ.get("DATABASE_URL") or _build_database_url()
        # Cloud MySQL providers (PlanetScale, Aiven, ...) require TLS.
        self.db_ssl: bool = _bool_env("DB_SSL", False)
        # PEM contents of a private CA cert (e.g. Aiven's project CA). When
        # empty, TLS verification falls back to the public certifi bundle.
        self.db_ca_cert: str = os.environ.get("DB_CA_CERT", "")

        self.jwt_secret: str = os.environ.get("JWT_SECRET", "dev-only-secret-change-me")
        self.jwt_algorithm: str = "HS256"
        self.jwt_expires_hours: int = int(os.environ.get("JWT_EXPIRES_HOURS", "8"))

        # COOKIE_SECURE=auto -> secure cookies whenever running on Vercel
        # (the VERCEL env var is always set there). Mirrors the PHP check of
        # $_SERVER['HTTPS'].
        cookie_secure = os.environ.get("COOKIE_SECURE", "auto").strip().lower()
        if cookie_secure == "auto":
            self.cookie_secure: bool = bool(os.environ.get("VERCEL"))
        else:
            self.cookie_secure = cookie_secure in ("1", "true", "yes", "on")

        # ── Login throttling ──
        self.lockout_max_attempts: int = int(os.environ.get("LOCKOUT_MAX_ATTEMPTS", "5"))
        self.lockout_window_minutes: int = int(os.environ.get("LOCKOUT_WINDOW_MINUTES", "15"))

        # ── Outbound email (applicant notifications) ──
        # When RESEND_API_KEY is not set, emails are recorded in the
        # notifications table with status 'skipped' instead of being sent.
        self.resend_api_key: str = os.environ.get("RESEND_API_KEY", "")
        self.email_from: str = os.environ.get("EMAIL_FROM", "NSPD Ghana <onboarding@resend.dev>")

        # ── Document storage ──
        # auto -> Vercel Blob when a token is configured, local disk otherwise.
        self.blob_token: str = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
        driver = os.environ.get("STORAGE_DRIVER", "auto").strip().lower()
        if driver == "auto":
            self.storage_driver: str = "vercel_blob" if self.blob_token else "local"
        else:
            self.storage_driver = driver
        default_uploads = Path(__file__).resolve().parent.parent / "uploads"
        self.uploads_dir: Path = Path(os.environ.get("UPLOADS_DIR", str(default_uploads)))
        self.max_upload_mb: int = int(os.environ.get("MAX_UPLOAD_MB", "10"))

        # ── Account recovery & scheduled cleanup ──
        self.reset_token_minutes: int = int(os.environ.get("RESET_TOKEN_MINUTES", "60"))
        # Portal invitation links live longer than self-requested resets
        self.invite_expires_days: int = int(os.environ.get("INVITE_EXPIRES_DAYS", "7"))
        self.unverified_retention_days: int = int(os.environ.get("UNVERIFIED_RETENTION_DAYS", "30"))

        # ── Certification expiry tracking ──
        # Watchlist horizon (staff page + dashboard card)
        self.expiry_warning_days: int = int(os.environ.get("EXPIRY_WARNING_DAYS", "90"))
        # Cron emails applicants when a certificate expires within this window
        self.expiry_alert_days: int = int(os.environ.get("EXPIRY_ALERT_DAYS", "30"))
        # Shared secret for Vercel Cron requests (Authorization: Bearer <secret>)
        self.cron_secret: str = os.environ.get("CRON_SECRET", "")
        self.is_vercel: bool = bool(os.environ.get("VERCEL"))


settings = Settings()
