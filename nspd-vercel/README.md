# NSPD Ghana — Vercel Edition (FastAPI + Static Frontend)

A full conversion of the PHP/MySQL **National Seafarer Placement Database (NSPD)** dashboard into a Vercel-deployable application:

| Layer    | Before (PHP version)         | After (this project)                          |
|----------|------------------------------|-----------------------------------------------|
| Backend  | PHP 8 pages + PDO            | **Python FastAPI** serverless function        |
| Auth     | PHP sessions + CSRF tokens   | **JWT** in httpOnly SameSite=Strict cookie    |
| Database | MySQL via PDO                | MySQL via **SQLAlchemy ORM** (PyMySQL driver) |
| Frontend | Server-rendered PHP/HTML     | Same HTML/CSS, data loaded with `fetch()`     |
| PDF      | TCPDF (Composer)             | **fpdf2** (pure Python, serverless-friendly)  |
| CSV      | `fputcsv` + BOM              | Python `csv` + BOM (identical output)         |

Every feature is preserved: login/logout, role-based access control (Administrator > Reviewer > Viewer), dashboard statistics, searchable/paginated submissions, submission detail, the five analytics charts with filters, CSV export, and per-submission PDF export.

## v2 Features (beyond the PHP version)

| Feature | Description |
|---------|-------------|
| **Review workflow** | Applications carry a status (Pending / Under Review / Approved / Rejected); Reviewers approve/reject from the detail page with reviewer + timestamp recorded |
| **Applicant notifications** | Status changes email the applicant via Resend; every attempt is logged in the `notifications` table (recorded as `skipped` when no API key is set) |
| **Reviewer comments** | Internal notes thread on each application (Reviewer+ write, all roles read) |
| **Document uploads** | Certificates/medical reports/photos per application — local disk in dev, Vercel Blob in production; PDF/JPG/PNG/DOC up to 10 MB |
| **User management** | Admin page to create users, change roles, deactivate accounts, and reset passwords; new/reset accounts must change their temp password at first login (enforced server-side) |
| **My Account page** | Self-service profile view and password change |
| **Audit log** | Admin page recording logins, exports (PII), status changes, comments, documents, and user administration, with action/user filters |
| **Login throttling** | DB-backed lockout: 5 failed attempts per username (20 per IP) in 15 minutes |
| **Data Quality page** | Duplicate-submission report grouped by shared email / telephone (Reviewer+) — clean these before applying the unique index from the original migrate_v2.sql |
| **Report date range** | From/To date filters on all five analytics charts |
| **Sortable columns** | Submissions table sorts by name, rank, email, status, or date |
| **Applicant portal** | Seafarers self-register (`portal-register.html`), verify their email, submit **one application per account**, upload their own documents, track status, edit while Pending, and resubmit after Rejection. Locked the moment review starts. Applicant auth is a fully separate realm (own table, own cookie, own JWT realm) — applicant sessions cannot touch staff endpoints and vice versa |
| **Password recovery** | Self-service forgot-password for both staff and applicants: single-use emailed tokens (60 min expiry), no account enumeration, per-IP request throttling |
| **Applicant administration** | Admins see all seafarer accounts on the Users page: verification state, linked application, deactivate/reactivate, resend verification emails |
| **Scheduled cleanup** | Vercel Cron job deletes never-verified accounts after 30 days (`/api/cron/cleanup-unverified`, protected by `CRON_SECRET`) |
| **Registration throttling** | Public endpoints (register, forgot-password, resend-verification) are rate-limited per IP |
| **Certification tracking** | Certificates and medicals carry real issue/expiry dates (the old registry only had Yes/No flags); staff and applicants manage them on the detail/portal pages |
| **Expiry Watch** | Staff page listing certificates expired or expiring within 30–365 days, plus a dashboard card; a weekly cron emails applicants (one mail per seafarer, repeated at most every 14 days) |
| **Ghana Card number** | Required on new portal applications, normalised and protected by a UNIQUE index — duplicate submissions become structurally impossible going forward; searchable and included in CSV/PDF exports |
| **Status timeline** | Submission and review history on the staff detail page (with reviewer names) and the applicant portal (anonymised), sourced from the audit trail |
| **Reference search** | The submissions search box also matches `#575`-style reference numbers and Ghana Card numbers |

