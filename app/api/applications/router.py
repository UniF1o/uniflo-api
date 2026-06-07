import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlmodel import Session

from app.api.applications import service
from app.api.applications.schemas import (
    ApplicationCreate,
    ApplicationRead,
    ConsentRequest,
    FieldMappingRead,
)
from app.api.automation.background import process_application
from app.db import get_session

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post(
    "",
    response_model=ApplicationRead,
    status_code=201,
    operation_id="applications_create",
)
def create_application(
    request: Request,
    data: ApplicationCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    user_id = request.state.user["sub"]
    application = service.create_application(session, user_id, data)
    background_tasks.add_task(process_application, application.id)
    return application


@router.get("", response_model=list[ApplicationRead], operation_id="applications_list")
def list_applications(request: Request, session: Session = Depends(get_session)):
    user_id = request.state.user["sub"]
    return service.list_applications(session, user_id)


@router.get(
    "/{application_id}", response_model=ApplicationRead, operation_id="applications_get"
)
def get_application(
    application_id: uuid.UUID, request: Request, session: Session = Depends(get_session)
):
    user_id = request.state.user["sub"]
    return service.get_application(session, user_id, application_id)


@router.get(
    "/{application_id}/field-mappings",
    response_model=FieldMappingRead,
    operation_id="applications_field_mappings",
)
def get_field_mapping(
    application_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    user_id = request.state.user["sub"]
    return service.get_field_mapping(session, user_id, application_id)


@router.post(
    "/{application_id}/consent",
    response_model=ApplicationRead,
    operation_id="applications_consent",
)
def record_consent(
    application_id: uuid.UUID,
    data: ConsentRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    user_id = request.state.user["sub"]
    return service.record_consent(
        session, user_id, application_id, popi=data.popi, agreement=data.agreement
    )


@router.post(
    "/{application_id}/retry",
    response_model=ApplicationRead,
    operation_id="applications_retry",
)
def retry_application(
    application_id: uuid.UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    user_id = request.state.user["sub"]
    application = service.retry_application(session, user_id, application_id)
    background_tasks.add_task(process_application, application.id)
    return application
