import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.api.auth.schemas import UserResponse
from app.db import get_session
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse, operation_id="auth_me")
def get_me(request: Request, session: Session = Depends(get_session)):
    user_id = uuid.UUID(request.state.user["sub"])
    user = session.get(User, user_id)
    if not user:
        # AuthMiddleware.ensure_user_synced should have created this row;
        # only happens if middleware was bypassed (e.g. during tests).
        raise HTTPException(status_code=404, detail="User not found")
    return user
