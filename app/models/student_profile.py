import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, String
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
    street_address: Optional[str] = Field(default=None, nullable=True)
    suburb: Optional[str] = Field(default=None, nullable=True)
    city: Optional[str] = Field(default=None, nullable=True)
    province: Optional[str] = Field(default=None, nullable=True)
    postal_code: Optional[str] = Field(default=None, sa_column=Column(String(4), nullable=True))
    nationality: Optional[str] = Field(default=None, nullable=True)
    gender: Optional[str] = Field(default=None, nullable=True)
    home_language: Optional[str] = Field(default=None, nullable=True)
    religion: Optional[str] = Field(default=None, nullable=True)
    disability: Optional[str] = Field(default=None, nullable=True)
    marital_status: Optional[str] = Field(default=None, nullable=True)
    ethnicity: Optional[str] = Field(default=None, nullable=True)
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=True,
        ),
    )
