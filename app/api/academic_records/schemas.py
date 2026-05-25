import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict

# Shape-only models. All domain rules (custom_name coupling, duplicate and
# range checks) live in service.py so failures return `detail` as a plain
# string the frontend can render directly, rather than FastAPI's default
# array-shaped 422 body. Subject-name membership is owned by the frontend's
# frozen NSC list for now, so the backend does not re-validate it.


class RecordType(str, Enum):
    GRADE_11_FINAL = "grade_11_final"
    GRADE_12_APRIL = "grade_12_april"


class SubjectIn(BaseModel):
    name: str
    mark: int
    custom_name: Optional[str] = None


class AcademicRecordCreate(BaseModel):
    record_type: RecordType = RecordType.GRADE_11_FINAL
    institution: str
    year: int
    subjects: list[SubjectIn]


class AcademicRecordPatch(BaseModel):
    institution: Optional[str] = None
    year: Optional[int] = None
    subjects: Optional[list[SubjectIn]] = None


class SubjectOut(BaseModel):
    # custom_name is always present: a string for "Other" rows, null otherwise.
    # The key is kept stable (rather than omitted) for predictable FE codegen.
    name: str
    mark: int
    custom_name: Optional[str] = None


class AcademicRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    record_type: RecordType
    institution: str
    year: int
    subjects: list[SubjectOut]
    aggregate: Optional[float] = None
