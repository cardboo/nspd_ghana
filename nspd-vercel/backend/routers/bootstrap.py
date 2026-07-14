"""
TEMPORARY one-time data bootstrap endpoint.

Purpose: load the initial SQL dump into the managed database when the
operator's own network cannot reach the database port directly (e.g. a
corporate firewall that blocks outbound MySQL ports). The operator's
machine can still reach Vercel over HTTPS/443, and Vercel reaches the
database, so the dump travels:

    operator -> Vercel (TLS/443) -> database (TLS)

Security: guarded by the CRON_SECRET bearer token. This router executes
arbitrary SQL and MUST be removed from main.py once the one-time load is
done (see the deployment runbook).
"""

import pymysql
from fastapi import APIRouter, HTTPException, Request
from pymysql.constants import CLIENT
from sqlalchemy.engine import make_url

from ..config import settings
from ..database import _ca_file

router = APIRouter(prefix="/api/bootstrap", tags=["Bootstrap (temporary)"])


def _authorize(request: Request) -> None:
    if not settings.cron_secret:
        raise HTTPException(status_code=503, detail="CRON_SECRET is not configured")
    if request.headers.get("authorization", "") != f"Bearer {settings.cron_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _raw_connection() -> pymysql.connections.Connection:
    """A dedicated multi-statement connection built from the app's DB settings."""
    url = make_url(settings.database_url)
    ssl_arg = {"ca": _ca_file()} if settings.db_ssl else None
    return pymysql.connect(
        host=url.host,
        port=url.port or 3306,
        user=url.username,
        password=url.password,
        database=url.database,
        charset="utf8mb4",
        ssl=ssl_arg,
        client_flag=CLIENT.MULTI_STATEMENTS,
    )


@router.post("/load-sql")
async def load_sql(request: Request):
    """Execute an uploaded SQL dump (idempotent when the dump uses DROP TABLE)."""
    _authorize(request)

    # utf-8-sig transparently strips a leading BOM if present
    sql = (await request.body()).decode("utf-8-sig")
    if not sql.strip():
        raise HTTPException(status_code=400, detail="Empty SQL body")

    conn = _raw_connection()
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
                except Exception:  # noqa: BLE001 - table may not exist if load failed
                    counts[table] = None
    except Exception as exc:  # noqa: BLE001 - surface the DB error to the caller
        raise HTTPException(status_code=500, detail=f"Load failed: {exc}")
    finally:
        conn.close()

    return {"ok": True, "result_sets": result_sets, "row_counts": counts}
