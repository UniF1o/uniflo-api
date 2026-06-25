import uuid

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session

from app.db import get_session
from app.models.user import User


def require_admin(request: Request, session: Session = Depends(get_session)) -> User:
    user_id = uuid.UUID(request.state.user["sub"])
    user = session.get(User, user_id)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
