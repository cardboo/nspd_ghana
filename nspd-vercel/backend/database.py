"""
SQLAlchemy engine and session management.

Replaces includes/db.php (PDO connection). NullPool is used because each
Vercel serverless invocation is short-lived: holding pooled connections
across invocations leaks them against cloud MySQL connection limits.
"""

import certifi
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from .config import settings

connect_args = {}
if settings.db_ssl:
    connect_args["ssl"] = {"ca": certifi.where()}

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
