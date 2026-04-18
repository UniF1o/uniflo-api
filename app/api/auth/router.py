from fastapi import APIRouter, Request, Depends
from sqlmodel import Session

from app.db import get_session
from app.models.user import User
from app.api.auth.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/me", response_model=UserResponse)
def get_me(request: Request, session: Session = Depends(get_session)):
    # extract user UUID from JWT payload attached by middleware
    user_id = request.state.user["sub"]
    email = request.state.user["email"]

    user = session.get(User, user_id)
    if not user:
        # self-heal — create missing row if webhook failed on sign-up
        user = User(id=user_id, email=email, role="student")
        session.add(user)
        session.commit()
        session.refresh(user)

    return user

