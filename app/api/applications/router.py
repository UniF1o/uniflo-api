import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.api.applications import service
from app.api.applications.schemas import ApplicationCreate, ApplicationRead
from app.db import get_session

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationRead, status_code=201)
def create_application(
    request: Request,
    data: ApplicationCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    user_id = request.state.user["sub"]
    application = service.create_application(session, user_id, data)
    background_tasks.add_task(process_application_stub, application.id)
    return application


@router.get("", response_model=list[ApplicationRead])
def list_applications(
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = request.state.user["sub"]
    return service.list_applications(session, user_id)


@router.get("/{application_id}", response_model=ApplicationRead)
def get_application(
    application_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = request.state.user["sub"]
    return service.get_application(session, user_id, application_id)


@router.post("/{application_id}/retry")
def retry_application(application_id: uuid.UUID):
    return JSONResponse(
        status_code=501,
        content={"detail": "retry_not_yet_implemented"}
    )


def process_application_stub(application_id: uuid.UUID):
    # Phase 2 stub — replaced by real Playwright adapter in Phase 3
    pass