## Project Structure

```
nspd-vercel/
├── api/
│   └── index.py                 # Vercel serverless entrypoint (exposes the ASGI app)
├── backend/
│   ├── main.py                  # FastAPI app, routers, error handling
│   ├── config.py                # Environment-based configuration
│   ├── database.py              # SQLAlchemy engine + session (serverless-safe)
│   ├── models.py                # User & Application ORM models
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── auth.py                  # JWT, bcrypt, role hierarchy dependencies
│   ├── routers/
│   │   ├── auth_routes.py       # /api/auth/*
│   │   ├── dashboard.py         # /api/dashboard/stats
│   │   ├── applications.py      # /api/applications*
│   │   ├── reports.py           # /api/reports/*
│   │   └── exports.py           # /api/exports/* (Reviewer+)
│   └── services/
│       ├── application_service.py
│       ├── report_service.py
│       └── export_service.py    # CSV + PDF generation
├── frontend/
│   ├── login.html / dashboard.html / submissions.html
│   ├── view-submission.html / reports.html
│   ├── css/style.css            # unchanged from the PHP version
│   └── js/                      # page modules + shared helpers
├── migrations/
│   └── 001_init.sql             # schema (users + applications)
├── vercel.json                  # routing: /api/* -> function, rest -> static
├── requirements.txt
├── .env.example
└── README.md
```

## API Reference

Interactive Swagger documentation is served at **`/api/docs`** once running.

| Method | Endpoint                    | Replaces (PHP)              | Auth       | Description |
|--------|-----------------------------|-----------------------------|------------|-------------|
| POST   | `/api/auth/login`           | `login.php` (POST)          | —          | Body `{username, password}`; sets the JWT cookie, returns the user |
| POST   | `/api/auth/logout`          | `logout.php`                | —          | Clears the auth cookie |
| GET    | `/api/auth/me`              | session check               | Cookie     | Returns the current user (401 if not logged in) |
| GET    | `/api/dashboard/stats`      | `dashboard.php` queries     | Cookie     | Totals, average experience, top rank, 24h count, 5 recent rows |
| GET    | `/api/applications`         | `submissions.php`           | Cookie     | Query `page`, `search`, `rank`; paginated (10/page) |
| GET    | `/api/applications/ranks`   | rank dropdown query         | Cookie     | Distinct ranks for the filter dropdown |
| GET    | `/api/applications/{id}`    | `view-submission.php`       | Cookie     | Full submission detail (404 if missing) |
| GET    | `/api/reports/data`         | `api/reports-data.php`      | Cookie     | Query `rank`, `course`, `medical`, `ship_type`, `date_from`, `date_to` |
| GET    | `/api/reports/filters`      | dropdowns in `reports.php`  | Cookie     | Distinct ranks + ship types |
| GET    | `/api/exports/csv`          | `api/export-all-csv.php`    | Reviewer+  | CSV download honouring `search`/`rank`/`status` filters (audited) |
| GET    | `/api/exports/pdf/{id}`     | `api/export-pdf.php`        | Reviewer+  | PDF download for one submission (audited) |

### v2 endpoints

| Method | Endpoint                              | Auth       | Description |
|--------|---------------------------------------|------------|-------------|
| PUT    | `/api/applications/{id}/status`       | Reviewer+  | Body `{status}`; records reviewer + time, emails the applicant |
| GET    | `/api/applications/{id}/comments`     | Cookie     | List internal review comments |
| POST   | `/api/applications/{id}/comments`     | Reviewer+  | Body `{comment}` (max 2000 chars) |
| DELETE | `/api/applications/comments/{id}`     | author/Admin | Delete a comment |
| GET    | `/api/applications/{id}/documents`    | Cookie     | List uploaded documents |
| POST   | `/api/applications/{id}/documents`    | Reviewer+  | Multipart `file` + `doc_type`; PDF/JPG/PNG/DOC, max 10 MB |
| GET    | `/api/documents/{id}/download`        | Cookie     | Download (local) or redirect (Vercel Blob) |
| DELETE | `/api/documents/{id}`                 | Reviewer+  | Delete file + metadata |
| GET    | `/api/users`                          | Admin      | List users |
| POST   | `/api/users`                          | Admin      | Create user with temp password (forced change at first login) |
| PUT    | `/api/users/{id}`                     | Admin      | Update name/email/role/active (cannot demote/deactivate self) |
| POST   | `/api/users/{id}/reset-password`      | Admin      | Set temp password (forced change at next login) |
| GET    | `/api/account/profile`                | Cookie     | Own profile (fresh from DB, includes last login) |
| POST   | `/api/account/password`               | Cookie     | Change own password; clears the forced-change flag |
| GET    | `/api/audit`                          | Admin      | Paginated audit log; `page`, `action`, `username` filters |
| GET    | `/api/reports/duplicates`             | Reviewer+  | Submissions sharing an email or telephone |

