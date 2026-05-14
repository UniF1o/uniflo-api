import uuid
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.university import University


def list_universities(
    session: Session, q: Optional[str] = None, is_active: Optional[bool] = None
) -> list[University]:
    statement = select(University)

    if q:
        statement = statement.where(University.name.ilike(f"%{q}%"))

    if is_active is not None:
        statement = statement.where(University.is_active == is_active)

    statement = statement.order_by(University.name)

    return session.exec(statement).all()


def get_university(session: Session, university_id: uuid.UUID) -> University:
    university = session.get(University, university_id)

    if not university:
        raise HTTPException(status_code=404, detail="university_not_found")

    return university
