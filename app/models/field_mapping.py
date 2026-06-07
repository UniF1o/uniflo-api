import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class FieldMappingRecord(SQLModel, table=True):
    """The AI-proposed mapping of a student's profile onto a portal's form, kept
    for Partner-A's review screen (it renders the entries + flags the
    low-confidence ones). One current mapping per application (upserted when
    regenerated). `entries` is the list of FieldMappingEntry dicts
    (field_id / value / confidence / reasoning / source_profile_field).

    Named `FieldMappingRecord` to avoid clashing with the runtime's transient
    `app.automation.base.FieldMapping` value-map."""

    __tablename__ = "field_mappings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    application_id: uuid.UUID = Field(
        foreign_key="applications.id", nullable=False, unique=True, index=True
    )
    university_id: uuid.UUID = Field(nullable=False)
    entries: Any = Field(sa_column=Column(JSONB, nullable=False))
    overall_confidence: float = Field(default=0.0)
    # The threshold in force when the mapping was produced; entries below it are
    # the ones the review screen flags.
    confidence_threshold: float = Field(default=0.85)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=True,
        ),
    )