The submissions list also accepts `status`, `sort` (`name|rank|email|status|date`) and `dir` (`asc|desc`).

### Applicant portal endpoints (separate `portal_token` cookie realm)

| Method | Endpoint                        | Auth      | Description |
|--------|---------------------------------|-----------|-------------|
| POST   | `/api/portal/register`          | —         | Create a seafarer account; sends a verification email (auto-verifies in dev without an email key) |
| GET    | `/api/portal/verify?token=`     | —         | Confirm email address |
| POST   | `/api/portal/login`             | —         | Sign in (throttled like staff logins; requires verified email) |
| POST   | `/api/portal/logout`            | —         | Clear the portal session |
| GET    | `/api/portal/me`                | Portal    | Account + application status summary |
| GET    | `/api/portal/ranks`             | —         | Rank options for the form |
| GET    | `/api/portal/application`       | Portal    | Own application |
| POST   | `/api/portal/application`       | Portal    | Submit (one per account — 409 otherwise); sends a confirmation email with the reference number |
| PUT    | `/api/portal/application`       | Portal    | Edit while Pending; editing a Rejected application resubmits it (status returns to Pending) |
| GET    | `/api/portal/documents`         | Portal    | Own documents |
| POST   | `/api/portal/documents`         | Portal    | Upload to own application (while editable; max 10 files) |
| DELETE | `/api/portal/documents/{id}`    | Portal    | Delete own self-uploaded document (staff-added files are protected) |

Portal pages: `portal-register.html`, `portal-login.html`, `verify.html`, `portal.html` (My Application). The staff login page links to the portal and vice versa.

### Account recovery & administration endpoints

| Method | Endpoint                                     | Auth   | Description |
|--------|----------------------------------------------|--------|-------------|
| POST   | `/api/auth/forgot-password`                  | —      | Staff reset link by username or email (generic response, IP-throttled) |
| POST   | `/api/auth/reset-password`                   | —      | Complete a staff reset with `{token, new_password}` |
| POST   | `/api/portal/forgot-password`                | —      | Applicant reset link by email |
| POST   | `/api/portal/reset-password`                 | —      | Complete an applicant reset (also marks the email verified) |
| POST   | `/api/portal/resend-verification`            | —      | Re-send the verification link (generic response, IP-throttled) |
| GET    | `/api/applicants`                            | Admin  | Paginated seafarer accounts with `search` |
| PUT    | `/api/applicants/{id}`                       | Admin  | Activate / deactivate an applicant account |
| POST   | `/api/applicants/{id}/resend-verification`   | Admin  | Re-send verification on behalf of an applicant |
| GET    | `/api/cron/cleanup-unverified`               | Cron   | Delete unverified accounts older than the retention window (Bearer `CRON_SECRET`) |

Recovery pages: `forgot-password.html` and `reset-password.html`, realm-selected by `?for=staff` or `?for=portal`.

### Certification & compliance endpoints

