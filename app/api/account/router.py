from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.api.account import service
from app.db import get_session

router = APIRouter(prefix="/account", tags=["account"])


@router.delete("", status_code=200, operation_id="account_delete")
def delete_account(request: Request, session: Session = Depends(get_session)):
    user_id = request.state.user["sub"]
    service.delete_account(session, user_id)
    return {}
