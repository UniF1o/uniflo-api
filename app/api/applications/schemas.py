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


class ApplicationCreate(BaseModel):
    university_id: uuid.UUID
    programme: str
    application_year: int

    @field_validator("programme")
    @classmethod
    def validate_programme(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Programme must be at least 3 characters")
        if len(v) > 120:
            raise ValueError("Programme must be at most 120 characters")
        return v

    @field_validator("application_year")
    @classmethod
    def validate_application_year(cls, v: int) -> int:
        if v not in (2026, 2027):
            raise ValueError("application_year must be 2026 or 2027")
        return v