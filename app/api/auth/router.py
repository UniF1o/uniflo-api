import uuid

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.api.auth.schemas import UserResponse
from app.db import get_session
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
def get_me(request: Request, session: Session = Depends(get_session)):
    user_id = uuid.UUID(request.state.user["sub"])
    email = request.state.user["email"]

    user = session.get(User, user_id)
    if not user:
        # Self-heal if the webhook missed this user on sign-up.
        user = User(id=user_id, email=email, role="student")
        session.add(user)
        session.commit()
        session.refresh(user)

    return user
