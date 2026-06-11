"""
Application queries: dashboard stats, list/search/pagination/sorting,
detail, review workflow, comments, and duplicate detection.

The original queries from dashboard.php, submissions.php and
view-submission.php are preserved; v2 adds status workflow, sortable
columns, reviewer comments, and data-quality reporting.
"""

import math

from fastapi import HTTPException
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from ..models import Application, ApplicationComment, AuditLog, User
from . import certification_service, voyage_service

PER_PAGE = 10

# Whitelisted sortable columns -> ORDER BY expressions
SORTABLE_COLUMNS = {
    "name": (Application.surname, Application.first_name),
    "rank": (Application.position_rank,),
    "email": (Application.email,),
    "status": (Application.status,),
    "date": (Application.submitted_at,),
}


def _iso(value):
    return value.isoformat() if value else None


def _years(value):
    return float(value) if value is not None else None


def serialize_summary(app: Application) -> dict:
    return {
        "id": app.id,
        "surname": app.surname,
        "first_name": app.first_name,
        "position_rank": app.position_rank,
        "email": app.email,
        "telephone": app.telephone,
        "short_courses_rmu": app.short_courses_rmu,
        "medicals": app.medicals,
        "status": app.status,
        "total_sea_experience_years": _years(app.total_sea_experience_years),
        "submitted_at": _iso(app.submitted_at),
    }


def serialize_detail(app: Application, reviewer_name: str = None) -> dict:
    return {
        "id": app.id,
        "surname": app.surname,
        "first_name": app.first_name,
        "other_names": app.other_names,
        "telephone": app.telephone,
        "ghana_card_number": app.ghana_card_number,
        "email": app.email,
        "position_rank": app.position_rank,
        "short_courses_rmu": app.short_courses_rmu,
        "familiarisation_isps_gma": app.familiarisation_isps_gma,
        "attachment": app.attachment,
        "medicals": app.medicals,
        "sea_experience": app.sea_experience,
        "total_sea_experience_years": _years(app.total_sea_experience_years),
        "last_ship_type": app.last_ship_type,
        "status": app.status,
        "reviewed_by": app.reviewed_by,
        "reviewer_name": reviewer_name,
        "reviewed_at": _iso(app.reviewed_at),
        "submitted_at": _iso(app.submitted_at),
    }


def get_reviewer_name(db: Session, app: Application):
    if not app.reviewed_by:
        return None
    reviewer = db.get(User, app.reviewed_by)
    return reviewer.full_name if reviewer else None


def build_search_filters(search: str, rank: str, status: str = "") -> list:
    """WHERE clause from submissions.php / export-all-csv.php, plus status,
    Ghana Card, and reference-number matching."""
    filters = []
    if search:
        like = f"%{search}%"
        conditions = [
            Application.surname.like(like),
            Application.first_name.like(like),
            Application.email.like(like),
            Application.ghana_card_number.like(like),
        ]
        # "#575" or "575" also matches the application reference number
        reference = search.lstrip("#").strip()
        if reference.isdigit():
            conditions.append(Application.id == int(reference))
        filters.append(or_(*conditions))
    if rank:
        filters.append(Application.position_rank == rank)
    if status:
        filters.append(Application.status == status)
    return filters


