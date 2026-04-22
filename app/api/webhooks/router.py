import hmac
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr
from sqlmodel import Session

from app.config import settings
from app.db import get_session
from app.models.user import User

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class UserCreatedRecord(BaseModel):
    id: uuid.UUID
    email: EmailStr


class UserCreatedPayload(BaseModel):
    record: UserCreatedRecord


class UserDeletedRecord(BaseModel):
    id: uuid.UUID


class UserDeletedPayload(BaseModel):
    record: UserDeletedRecord


def _verify_secret(provided: str | None, expected: str) -> None:
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Unauthorised")


@router.post("/user-created")
def user_created(
    payload: UserCreatedPayload,
    x_webhook_secret: str | None = Header(default=None, alias="x-webhook-secret"),
    session: Session = Depends(get_session),
):
    _verify_secret(x_webhook_secret, settings.WEBHOOK_SECRET)

    record = payload.record
    if session.get(User, record.id):
        return {"status": "user already exists"}

    session.add(User(id=record.id, email=record.email, role="student"))
    session.commit()
    return {"status": "ok"}


@router.post("/user-deleted")
def user_deleted(
    payload: UserDeletedPayload,
    x_webhook_secret: str | None = Header(default=None, alias="x-webhook-secret"),
    session: Session = Depends(get_session),
):
    _verify_secret(x_webhook_secret, settings.DELETE_WEBHOOK_SECRET)

    existing = session.get(User, payload.record.id)
    if not existing:
        return {"status": "user doesn't exist"}

    session.delete(existing)
    session.commit()
    return {"status": "ok"}
