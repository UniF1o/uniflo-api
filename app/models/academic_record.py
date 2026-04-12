from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field
import uuid

class AcademicRecord(SQLModel, table=True):
    __tablename__ = "academic_records"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: uuid.UUID = Field(foreign_key="student_profiles.id", nullable=False)
    institution: str
    year: int
    subjects: Optional[Any] = Field(default=None, sa_column= Column(JSONB, nullable=True))
    aggregate: Optional[int] = Field(default=None)
    
    
