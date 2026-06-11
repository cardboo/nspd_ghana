"""
Analytics queries for the Reports page.

Converted from api/reports-data.php — the five chart datasets keep the
exact same JSON shape so the Chart.js frontend code is unchanged.
"""

from datetime import datetime, timedelta

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session

from ..models import Application


def _parse_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def build_report_filters(
    rank: str,
    course: str,
    medical: str,
    ship_type: str,
    date_from: str = "",
    date_to: str = "",
) -> list:
    """Shared WHERE clause: the PHP version's filters plus a date range."""
    filters = []
    if rank:
        filters.append(Application.position_rank == rank)
    if course:
        filters.append(Application.short_courses_rmu == course)
    if medical:
        filters.append(Application.medicals == medical)
    if ship_type:
        filters.append(Application.last_ship_type == ship_type)

    start = _parse_date(date_from)
    if start:
        filters.append(Application.submitted_at >= start)
    end = _parse_date(date_to)
    if end:
        # inclusive end date: anything before the following midnight
        filters.append(Application.submitted_at < end + timedelta(days=1))
    return filters


def get_filter_options(db: Session) -> dict:
    """Distinct ranks and ship types (previously rendered server-side in reports.php)."""
    ranks = [
        r[0]
        for r in db.query(Application.position_rank)
        .filter(Application.position_rank.isnot(None), Application.position_rank != "")
        .distinct()
        .order_by(Application.position_rank)
        .all()
    ]
    ship_types = [
        r[0]
        for r in db.query(Application.last_ship_type)
        .filter(Application.last_ship_type.isnot(None), Application.last_ship_type != "")
        .distinct()
        .order_by(Application.last_ship_type)
        .all()
    ]
    return {"ranks": ranks, "ship_types": ship_types}


def get_report_data(
    db: Session,
    rank: str,
    course: str,
    medical: str,
    ship_type: str,
    date_from: str = "",
    date_to: str = "",
) -> dict:
    filters = build_report_filters(rank, course, medical, ship_type, date_from, date_to)

    # 1. APPLICATION TRENDS (LINE CHART)
    # Grouping by both month expressions (same granularity) keeps the query
    # valid under MySQL's ONLY_FULL_GROUP_BY, which cloud MySQL enables.
    month_label = func.date_format(Application.submitted_at, "%b %Y")
    month_key = func.date_format(Application.submitted_at, "%Y-%m")
    trends = (
        db.query(month_label.label("month"), func.count().label("count"))
        .filter(*filters)
        .group_by(month_key, month_label)
        .order_by(func.min(Application.submitted_at).asc())
        .limit(12)
        .all()
    )
    application_trends = {
        "labels": [row.month for row in trends],
        "values": [int(row.count) for row in trends],
    }

    # 2. RANK DISTRIBUTION (BAR CHART)
    rank_rows = (
        db.query(Application.position_rank, func.count().label("count"))
        .filter(*filters)
        .group_by(Application.position_rank)
        .order_by(func.count().desc())
        .all()
    )
    rank_distribution = {
        "labels": [row.position_rank for row in rank_rows],
        "values": [int(row.count) for row in rank_rows],
    }

    # 3. SEA EXPERIENCE DISTRIBUTION (PIE CHART)
    years = Application.total_sea_experience_years
    exp = (
        db.query(
            func.sum(case((years.between(0, 2), 1), else_=0)).label("exp_0_2"),
            func.sum(case((and_(years > 2, years <= 5), 1), else_=0)).label("exp_3_5"),
            func.sum(case((and_(years > 5, years <= 10), 1), else_=0)).label("exp_6_10"),
            func.sum(case((years > 10, 1), else_=0)).label("exp_10_plus"),
        )
        .filter(*filters)
        .one()
    )
    experience_distribution = {
        "labels": ["0-2 years", "3-5 years", "6-10 years", "10+ years"],
        "values": [int(v or 0) for v in exp],
    }

    # 4. CERTIFICATION COVERAGE (DOUGHNUT CHART)
    cert = (
        db.query(
            func.sum(case((Application.short_courses_rmu == "Yes", 1), else_=0)).label("rmu"),
            func.sum(case((Application.familiarisation_isps_gma == "Yes", 1), else_=0)).label("gma"),
            func.sum(
                case(
                    (
                        and_(
                            Application.short_courses_rmu != "Yes",
                            Application.familiarisation_isps_gma != "Yes",
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("incomplete"),
        )
        .filter(*filters)
        .one()
    )
    certification_coverage = {
        "labels": ["RMU Short Courses", "GMA / ISPS", "Incomplete"],
        "values": [int(v or 0) for v in cert],
    }

    # 5. MEDICAL FITNESS STATUS (PIE CHART)
    medical_rows = (
        db.query(
            func.sum(case((Application.medicals == "Yes", 1), else_=0)).label("fit"),
            func.sum(
                case(
                    (or_(Application.medicals != "Yes", Application.medicals.is_(None)), 1),
                    else_=0,
                )
            ).label("unfit"),
        )
        .filter(*filters)
        .one()
    )
    medical_status = {
        "labels": ["Medically Fit", "Not Medically Fit"],
        "values": [int(v or 0) for v in medical_rows],
    }

    return {
        "applicationTrends": application_trends,
        "rankDistribution": rank_distribution,
        "experienceDistribution": experience_distribution,
        "certificationCoverage": certification_coverage,
        "medicalStatus": medical_status,
    }
