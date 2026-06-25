import uuid

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.admin.schemas import (
    AdminApplicationRow,
    AdminApplicationsResponse,
    AdminStatsResponse,
    AdminStudentRow,
    AdminStudentsResponse,
    ApplicationStatusCount,
    UniversityCreate,
    UniversityUpdate,
)
from app.models.application import Application
from app.models.student_profile import StudentProfile
from app.models.university import University
from app.models.user import User


def get_stats(session: Session) -> AdminStatsResponse:
    total_students = session.exec(
        select(func.count(User.id)).where(User.role == "student")
    ).one()

    active_universities = session.exec(
        select(func.count(University.id)).where(University.is_active == True)  # noqa: E712
    ).one()

    status_rows = session.exec(
        select(Application.status, func.count(Application.id)).group_by(
            Application.status
        )
    ).all()

    return AdminStatsResponse(
        total_students=total_students,
        active_universities=active_universities,
        applications_by_status=[
            ApplicationStatusCount(status=s or "unknown", count=c)
            for s, c in status_rows
        ],
    )


def list_students(session: Session, page: int, per_page: int) -> AdminStudentsResponse:
    offset = (page - 1) * per_page

    total = session.exec(
        select(func.count(User.id)).where(User.role == "student")
    ).one()

    rows = session.exec(
        select(User, StudentProfile)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .where(User.role == "student")
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(per_page)
    ).all()

    user_ids = [u.id for u, _ in rows]
    app_counts: dict[uuid.UUID, int] = {}
    if user_ids:
        count_rows = session.exec(
            select(StudentProfile.user_id, func.count(Application.id).label("cnt"))
            .join(Application, Application.student_id == StudentProfile.id)
            .where(StudentProfile.user_id.in_(user_ids))
            .group_by(StudentProfile.user_id)
        ).all()
        app_counts = {row[0]: row[1] for row in count_rows}

    items = []
    for user, profile in rows:
        profile_complete = bool(
            profile
            and profile.first_name
            and profile.last_name
            and profile.id_number
            and profile.date_of_birth
        )
        items.append(
            AdminStudentRow(
                user_id=user.id,
                email=user.email,
                first_name=profile.first_name if profile else None,
                last_name=profile.last_name if profile else None,
                profile_complete=profile_complete,
                application_count=app_counts.get(user.id, 0),
                created_at=user.created_at,
            )
        )

    return AdminStudentsResponse(items=items, total=total, page=page, per_page=per_page)


def list_applications(
    session: Session, page: int, per_page: int
) -> AdminApplicationsResponse:
    offset = (page - 1) * per_page

    total = session.exec(select(func.count(Application.id))).one()

    rows = session.exec(
        select(Application, StudentProfile, User, University)
        .join(StudentProfile, StudentProfile.id == Application.student_id)
        .join(User, User.id == StudentProfile.user_id)
        .join(University, University.id == Application.university_id)
        .order_by(Application.created_at.desc())
        .offset(offset)
        .limit(per_page)
    ).all()

    items = [
        AdminApplicationRow(
            id=app.id,
            student_email=user.email,
            student_name=(
                f"{profile.first_name or ''} {profile.last_name or ''}".strip() or None
            ),
            university_name=university.name,
            programme=app.programme,
            status=app.status,
            created_at=app.created_at,
        )
        for app, profile, user, university in rows
    ]

    return AdminApplicationsResponse(
        items=items, total=total, page=page, per_page=per_page
    )


def create_university(session: Session, data: UniversityCreate) -> University:
    university = University(
        name=data.name,
        website=data.website,
        portal_url=data.portal_url,
        open_date=data.open_date,
        close_date=data.close_date,
        is_active=data.is_active,
        scoring_method=data.scoring_method,
    )
    session.add(university)
    session.commit()
    session.refresh(university)
    return university


def update_university(
    session: Session, university_id: uuid.UUID, data: UniversityUpdate
) -> University:
    university = session.get(University, university_id)
    if not university:
        raise HTTPException(status_code=404, detail="university_not_found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(university, field, value)

    session.add(university)
    session.commit()
    session.refresh(university)
    return university
