"""
SQLAlchemy engine and session management.

Replaces includes/db.php (PDO connection). NullPool is used because each
Vercel serverless invocation is short-lived: holding pooled connections
across invocations leaks them against cloud MySQL connection limits.
"""

import os
import tempfile

import certifi
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from .config import settings


def _ca_file() -> str:
    """Path to the CA bundle used to verify the database's TLS certificate.

    Managed hosts that sign with a private CA (e.g. Aiven) require their
    own CA cert, which is not in the public certifi bundle. Paste that PEM
    into DB_CA_CERT and we materialise it to a temp file (Vercel only allows
    writes under /tmp). With no custom CA, fall back to certifi, which works
    for hosts that use publicly-trusted certs (PlanetScale, RDS, …).
    """
    if settings.db_ca_cert.strip():
        ca_path = os.path.join(tempfile.gettempdir(), "nspd_db_ca.pem")
        with open(ca_path, "w", encoding="utf-8") as handle:
            handle.write(settings.db_ca_cert)
        return ca_path
    return certifi.where()


connect_args = {}
if settings.db_ssl:
    connect_args["ssl"] = {"ca": _ca_file()}

engine = create_engine(
    settings.database_url,
    poolclass=NullPool,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


def get_db():
    """FastAPI dependency yielding a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
