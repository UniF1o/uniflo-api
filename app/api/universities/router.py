import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlmodel import Session

from app.api.universities import service
from app.api.universities.schemas import UniversitiesListResponse, UniversityRead
from app.db import get_session

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/universities", tags=["universities"])


@router.get("", response_model=UniversitiesListResponse)
@limiter.limit("60/minute")
def list_universities(
    request: Request,
    q: Optional[str] = None,
    is_active: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    universities = service.list_universities(session, q, is_active)
    return UniversitiesListResponse(items=universities)


@router.get("/{university_id}", response_model=UniversityRead)
@limiter.limit("60/minute")
def get_university(
    request: Request,
    university_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    return service.get_university(session, university_id)