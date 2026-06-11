"""
Voyage & employment history — the "Placement" in NSPD.

Each record is one sea-service engagement (vessel, employer, rank held,
sign-on/sign-off). An open voyage (signed_off IS NULL with a sign-on
date) means the seafarer is currently on board.
"""

import datetime as dt

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Voyage


def serialize(voyage: Voyage) -> dict:
    onboard = voyage.signed_on is not None and voyage.signed_off is None
    days = None
    if voyage.signed_on:
        end = voyage.signed_off or dt.date.today()
        days = max(0, (end - voyage.signed_on).days)
    return {
        "id": voyage.id,
        "application_id": voyage.application_id,
        "vessel_name": voyage.vessel_name,
        "vessel_type": voyage.vessel_type,
        "imo_number": voyage.imo_number,
        "employer": voyage.employer,
        "rank_held": voyage.rank_held,
        "signed_on": voyage.signed_on.isoformat() if voyage.signed_on else None,
        "signed_off": voyage.signed_off.isoformat() if voyage.signed_off else None,
        "remarks": voyage.remarks,
        "added_by": voyage.added_by,
        "onboard": onboard,
        "days": days,
    }


def list_for_application(db: Session, application_id: int) -> dict:
    rows = (
        db.query(Voyage)
        .filter(Voyage.application_id == application_id)
        .order_by(Voyage.signed_on.is_(None), Voyage.signed_on.desc())
        .all()
    )
    voyages = [serialize(v) for v in rows]
    total_days = sum(v["days"] or 0 for v in voyages)
    return {
        "voyages": voyages,
        "summary": {
            "total_voyages": len(voyages),
            "total_days": total_days,
            "currently_onboard": any(v["onboard"] for v in voyages),
        },
    }


def create(db: Session, application_id: int, form, added_by: int = None) -> Voyage:
    if form.signed_on and form.signed_off and form.signed_off < form.signed_on:
        raise HTTPException(status_code=400, detail="Sign-off date cannot be before the sign-on date")

    voyage = Voyage(
        application_id=application_id,
        vessel_name=form.vessel_name.strip(),
        vessel_type=(form.vessel_type or "").strip() or None,
        imo_number=(form.imo_number or "").strip() or None,
        employer=(form.employer or "").strip() or None,
        rank_held=(form.rank_held or "").strip() or None,
        signed_on=form.signed_on,
        signed_off=form.signed_off,
        remarks=(form.remarks or "").strip() or None,
        added_by=added_by,
    )
    db.add(voyage)
    db.commit()
    db.refresh(voyage)
    return voyage


def get_or_404(db: Session, voyage_id: int) -> Voyage:
    voyage = db.get(Voyage, voyage_id)
    if voyage is None:
        raise HTTPException(status_code=404, detail="Voyage not found")
    return voyage


def delete(db: Session, voyage: Voyage) -> None:
    db.delete(voyage)
    db.commit()


def count_onboard(db: Session) -> int:
    """Seafarers currently on board (distinct applications with an open voyage)."""
    return (
        db.query(func.count(func.distinct(Voyage.application_id)))
        .filter(Voyage.signed_on.isnot(None), Voyage.signed_off.is_(None))
        .scalar()
        or 0
    )
