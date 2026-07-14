"""
TEMPORARY one-time data bootstrap endpoints.

Purpose: load the initial SQL dump into the managed database when the
operator's own network cannot reach the database port directly (e.g. a
corporate firewall that blocks outbound MySQL ports). The operator's
machine can still reach Vercel over HTTPS/443, and Vercel reaches the
database, so the dump travels:

    operator -> Vercel (TLS/443) -> database (TLS)

Security: guarded by the CRON_SECRET bearer token. These routes touch the
database directly and MUST be removed from main.py once the one-time load
is complete (see the deployment runbook).
"""

import pymysql
from fastapi import APIRouter, HTTPException, Request
from pymysql.constants import CLIENT
from sqlalchemy.engine import make_url

from ..config import settings
from ..database import _ssl_arg

router = APIRouter(prefix="/api/bootstrap", tags=["Bootstrap (temporary)"])


def _authorize(request: Request) -> None:
    if not settings.cron_secret:
        raise HTTPException(status_code=503, detail="CRON_SECRET is not configured")
    if request.headers.get("authorization", "") != f"Bearer {settings.cron_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _raw_connection() -> "pymysql.connections.Connection":
    """A dedicated multi-statement connection built from the app's DB settings."""
    url = make_url(settings.database_url)
    return pymysql.connect(
        host=url.host,
        port=url.port or 3306,
        user=url.username,
        password=url.password,
        database=url.database,
        charset="utf8mb4",
        ssl=_ssl_arg(),
        client_flag=CLIENT.MULTI_STATEMENTS,
        connect_timeout=10,
        read_timeout=45,
        write_timeout=45,
    )


@router.get("/ping")
def ping(request: Request):
    """Diagnose the DB connection: reports success + server version, or the
    exact driver error (so connection problems are visible, not a blank 500)."""
    _authorize(request)
    url = make_url(settings.database_url)
    info = {
        "host": url.host,
        "port": url.port,
        "user": url.username,
        "database": url.database,
        "db_ssl": settings.db_ssl,
        "db_ssl_verify": settings.db_ssl_verify,
    }
    try:
        conn = _raw_connection()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "stage": "connect", "error": f"{type(exc).__name__}: {exc}", "config": info}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            version = cur.fetchone()[0]
        return {"ok": True, "server_version": version, "config": info}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "stage": "query", "error": f"{type(exc).__name__}: {exc}", "config": info}
    finally:
        conn.close()


@router.post("/load-sql")
async def load_sql(request: Request):
    """Execute an uploaded SQL dump (idempotent when the dump uses DROP TABLE)."""
    _authorize(request)

    # utf-8-sig transparently strips a leading BOM if present
    sql = (await request.body()).decode("utf-8-sig")
    if not sql.strip():
        raise HTTPException(status_code=400, detail="Empty SQL body")

    try:
        conn = _raw_connection()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"DB connect failed: {type(exc).__name__}: {exc}")

    try:
        result_sets = 0
        with conn.cursor() as cur:
            # args=None -> pymysql sends the text verbatim (no % interpolation),
            # and MULTI_STATEMENTS lets the server run every statement in the dump.
            cur.execute(sql)
            result_sets += 1
            while cur.nextset():
                result_sets += 1
        conn.commit()

        counts = {}
        with conn.cursor() as cur:
            for table in ("applications", "users", "applicants"):
                try:
                    cur.execute(f"SELECT COUNT(*) FROM `{table}`")
                    counts[table] = cur.fetchone()[0]
                except Exception:  # noqa: BLE001
                    counts[table] = None
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Load failed: {type(exc).__name__}: {exc}")
    finally:
        conn.close()

    return {"ok": True, "result_sets": result_sets, "row_counts": counts}
