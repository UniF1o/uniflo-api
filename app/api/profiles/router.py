from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.db import get_session
from app.api.profiles.schemas import StudentProfileCreate, StudentProfileUpdate, StudentProfileResponse
from app.api.profiles import service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("", response_model=StudentProfileResponse, status_code=201) # Creates profile :)
def create_profile(
    request: Request,
    data: StudentProfileCreate,
    session: Session = Depends(get_session)
):
    user_id = request.state.user["sub"]
    return service.create_profile(session, user_id, data)


@router.get("", response_model=StudentProfileResponse) # Gets sttudent profile details <3
def get_profile(
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = request.state.user["sub"]
    return service.get_profile(session, user_id)


@router.patch("", response_model=StudentProfileResponse) # Updates Student profile details
def update_profile(
    request: Request,
    data: StudentProfileUpdate,
    session: Session = Depends(get_session)
):
    user_id = request.state.user["sub"]
    return service.update_profile(session, user_id, data)