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
    first_name: str = Field(nullable=False)
    last_name: str = Field(nullable=False)
    id_number: str = Field(unique=True)
    date_of_birth: date
    phone: str = Field(nullable=False)
    address: str = Field(nullable=False)
    nationality: str = Field(nullable=False)
    gender: str = Field(nullable=False)
    home_language: str = Field(nullable=False)
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=True,
        ),
    )
