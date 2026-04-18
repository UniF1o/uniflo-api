import uuid
from sqlmodel import Session, select
from fastapi import HTTPException

from app.models.student_profile import StudentProfile
from app.api.profiles.schemas import StudentProfileCreate, StudentProfileUpdate


def get_profile(session: Session, user_id: str) -> StudentProfile:
    statement = select(StudentProfile).where(StudentProfile.user_id == uuid.UUID(user_id))
    profile = session.exec(statement).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return profile


def create_profile(session: Session, user_id: str, data: StudentProfileCreate) -> StudentProfile:
    statement = select(StudentProfile).where(StudentProfile.user_id == uuid.UUID(user_id))
    existing = session.exec(statement).first()

    if existing:
        raise HTTPException(status_code=409, detail="Profile already exists")

    profile = StudentProfile(
        user_id=uuid.UUID(user_id),
        **data.model_dump()
    )

    session.add(profile)
    session.commit()
    session.refresh(profile)

    return profile


def update_profile(session: Session, user_id: str, data: StudentProfileUpdate) -> StudentProfile:
    profile = get_profile(session, user_id)

    # only update fields that were actually provided
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    session.add(profile)
    session.commit()
    session.refresh(profile)

    return profile