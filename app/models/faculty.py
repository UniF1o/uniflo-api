import uuid
from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class Faculty(SQLModel, table=True):
    __tablename__ = "faculties"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    university_id: uuid.UUID = Field(
        foreign_key="universities.id", nullable=False, index=True
    )
    name: str = Field(nullable=False)
    close_date: Optional[date] = Field(default=None)
