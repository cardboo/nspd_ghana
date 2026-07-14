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

import socket

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
    """Layered DB connectivity diagnostic: DNS -> raw TCP -> MySQL/TLS.
    Each stage reports independently so we can see exactly where it breaks."""
    _authorize(request)
    url = make_url(settings.database_url)
    host, port = url.host, (url.port or 3306)
    result = {
        "config": {
            "host": host, "port": port, "user": url.username,
            "database": url.database, "db_ssl": settings.db_ssl,
            "db_ssl_verify": settings.db_ssl_verify,
        },
        "stages": {},
    }

    # 1) DNS resolution — what IP(s) does the host resolve to on Vercel?
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        result["stages"]["dns"] = sorted({ai[4][0] for ai in infos})
    except Exception as exc:  # noqa: BLE001
        result["stages"]["dns"] = f"ERR {type(exc).__name__}: {exc}"
        return result

    # 2) Raw TCP connect — can Vercel open a socket to the DB port at all?
    try:
        s = socket.create_connection((host, port), timeout=8)
        s.close()
        result["stages"]["tcp"] = "ok"
    except Exception as exc:  # noqa: BLE001
        result["stages"]["tcp"] = f"ERR {type(exc).__name__}: {exc}"

    # 3) Full MySQL + TLS handshake
    try:
        conn = _raw_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT VERSION()")
                result["stages"]["mysql"] = {"ok": True, "version": cur.fetchone()[0]}
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        result["stages"]["mysql"] = f"ERR {type(exc).__name__}: {exc}"

    result["ok"] = result["stages"].get("mysql", {}) == {"ok": True} or (
        isinstance(result["stages"].get("mysql"), dict) and result["stages"]["mysql"].get("ok")
    )
    return result


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
