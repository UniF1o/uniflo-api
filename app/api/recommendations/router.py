import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.api.recommendations import service
from app.api.recommendations.schemas import RecommendationsResponse
from app.db import get_session
from app.rate_limit import limiter

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationsResponse, operation_id="recommendations_get")
@limiter.limit("60/minute")
def get_recommendations(
    request: Request,
    university_id: uuid.UUID,
    record_type: Optional[str] = None,
    intake_year: Optional[int] = None,
    session: Session = Depends(get_session),
):
    user_id = request.state.user["sub"]
    return service.get_recommendations(
        session, user_id, university_id, record_type, intake_year
    )