def get_dashboard_stats(db: Session) -> dict:
    """Converted from the queries at the top of dashboard.php, plus the pending queue."""
    total = db.query(func.count(Application.id)).scalar() or 0

    avg_exp = db.query(func.avg(Application.total_sea_experience_years)).scalar()
    avg_exp = float(avg_exp) if avg_exp is not None else 0.0

    most_common_rank = (
        db.query(Application.position_rank)
        .group_by(Application.position_rank)
        .order_by(func.count().desc())
        .limit(1)
        .scalar()
    )

    # NOW() is evaluated by MySQL, exactly like the original query.
    recent_24h = (
        db.query(func.count(Application.id))
        .filter(Application.submitted_at >= text("NOW() - INTERVAL 1 DAY"))
        .scalar()
        or 0
    )

    status_rows = (
        db.query(Application.status, func.count().label("count"))
        .group_by(Application.status)
        .all()
    )
    status_counts = {row.status: int(row.count) for row in status_rows}

    recent = (
        db.query(Application)
        .order_by(Application.submitted_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total_submissions": int(total),
        "avg_experience": avg_exp,
        "most_common_rank": most_common_rank,
        "recent_24h": int(recent_24h),
        "pending_review": status_counts.get("Pending", 0) + status_counts.get("Under Review", 0),
        "expiring_certs": int(certification_service.count_expiring(db)),
        "onboard_count": int(voyage_service.count_onboard(db)),
        "status_counts": status_counts,
        "recent_submissions": [serialize_summary(a) for a in recent],
    }


def list_applications(
    db: Session,
    page: int,
    search: str,
    rank: str,
    status: str = "",
    sort: str = "date",
    direction: str = "desc",
) -> dict:
    """Pagination/filter logic from submissions.php, plus status filter and sorting."""
    filters = build_search_filters(search, rank, status)

    total = db.query(func.count(Application.id)).filter(*filters).scalar() or 0
    total_pages = max(1, math.ceil(total / PER_PAGE))
    page = min(max(1, page), total_pages)

    sort_columns = SORTABLE_COLUMNS.get(sort, SORTABLE_COLUMNS["date"])
    descending = direction != "asc"
    order_by = [col.desc() if descending else col.asc() for col in sort_columns]
    order_by.append(Application.id.desc())  # stable tiebreaker

    rows = (
        db.query(Application)
        .filter(*filters)
        .order_by(*order_by)
        .limit(PER_PAGE)
        .offset((page - 1) * PER_PAGE)
        .all()
    )

    return {
        "items": [serialize_summary(a) for a in rows],
        "total": int(total),
        "page": page,
        "per_page": PER_PAGE,
        "total_pages": total_pages,
    }


def distinct_ranks(db: Session) -> list:
    """SELECT DISTINCT position_rank ... ORDER BY position_rank (submissions.php)."""
    rows = (
        db.query(Application.position_rank)
        .distinct()
        .order_by(Application.position_rank)
        .all()
    )
    return [r[0] for r in rows]


def get_application(db: Session, application_id: int):
    return db.get(Application, application_id)


def fetch_for_export(db: Session, search: str, rank: str, status: str = "") -> list:
    """All matching rows, newest first — same as export-all-csv.php."""
    filters = build_search_filters(search, rank, status)
    return (
        db.query(Application)
        .filter(*filters)
        .order_by(Application.submitted_at.desc())
        .all()
    )


# ──────────────────────────────────────────────
# Review workflow
# ──────────────────────────────────────────────

def update_status(db: Session, application: Application, new_status: str, user: dict) -> Application:
    application.status = new_status
    application.reviewed_by = user["id"]
    application.reviewed_at = func.now()
    db.commit()
    db.refresh(application)
    return application


# ──────────────────────────────────────────────
# Status history (from the audit trail)
# ──────────────────────────────────────────────

HISTORY_ACTIONS = ("status_changed", "application_submitted", "application_resubmitted")


def get_status_history(db: Session, application: Application, include_usernames: bool = True) -> list:
    """Timeline of submission and review events for one application.

    Sourced from the audit log; the initial submission is synthesised from
    submitted_at for legacy rows that predate audit logging.
    """
    rows = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity == "application",
            AuditLog.entity_id == application.id,
            AuditLog.action.in_(HISTORY_ACTIONS),
        )
        .order_by(AuditLog.id.asc())
        .all()
    )

    events = []
    has_submission_event = any(r.action == "application_submitted" for r in rows)
    if not has_submission_event:
        events.append({
            "action": "application_submitted",
            "username": None,
            "details": None,
            "created_at": application.submitted_at.isoformat() if application.submitted_at else None,
        })

    for row in rows:
        events.append({
            "action": row.action,
            "username": row.username if include_usernames else None,
            "details": row.details,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        })
    return events


# ──────────────────────────────────────────────
# Reviewer comments
# ──────────────────────────────────────────────

def serialize_comment(comment: ApplicationComment) -> dict:
    return {
        "id": comment.id,
        "application_id": comment.application_id,
        "user_id": comment.user_id,
        "username": comment.username,
        "comment": comment.comment,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


def list_comments(db: Session, application_id: int) -> list:
    rows = (
        db.query(ApplicationComment)
        .filter(ApplicationComment.application_id == application_id)
        .order_by(ApplicationComment.id.asc())
        .all()
    )
    return [serialize_comment(c) for c in rows]


def add_comment(db: Session, application_id: int, user: dict, comment_text: str) -> ApplicationComment:
    comment = ApplicationComment(
        application_id=application_id,
        user_id=user["id"],
        username=user["username"],
        comment=comment_text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, comment_id: int, user: dict) -> ApplicationComment:
    comment = db.get(ApplicationComment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != user["id"] and user["role"] != "Administrator":
        raise HTTPException(status_code=403, detail="You can only delete your own comments")
    db.delete(comment)
    db.commit()
    return comment


# ──────────────────────────────────────────────
# Data quality: duplicate detection
# ──────────────────────────────────────────────

def find_duplicates(db: Session) -> dict:
    """Submissions sharing an email address or telephone number.

    The original migrate_v2.sql wanted a UNIQUE (email, telephone) index;
    this report surfaces the conflicting rows so they can be cleaned up
    before that constraint is applied.
    """
    dup_emails = (
        select(Application.email)
        .where(Application.email != "")
        .group_by(Application.email)
        .having(func.count() > 1)
    )
    by_email = (
        db.query(Application)
        .filter(Application.email.in_(dup_emails))
        .order_by(Application.email, Application.submitted_at.desc())
        .all()
    )

    dup_phones = (
        select(Application.telephone)
        .where(Application.telephone != "")
        .group_by(Application.telephone)
        .having(func.count() > 1)
    )
    by_phone = (
        db.query(Application)
        .filter(Application.telephone.in_(dup_phones))
        .order_by(Application.telephone, Application.submitted_at.desc())
        .all()
    )

    return {
        "by_email": [serialize_summary(a) for a in by_email],
        "by_telephone": [serialize_summary(a) for a in by_phone],
    }
