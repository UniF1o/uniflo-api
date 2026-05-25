import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.applications.schemas import ApplicationCreate, ApplicationStatus
from app.api.profiles.schemas import REQUIRED_PROFILE_FIELDS
from app.models.application import Application
from app.models.application_job import ApplicationJob
from app.models.student_profile import StudentProfile
from app.models.university import University


def get_student_profile(session: Session, user_id: str) -> StudentProfile:
    statement = select(StudentProfile).where(
        StudentProfile.user_id == uuid.UUID(user_id)
    )
    profile = session.exec(statement).first()

    if not profile:
        raise HTTPException(status_code=403, detail="profile_not_found")

    return profile


def get_latest_job(
    session: Session, application_id: uuid.UUID
) -> Optional[ApplicationJob]:
    statement = (
        select(ApplicationJob)
        .where(ApplicationJob.application_id == application_id)
        .order_by(ApplicationJob.created_at.desc())
        .limit(1)
    )
    return session.exec(statement).first()


_REQUIRED_PROFILE_FIELDS = REQUIRED_PROFILE_FIELDS


def create_application(
    session: Session, user_id: str, data: ApplicationCreate
) -> Application:
    # resolve student profile
    profile = get_student_profile(session, user_id)

    incomplete = [f for f in _REQUIRED_PROFILE_FIELDS if getattr(profile, f) is None]
    if incomplete:
        raise HTTPException(
            status_code=422,
            detail={"code": "profile_incomplete", "missing_fields": incomplete},
        )

    # validate university exists and is active
    university = session.get(University, data.university_id)
    if not university:
        raise HTTPException(status_code=400, detail="university_not_found")
    if not university.is_active:
        raise HTTPException(status_code=400, detail="university_inactive")

    # validate application deadline
    if university.close_date and university.close_date < date.today():
        raise HTTPException(
            status_code=400,
            detail={
                "code": "applications_closed",
                "close_date": university.close_date.isoformat(),
            },
        )

    # create application and job in same transaction
    application = Application(
        student_id=profile.id,
        university_id=data.university_id,
        programme=data.programme,
        application_year=data.application_year,
        status=ApplicationStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    session.add(application)
    session.flush()  # get application.id without committing

    job = ApplicationJob(
        application_id=application.id,
        status=ApplicationStatus.PENDING,
        attempts=0,
    )
    session.add(job)
    session.commit()
    session.refresh(application)
    session.refresh(job)

    application.latest_job = job
    return application


def list_applications(session: Session, user_id: str) -> list[Application]:
    profile = get_student_profile(session, user_id)

    statement = (
        select(Application)
        .where(Application.student_id == profile.id)
        .order_by(Application.created_at.desc())
    )
    applications = session.exec(statement).all()

    # attach latest job to each application
    for app in applications:
        app.latest_job = get_latest_job(session, app.id)

    return applications


def get_application(
    session: Session, user_id: str, application_id: uuid.UUID
) -> Application:
    profile = get_student_profile(session, user_id)

    application = session.get(Application, application_id)

    if not application or application.student_id != profile.id:
        raise HTTPException(status_code=404, detail="application_not_found")

    application.latest_job = get_latest_job(session, application.id)
    return application
