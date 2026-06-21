import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class Application(SQLModel, table=True):
    __tablename__ = "applications"
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: uuid.UUID = Field(
        foreign_key="student_profiles.id", nullable=False, index=True
    )
    university_id: uuid.UUID = Field(
        foreign_key="universities.id", nullable=False, index=True
    )
    programme: str
    programme_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="programmes.id", nullable=True, index=True
    )
    application_year: int
    status: Optional[str]
    # Consent timestamps — set when the student explicitly accepts the portal's
    # POPI notice and its application agreement. The automation will not tick the
    # POPI box / submit on their behalf until the relevant one is recorded.
    popi_consent_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    agreement_consent_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    submitted_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
