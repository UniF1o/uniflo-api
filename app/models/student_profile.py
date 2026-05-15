import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class StudentProfile(SQLModel, table=True):
    __tablename__ = "student_profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, unique=True, index=True
    )
    first_name: Optional[str] = Field(default=None, nullable=True)
    last_name: Optional[str] = Field(default=None, nullable=True)
    id_number: Optional[str] = Field(default=None, unique=True, nullable=True)
    date_of_birth: Optional[date] = Field(default=None, nullable=True)
    phone: Optional[str] = Field(default=None, nullable=True)
    address: Optional[str] = Field(default=None, nullable=True)
    nationality: Optional[str] = Field(default=None, nullable=True)
    gender: Optional[str] = Field(default=None, nullable=True)
    home_language: Optional[str] = Field(default=None, nullable=True)
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=True,
        ),
    )
