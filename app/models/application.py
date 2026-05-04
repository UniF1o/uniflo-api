import uuid
from datetime import datetime,timezone
from typing import Optional

from sqlmodel import Field, SQLModel

class Application(SQLModel, table=True):
    __tablename__ = "applications"
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: uuid.UUID = Field(foreign_key="student_profiles.id", nullable=False, index=True)
    university_id: uuid.UUID = Field(foreign_key="universities.id", nullable=False, index=True)
    programme: str
    application_year: int
    status: Optional[str]
    submitted_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))    