| Method | Endpoint                                        | Auth      | Description |
|--------|--------------------------------------------------|-----------|-------------|
| GET    | `/api/applications/{id}/certifications`          | Cookie    | Certificates with computed expiry status |
| POST   | `/api/applications/{id}/certifications`          | Reviewer+ | Add a record `{cert_type, title, issued_on?, expires_on?, issuer?}` |
| DELETE | `/api/applications/certifications/{id}`          | Reviewer+ | Remove a record |
| GET    | `/api/applications/{id}/history`                 | Cookie    | Submission/review timeline (audit-sourced) |
| GET    | `/api/portal/certifications`                     | Portal    | Own records |
| POST   | `/api/portal/certifications`                     | Portal    | Add while the application is editable |
| DELETE | `/api/portal/certifications/{id}`                | Portal    | Remove own (self-added) record while editable |
| GET    | `/api/portal/application/history`                | Portal    | Own timeline (staff names hidden) |
| GET    | `/api/reports/expiring?days=N`                   | Reviewer+ | Expiry watchlist (default `EXPIRY_WARNING_DAYS`) |
| GET    | `/api/cron/expiry-alerts`                        | Cron      | Weekly applicant expiry reminder emails |

Expiry statuses: `expired`, `expiring_soon` (within `EXPIRY_WARNING_DAYS`), `valid`, `no_expiry`.

Errors are JSON: `{"detail": "..."}` with proper status codes (400, 401, 403, 404, 409, 422, 429, 500).

## Authentication Notes

- Passwords are verified with **bcrypt**. Existing PHP `$2y$` hashes keep working (the backend normalises the prefix — `$2y$` and `$2b$` are the same algorithm), so **no password resets are needed** when migrating the users table.
- On login the API issues a **JWT** (default 8h lifetime, `JWT_EXPIRES_HOURS`) stored in an **httpOnly, SameSite=Strict** cookie — not readable by JavaScript, not sent on cross-site requests.
- The PHP CSRF token is replaced by that SameSite=Strict cookie plus JSON-only request bodies, which together block cross-site form submissions. Refresh tokens were deliberately omitted: for an internal dashboard a short-lived access token with re-login matches the old session behaviour.
- Role hierarchy is unchanged: `Administrator (3) > Reviewer (2) > Viewer (1)`; exports require Reviewer or above (HTTP 403 otherwise).

## Database Setup (cloud MySQL)

The app keeps MySQL (no PostgreSQL conversion needed). Any MySQL 8-compatible host works — e.g. **Railway**, **PlanetScale**, **Aiven**, or AWS RDS.

