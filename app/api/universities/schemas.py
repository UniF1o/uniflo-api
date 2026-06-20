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
    # Identifies the APS scoring function used for this university. The frontend
    # maps this to a display label ("APS" for up_aps/wits_aps, "FPS" for uct_fps)
    # so the score header on the /courses page reads correctly per university.
    scoring_method: Optional[str] = None


class UniversitiesListResponse(BaseModel):
    items: list[UniversityRead]
