from datetime import datetime, timezone, date
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid

class Document(SQLModel, table=True):
    __tablename__ = "documents"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: uuid.UUID = Field(foreign_key="student_profiles.id", nullable=False)
    type: str
    storage_url: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))