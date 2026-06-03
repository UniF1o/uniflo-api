from fastapi import APIRouter, Depends, Query, Request, Response
from sqlmodel import Session

from app.api.contacts import service
from app.api.contacts.schemas import ContactResponse, ContactType, ContactWrite
from app.db import get_session

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactResponse], operation_id="contacts_list")
def list_contacts(request: Request, session: Session = Depends(get_session)):
    user_id = request.state.user["sub"]
    return service.list_contacts(session, user_id)


@router.post(
    "",
    response_model=ContactResponse,
    status_code=201,
    operation_id="contacts_upsert",
)
def upsert_contact(
    request: Request,
    data: ContactWrite,
    session: Session = Depends(get_session),
):
    # Upsert by (student, contact_type) — at most one contact of each type.
    user_id = request.state.user["sub"]
    return service.upsert_contact(session, user_id, data)


@router.delete("", status_code=204, operation_id="contacts_delete")
def delete_contact(
    request: Request,
    contact_type: ContactType = Query(...),
    session: Session = Depends(get_session),
):
    user_id = request.state.user["sub"]
    service.delete_contact(session, user_id, contact_type.value)
    return Response(status_code=204)
