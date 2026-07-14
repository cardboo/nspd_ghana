"""
NSPD Ghana — FastAPI application.

Replaces the PHP page controllers with a JSON REST API. The HTML pages are
now static files in frontend/ and talk to these endpoints with fetch().

Interactive API documentation is served at /api/docs (Swagger UI).
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from .routers import (
    account,
    applicants_admin,
    applications,
    audit,
    auth_routes,
    bootstrap,  # TEMPORARY: remove after the one-time data load
    cron,
    dashboard,
    documents,
    exports,
    portal,
    reports,
    users,
)

app = FastAPI(
    title="NSPD Ghana API",
    description="REST API for the NSPD Ghana Seafarer Training & Registration Portal.",
    version="2.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.include_router(auth_routes.router)
app.include_router(account.router)
app.include_router(dashboard.router)
app.include_router(applications.router)
app.include_router(documents.router)
app.include_router(reports.router)
app.include_router(exports.router)
app.include_router(users.router)
app.include_router(audit.router)
app.include_router(portal.router)
app.include_router(applicants_admin.router)
app.include_router(cron.router)
app.include_router(bootstrap.router)  # TEMPORARY: remove after the one-time data load


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    # Same friendly message as includes/db.php, without leaking details.
    return JSONResponse(
        status_code=500,
        content={"detail": "Database connection failed. Please check the configuration."},
    )


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/login.html")


# Local development convenience: `uvicorn backend.main:app` serves the static
# frontend from the same process. On Vercel the frontend is served by the
# static build and these requests never reach the function.
_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dir)), name="frontend")
