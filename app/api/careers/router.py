import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.api.careers import service
from app.api.careers.schemas import CareerProgrammesResponse, CareersListResponse
from app.db import get_session
from app.rate_limit import limiter

router = APIRouter(prefix="/careers", tags=["careers"])


@router.get("", response_model=CareersListResponse, operation_id="careers_list")
@limiter.limit("60/minute")
def list_careers(
    request: Request,
    intake_year: Optional[int] = None,
    session: Session = Depends(get_session),
):
    user_id = request.state.user["sub"]
    return service.list_careers(session, user_id, intake_year)


@router.get(
    "/{career_id}/programmes",
    response_model=CareerProgrammesResponse,
    operation_id="careers_programmes_list",
)
@limiter.limit("60/minute")
def list_career_programmes(
    request: Request,
    career_id: uuid.UUID,
    intake_year: Optional[int] = None,
    session: Session = Depends(get_session),
):
    user_id = request.state.user["sub"]
    return service.list_career_programmes(session, user_id, career_id, intake_year)
