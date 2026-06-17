import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: uuid.UUID = Field(foreign_key="student_profiles.id", nullable=False)
    type: str
    storage_path: str = Field(nullable=False)
    # User-supplied upload filename, for display only. Storage paths use a UUID,
    # never this value. Nullable: legacy rows and uploads without a name have none.
    original_filename: Optional[str] = Field(default=None, nullable=True)
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
