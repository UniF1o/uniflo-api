import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    # The run is waiting in place for the student (e.g. an emailed OTP) — the
    # frontend prompts using `pending_challenge.requested_fields` and posts the
    # values to /applications/{id}/challenge.
    ACTION_REQUIRED = "action_required"
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
    programme_id: Optional[uuid.UUID] = None
    eligible: Optional[bool] = None


class PendingChallengeRead(BaseModel):
    """An unanswered email challenge the run is waiting on — non-null while the
    status is `action_required`. The app shows one input per requested field
    (e.g. ["otp"], or ["temp_id", "password"]) and posts the values to
    /applications/{id}/challenge."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    portal_slug: str
    requested_fields: list[str]
    created_at: datetime


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    university_id: uuid.UUID
    programme: str
    programme_id: Optional[uuid.UUID] = None
    application_year: int
    status: Optional[ApplicationStatus]
    submitted_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_at: datetime
    # When the student accepted the portal's POPI notice / application agreement
    # (null = not yet — the automation won't tick POPI / submit without these).
    popi_consent_at: Optional[datetime] = None
    agreement_consent_at: Optional[datetime] = None
    latest_job: Optional[ApplicationJobRead] = None
    # Ordered programme choices (choice 1 == `programme`). Portals take 2-3.
    choices: list[ApplicationChoiceRead] = []
    pending_challenge: Optional[PendingChallengeRead] = None


def _validate_programme(v: str) -> str:
    v = v.strip()
    if len(v) < 3:
        raise ValueError("Programme must be at least 3 characters")
    if len(v) > 120:
        raise ValueError("Programme must be at most 120 characters")
    return v


# Most choices any target portal accepts (Wits = 3): choice 1 + 2 extra.
MAX_ADDITIONAL_PROGRAMMES = 2


class FieldMappingEntryRead(BaseModel):
    """One mapped field for the review screen. `flagged` == low confidence
    (below the threshold in force when the mapping was produced)."""

    field_id: str
    value: Optional[str] = None
    confidence: float
    flagged: bool
    reasoning: str = ""
    source_profile_field: Optional[str] = None


class FieldMappingRead(BaseModel):
    application_id: uuid.UUID
    university_id: uuid.UUID
    overall_confidence: float
    confidence_threshold: float
    entries: list[FieldMappingEntryRead]
    created_at: datetime
    updated_at: Optional[datetime] = None


class ConsentRequest(BaseModel):
    """Records the student's explicit acceptance after they've viewed the portal's
    POPI notice / application agreement (surfaced by the frontend). At least one
    must be true."""

    popi: bool = False
    agreement: bool = False


class ChallengeSupplyRequest(BaseModel):
    """The student's answer to a pending challenge: one value per requested
    field name (extra keys are ignored, missing ones are a 422)."""

    values: dict[str, str]

    @field_validator("values")
    @classmethod
    def validate_values(cls, v: dict[str, str]) -> dict[str, str]:
        if not v:
            raise ValueError("values must not be empty")
        if len(v) > 10:
            raise ValueError("too many values")
        cleaned = {}
        for key, value in v.items():
            value = value.strip()
            if not value:
                raise ValueError(f"value for {key!r} must not be blank")
            if len(value) > 200:
                raise ValueError(f"value for {key!r} is too long")
            cleaned[key.strip()] = value
        return cleaned


class ApplicationCreate(BaseModel):
    university_id: uuid.UUID
    programme: str
    programme_id: Optional[uuid.UUID] = None
    # Optional 2nd/3rd choices, in preference order after `programme`.
    additional_programmes: Optional[list[str]] = None
    additional_programme_ids: Optional[list[uuid.UUID]] = None
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

    @field_validator("additional_programme_ids")
    @classmethod
    def validate_additional_programme_ids(
        cls, v: Optional[list[uuid.UUID]]
    ) -> Optional[list[uuid.UUID]]:
        if v is None:
            return v
        if len(v) > MAX_ADDITIONAL_PROGRAMMES:
            raise ValueError(
                f"At most {MAX_ADDITIONAL_PROGRAMMES} additional programme ids allowed"
            )
        return v

    @model_validator(mode="after")
    def validate_parallel_lengths(self) -> "ApplicationCreate":
        progs = self.additional_programmes
        ids = self.additional_programme_ids
        if progs is not None and ids is not None and len(progs) != len(ids):
            raise ValueError(
                "additional_programmes and additional_programme_ids must be the same length"
            )
        return self

    @field_validator("application_year")
    @classmethod
    def validate_application_year(cls, v: int) -> int:
        if v not in (2026, 2027):
            raise ValueError("application_year must be 2026 or 2027")
        return v
