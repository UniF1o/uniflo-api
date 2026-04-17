from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.config import settings
from app.models.user import User
from app.db import get_session
from fastapi import Depends

router = APIRouter()

@router.post("/webhooks/user-created")
async def user_created(
    request: Request,
    session: Session = Depends(get_session)
):
    secret = request.headers.get("x-webhook-secret")

    if secret != settings.WEBHOOK_SECRET:
        return JSONResponse(
            status_code= 401,
            content = {"detail":"Unauthorised"}
        )
    payload = await request.json()
    record = payload["record"]

    user_id = record["id"]
    email = record["email"]
    #user_created_at = record["created_at"]

    existing = session.get(User, user_id)
    if existing:
        return {"status":"user already exists"}
    user = User(id=user_id, email=email,  role="student") #created_at=user_created_at,
    session.add(user)
    session.commit()

    return {"status":"ok"}

@router.post("/webhooks/user-deleted")
async def user_deleted(
    request: Request,
    session: Session = Depends(get_session)
):
    secret = request.headers.get("x-webhook-secret")

    if secret != settings.DELETE_WEBHOOK_SECRET:
        return JSONResponse(
            status_code= 401,
            content = {"detail":"Unauthorised"}
        )
    payload = await request.json()
    record = payload["record"]

    user_id = record["id"]
    
    existing = session.get(User, user_id)
    if not existing:
        return {"status":"user doesn't exist"}
    session.delete(existing)
    session.commit()

    return {"status":"ok"}