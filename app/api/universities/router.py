import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.api.recommendations import service as recommendations_service
from app.api.recommendations.schemas import ProgrammesCatalogueResponse
from app.api.universities import service
from app.api.universities.schemas import UniversitiesListResponse, UniversityRead
from app.db import get_session
from app.rate_limit import limiter

router = APIRouter(prefix="/universities", tags=["universities"])


@router.get(
    "", response_model=UniversitiesListResponse, operation_id="universities_list"
)
@limiter.limit("60/minute")
def list_universities(
    request: Request,
    q: Optional[str] = None,
    is_active: Optional[bool] = None,
    session: Session = Depends(get_session),
):
    universities = service.list_universities(session, q, is_active)
    return UniversitiesListResponse(items=universities)


@router.get(
    "/{university_id}", response_model=UniversityRead, operation_id="universities_get"
)
@limiter.limit("60/minute")
def get_university(
    request: Request, university_id: uuid.UUID, session: Session = Depends(get_session)
):
    return service.get_university(session, university_id)


@router.get(
    "/{university_id}/programmes",
    response_model=ProgrammesCatalogueResponse,
    operation_id="universities_programmes",
)
@limiter.limit("60/minute")
def list_university_programmes(
    request: Request,
    university_id: uuid.UUID,
    intake_year: Optional[int] = None,
    session: Session = Depends(get_session),
):
    return recommendations_service.list_university_programmes(
        session, university_id, intake_year
    )
