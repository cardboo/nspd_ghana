"""
User administration (Administrator only) and self-service account logic.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..auth import hash_password
from ..models import User


def serialize(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "email": user.email,
        "is_active": bool(user.is_active),
        "must_change_password": bool(user.must_change_password),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


def list_users(db: Session) -> list:
    return [serialize(u) for u in db.query(User).order_by(User.username).all()]


def create_user(db: Session, data) -> User:
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=409, detail="Email already exists")

    user = User(
        username=data.username,
        password_hash=hash_password(data.temp_password),
        full_name=data.full_name,
        role=data.role,
        email=data.email,
        is_active=True,
        must_change_password=True,  # temp password must be replaced at first login
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, data, acting_user: dict) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Safety rails: an administrator cannot demote or deactivate themselves
    if user.id == acting_user["id"]:
        if data.role is not None and data.role != "Administrator":
            raise HTTPException(status_code=400, detail="You cannot change your own role")
        if data.is_active is not None and not data.is_active:
            raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    if data.email is not None and data.email != user.email:
        if db.query(User).filter(User.email == data.email, User.id != user.id).first():
            raise HTTPException(status_code=409, detail="Email already exists")
        user.email = data.email
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active

    db.commit()
    db.refresh(user)
    return user


def reset_password(db: Session, user_id: int, temp_password: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(temp_password)
    user.must_change_password = True
    db.commit()
    db.refresh(user)
    return user
