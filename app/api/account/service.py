import logging
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.academic_record import AcademicRecord
from app.models.application import Application
from app.models.application_job import ApplicationJob
from app.models.document import Document
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def delete_account(session: Session, user_id_str: str) -> None:
    user_uuid = uuid.UUID(user_id_str)

    user = session.get(User, user_uuid)
    if user is None:
        raise HTTPException(status_code=404, detail="user_not_found")

    profile = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == user_uuid)
    ).first()

    if profile:
        applications = session.exec(
            select(Application).where(Application.student_id == profile.id)
        ).all()

        # application_jobs must be deleted before applications (FK child)
        for app in applications:
            for job in session.exec(
                select(ApplicationJob).where(ApplicationJob.application_id == app.id)
            ).all():
                session.delete(job)
        session.flush()

        for app in applications:
            session.delete(app)
        for doc in session.exec(
            select(Document).where(Document.student_id == profile.id)
        ).all():
            session.delete(doc)
        for record in session.exec(
            select(AcademicRecord).where(AcademicRecord.student_id == profile.id)
        ).all():
            session.delete(record)
        session.flush()

        session.delete(profile)
        session.flush()

    session.delete(user)

    # Supabase auth deletion runs before DB commit — if it fails, the
    # transaction rolls back and the client receives 500 and can retry.
    try:
        get_supabase().auth.admin.delete_user(str(user_uuid))
    except Exception as exc:
        logger.exception("Supabase admin delete_user failed for %s", user_uuid)
        raise HTTPException(
            status_code=500,
            detail="account_deletion_auth_failed",
        ) from exc

    session.commit()
