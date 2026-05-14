import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UniversityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    website: str
    portal_url: str
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    is_active: bool


class UniversitiesListResponse(BaseModel):
    items: list[UniversityRead]
