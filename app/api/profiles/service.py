import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.profiles.schemas import StudentProfileCreate, StudentProfileUpdate
from app.models.student_profile import StudentProfile


def get_profile(session: Session, user_id: str) -> StudentProfile:
    statement = select(StudentProfile).where(
        StudentProfile.user_id == uuid.UUID(user_id)
    )
    profile = session.exec(statement).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return profile


def create_profile(
    session: Session, user_id: str, data: StudentProfileCreate
) -> StudentProfile:
    user_uuid = uuid.UUID(user_id)
    statement = select(StudentProfile).where(StudentProfile.user_id == user_uuid)
    profile = session.exec(statement).first()

    if profile:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
    else:
        profile = StudentProfile(
            user_id=user_uuid, **data.model_dump(exclude_unset=True)
        )
        session.add(profile)

    session.commit()
    session.refresh(profile)
    return profile


def update_profile(
    session: Session, user_id: str, data: StudentProfileUpdate
) -> StudentProfile:
    profile = get_profile(session, user_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile
