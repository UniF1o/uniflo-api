import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class ApplicationJob(SQLModel, table=True):
    __tablename__ = "application_jobs"
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    application_id: uuid.UUID = Field(
        foreign_key="applications.id", nullable=False, index=True
    )
    status: Optional[str] = Field(index=True)
    attempts: int = Field(default=0)
    last_error: Optional[str]
    screenshot_url: Optional[str]
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=True,
        ),
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
