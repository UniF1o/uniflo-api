from typing import Any, Optional

from pydantic import BaseModel


class CompensationOut(BaseModel):
    entry: int
    mid: int
    senior: int
    currency: str
    period: str
    display: str


class EmployabilityOut(BaseModel):
    demand: str
    outlook: str
    pathways: list[str]
    employment_note: Optional[str] = None


class CareerRead(BaseModel):
    id: str
    slug: str
    title: str
    industry: str
    description: str
    compensation: CompensationOut
    employability: EmployabilityOut
    required_subjects: list[str] = []


class CareersListResponse(BaseModel):
    careers: list[CareerRead]


# Per-university group returned by GET /careers/{id}/programmes.
# Reuses the same match-status vocabulary as /recommendations.
class CareerProgrammeMatch(BaseModel):
    id: str
    name: str
    faculty: Optional[str] = None
    qualification_type: Optional[str] = None
    duration_years: Optional[int] = None
    min_aps: Optional[int] = None
    status: str  # qualifies | borderline | not_yet
    unmet_rules: list[Any] = []
    notes: Optional[str] = None


class CareerUniversityGroup(BaseModel):
    university_id: str
    university_name: str
    scoring_method: Optional[str] = None
    aps: int
    aps_max: int
    programmes: list[CareerProgrammeMatch]


class CareerProgrammesResponse(BaseModel):
    career_id: str
    career_title: str
    # Empty means TVET/college-only path — frontend renders the note.
    universities: list[CareerUniversityGroup]
    tvet_only: bool = False
