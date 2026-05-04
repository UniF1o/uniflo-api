import uuid
from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class University(SQLModel, table=True):
    __tablename__ = "universities"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, unique=True)
    website: str
    portal_url: str
    open_date: Optional[date]
    close_date: Optional[date]
    is_active: bool = Field(default=False)
