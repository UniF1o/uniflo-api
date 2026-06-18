import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Programme(SQLModel, table=True):
    __tablename__ = "programmes"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    university_id: uuid.UUID = Field(
        foreign_key="universities.id", nullable=False, index=True
    )
    faculty_id: uuid.UUID = Field(
        foreign_key="faculties.id", nullable=False, index=True
    )
    name: str = Field(nullable=False)
    qualification_code: Optional[str] = Field(default=None, nullable=True)
    intake_year: int = Field(nullable=False)
    min_aps: Optional[int] = Field(default=None, nullable=True)
    # subject_rules: list of {subjects, min_mark?, min_level?}
    requirements: Any = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default="{}")
    )
    notes: Optional[str] = Field(default=None, nullable=True)
    is_active: bool = Field(default=False)
    source_page: Optional[int] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=True,
        ),
    )