1. Create a MySQL database (e.g. `nspd_db`).
2. Run [migrations/001_init.sql](migrations/001_init.sql) against it (creates `users` + `applications`; the only schema change from the PHP version is MyISAM → InnoDB, which cloud providers require).
3. Import your existing data dump (`mysqldump nspd_db` from the old server, or the project's `nspd_db (2).sql`).
4. Run [migrations/002_features.sql](migrations/002_features.sql) (workflow columns, user admin columns, comments/documents/audit/throttling/notifications tables). Run it **after** importing data — the import recreates the `applications` table.
5. Run [migrations/003_portal.sql](migrations/003_portal.sql) (applicant accounts + application ownership link).
6. Note the connection details for the environment variables below.

> The original `migrate_v2.sql` unique index on `(email, telephone)` is intentionally not applied by 002 — the existing data contains duplicates. Clean them via the **Data Quality** page first, then apply the index manually.

> PlanetScale/Aiven require TLS — set `DB_SSL=true`.

## Environment Variables

Copy `.env.example` to `.env` locally; in production set the same variables in **Vercel → Project Settings → Environment Variables**. No credentials are hardcoded anywhere.

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | Full SQLAlchemy URL (preferred) | `mysql+pymysql://user:pass@host:3306/nspd_db?charset=utf8mb4` |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASS` / `DB_NAME` | Used when `DATABASE_URL` is unset | — |
| `DB_SSL` | `true` for providers requiring TLS | `true` |
| `JWT_SECRET` | Token signing key — **required in production** | output of `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_EXPIRES_HOURS` | Access-token lifetime | `8` |
| `COOKIE_SECURE` | `auto` (secure on Vercel) / `true` / `false` | `auto` |
| `LOCKOUT_MAX_ATTEMPTS` | Failed logins per username before lockout (per-IP limit is 4x) | `5` |
| `LOCKOUT_WINDOW_MINUTES` | Lockout window | `15` |
| `RESEND_API_KEY` | [Resend](https://resend.com) key for applicant emails; unset = emails logged as `skipped` | — |
| `EMAIL_FROM` | From address for notifications (must be a verified Resend domain in production) | `NSPD Ghana <noreply@yourdomain>` |
| `STORAGE_DRIVER` | `auto` / `local` / `vercel_blob` | `auto` |
| `BLOB_READ_WRITE_TOKEN` | Injected by Vercel when you attach a Blob store — **required for uploads on Vercel** (no persistent disk on serverless) | — |
| `MAX_UPLOAD_MB` | Document upload size limit | `10` |
| `RESET_TOKEN_MINUTES` | Password-reset link validity | `60` |
| `UNVERIFIED_RETENTION_DAYS` | Never-verified accounts are deleted after this many days | `30` |
| `CRON_SECRET` | Shared secret for Vercel Cron — set it in production so `/api/cron/*` requires `Authorization: Bearer <secret>` | random string |
| `EXPIRY_WARNING_DAYS` | Watchlist/dashboard horizon for "expiring soon" | `90` |
| `EXPIRY_ALERT_DAYS` | Cron emails applicants when a certificate expires within this window | `30` |

## Run Locally

```bash
cd nspd-vercel
python -m venv .venv
.venv\Scripts\activate          # Windows  (source .venv/bin/activate on Unix)
pip install -r requirements.txt
copy .env.example .env           # then edit credentials
uvicorn backend.main:app --reload --port 8000
```

Open <http://localhost:8000> — the FastAPI process also serves the static frontend locally, so the whole app runs from one command. Default account: `admin` / `admin123` (change it immediately).

## Deploy to Vercel

1. Push this project to a Git repository (GitHub/GitLab/Bitbucket).
2. In Vercel: **Add New → Project → Import** the repository.
   - If `nspd-vercel/` is a subfolder of your repo, set **Root Directory** to `nspd-vercel`.
   - Framework preset: **Other**. No build command or output directory needed — `vercel.json` defines everything.
3. Add the environment variables (`DATABASE_URL` or `DB_*`, `DB_SSL`, `JWT_SECRET`) for the Production environment.
4. Deploy. Vercel builds `api/index.py` with the Python runtime (installing `requirements.txt`) and serves `frontend/` as static files; `vercel.json` routes `/api/*` to the function and everything else to the frontend.
5. Visit the deployment URL — it lands on the login page.

CLI alternative:

```bash
npm i -g vercel
cd nspd-vercel
vercel            # preview deployment
vercel --prod     # production
```

### How requests flow in production

```
Browser ──/dashboard.html──────────▶ Vercel static (frontend/)
        ──/api/applications?page=2─▶ Vercel Python fn (api/index.py → FastAPI)
                                          │ SQLAlchemy / PyMySQL (TLS)
                                          ▼
                                    Cloud MySQL (Railway / PlanetScale / …)
```

## Conversion Notes (what changed and why)

- **Server-rendered pages → static pages + fetch().** Each PHP page's queries became a JSON endpoint; the HTML/CSS and rendered output are unchanged. The shared `includes/sidebar.php` and `includes/header.php` became `js/layout.js`, which also enforces the login redirect (`require_auth()` equivalent) via `/api/auth/me`.
- **Sessions → JWT cookie.** Serverless functions have no shared session storage; a signed cookie carries the same fields the PHP session held (`user_id`, `username`, `full_name`, `role`, `email`).
- **TCPDF → fpdf2.** TCPDF is PHP-only. fpdf2 is pure Python (works within Vercel's runtime) and reproduces the report layout: navy banner, blue section bars, bordered label/value rows, green/red Yes/No badges, and the same footer text.
- **Query semantics preserved**, including: search across surname/first name/email with `LIKE`, the ±2 page pagination window, the 12-month trends limit, certification/medical `CASE` aggregations, `NOW() - INTERVAL 1 DAY` evaluated by MySQL, and the CSV column order/date formats. The trends query now groups by both month expressions so it also runs under MySQL's `ONLY_FULL_GROUP_BY` mode (default on cloud MySQL).
- **MyISAM → InnoDB** for `applications` (cloud MySQL requirement; no behavioural impact).

## Default Roles

| Role          | Permissions                                 |
|---------------|---------------------------------------------|
| Administrator | Full access — view, export                  |
| Reviewer      | View all submissions, export CSV/PDF        |
| Viewer        | View dashboard and submissions (no exports) |
