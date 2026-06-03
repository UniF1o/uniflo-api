import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUBMITTED = "submitted"
    FAILED = "failed"


class ApplicationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: Optional[ApplicationStatus]
    attempts: int
    last_error: Optional[str]
    screenshot_url: Optional[str]
    updated_at: Optional[datetime]
    created_at: datetime


class ApplicationChoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    choice_number: int
    programme: str
    eligible: Optional[bool] = None


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    university_id: uuid.UUID
    programme: str
    application_year: int
    status: Optional[ApplicationStatus]
    submitted_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_at: datetime
    latest_job: Optional[ApplicationJobRead] = None
    # Ordered programme choices (choice 1 == `programme`). Portals take 2-3.
    choices: list[ApplicationChoiceRead] = []


def _validate_programme(v: str) -> str:
    v = v.strip()
    if len(v) < 3:
        raise ValueError("Programme must be at least 3 characters")
    if len(v) > 120:
        raise ValueError("Programme must be at most 120 characters")
    return v


# Most choices any target portal accepts (Wits = 3): choice 1 + 2 extra.
MAX_ADDITIONAL_PROGRAMMES = 2


class ApplicationCreate(BaseModel):
    university_id: uuid.UUID
    programme: str
    # Optional 2nd/3rd choices, in preference order after `programme`.
    additional_programmes: Optional[list[str]] = None
    application_year: int

    @field_validator("programme")
    @classmethod
    def validate_programme(cls, v: str) -> str:
        return _validate_programme(v)

    @field_validator("additional_programmes")
    @classmethod
    def validate_additional_programmes(
        cls, v: Optional[list[str]]
    ) -> Optional[list[str]]:
        if v is None:
            return v
        if len(v) > MAX_ADDITIONAL_PROGRAMMES:
            raise ValueError(
                f"At most {MAX_ADDITIONAL_PROGRAMMES} additional programmes allowed"
            )
        return [_validate_programme(p) for p in v]

    @field_validator("application_year")
    @classmethod
    def validate_application_year(cls, v: int) -> int:
        if v not in (2026, 2027):
            raise ValueError("application_year must be 2026 or 2027")
        return v
