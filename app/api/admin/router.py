import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api.admin import service
from app.api.admin.schemas import (
    AdminApplicationsResponse,
    AdminStatsResponse,
    AdminStudentsResponse,
    UniversityCreate,
    UniversityUpdate,
)
from app.api.dependencies import require_admin
from app.api.universities import service as uni_service
from app.api.universities.schemas import UniversitiesListResponse, UniversityRead
from app.db import get_session
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStatsResponse, operation_id="admin_stats")
def get_stats(
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    return service.get_stats(session)


@router.get(
    "/students", response_model=AdminStudentsResponse, operation_id="admin_students"
)
def list_students(
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    return service.list_students(session, page, per_page)


@router.get(
    "/applications",
    response_model=AdminApplicationsResponse,
    operation_id="admin_applications",
)
def list_applications(
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    return service.list_applications(session, page, per_page)


@router.get(
    "/universities",
    response_model=UniversitiesListResponse,
    operation_id="admin_universities_list",
)
def list_universities(
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    return UniversitiesListResponse(items=uni_service.list_universities(session))


@router.post(
    "/universities",
    response_model=UniversityRead,
    status_code=201,
    operation_id="admin_universities_create",
)
def create_university(
    data: UniversityCreate,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    return service.create_university(session, data)


@router.patch(
    "/universities/{university_id}",
    response_model=UniversityRead,
    operation_id="admin_universities_update",
)
def update_university(
    university_id: uuid.UUID,
    data: UniversityUpdate,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    return service.update_university(session, university_id, data)
