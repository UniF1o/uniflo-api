import uuid
from typing import Any, Optional

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class AcademicRecord(SQLModel, table=True):
    __tablename__ = "academic_records"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "record_type",
            name="uq_academic_records_student_record_type",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: uuid.UUID = Field(
        foreign_key="student_profiles.id", nullable=False, index=True
    )
    record_type: str = Field(default="grade_11_final", nullable=False)
    institution: str
    year: int
    subjects: Optional[Any] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    aggregate: Optional[float] = Field(default=None)
