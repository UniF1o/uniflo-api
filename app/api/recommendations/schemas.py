from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Recommendations endpoint — locked contract (Appendix A)
# ---------------------------------------------------------------------------


class MatchStatus(str, Enum):
    QUALIFIES = "qualifies"
    BORDERLINE = "borderline"
    NOT_YET = "not_yet"


class UnmetRule(BaseModel):
    requirement: str  # "Mathematics 65%"  |  "APS 35"
    have: str  # "Mathematics 58%"  |  "APS 34"
    shortfall: str  # "7%"               |  "1 point"


class ProgrammeMatch(BaseModel):
    id: str
    name: str
    faculty: Optional[str]
    qualification_code: Optional[str]
    # "degree" | "diploma" | "higher_certificate". Extended programmes are not a
    # separate type — distinguish them by duration_years (4 vs 3).
    qualification_type: Optional[str] = None
    duration_years: Optional[int] = None
    min_aps: Optional[int]
    status: MatchStatus
    unmet_rules: list[UnmetRule]
    notes: Optional[str]  # non-academic requirements (NBT, portfolio…), shown not scored


class RecommendationsResponse(BaseModel):
    university_id: str
    intake_year: int
    record_type_used: str
    aps: int
    aps_max: int
    programmes: list[ProgrammeMatch]


# ---------------------------------------------------------------------------
# Catalogue endpoint — GET /universities/{id}/programmes
# ---------------------------------------------------------------------------


class ProgrammeCatalogueItem(BaseModel):
    id: str
    name: str
    qualification_code: Optional[str]
    qualification_type: Optional[str] = None
    duration_years: Optional[int] = None
    min_aps: Optional[int]
    notes: Optional[str]


class FacultyGroup(BaseModel):
    faculty_id: str
    faculty_name: str
    close_date: Optional[date]
    programmes: list[ProgrammeCatalogueItem]


class ProgrammesCatalogueResponse(BaseModel):
    university_id: str
    intake_year: int
    faculties: list[FacultyGroup]
