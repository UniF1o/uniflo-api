from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlmodel import Session

from app.api.academic_records import service
from app.api.academic_records.schemas import (
    AcademicRecordCreate,
    AcademicRecordPatch,
    AcademicRecordResponse,
    RecordType,
)
from app.db import get_session

router = APIRouter(prefix="/academic-records", tags=["academic-records"])


@router.post(
    "",
    response_model=AcademicRecordResponse,
    status_code=201,
    operation_id="academic_records_create",
)
def create_academic_record(
    request: Request,
    data: AcademicRecordCreate,
    session: Session = Depends(get_session),
):
    user_id = request.state.user["sub"]
    return service.upsert_record(session, user_id, data)


@router.get(
    "",
    response_model=Optional[AcademicRecordResponse],
    operation_id="academic_records_get",
)
def get_academic_record(
    request: Request,
    record_type: RecordType = Query(default=RecordType.GRADE_11_FINAL),
    session: Session = Depends(get_session),
):
    user_id = request.state.user["sub"]
    # null (not 404) when none yet -- 404-redirect semantics are /profile-only.
    return service.get_record(session, user_id, record_type.value)


@router.patch(
    "",
    response_model=AcademicRecordResponse,
    operation_id="academic_records_update",
)
def update_academic_record(
    request: Request,
    data: AcademicRecordPatch,
    record_type: RecordType = Query(default=RecordType.GRADE_11_FINAL),
    session: Session = Depends(get_session),
):
    user_id = request.state.user["sub"]
    return service.patch_record(session, user_id, data, record_type.value)
