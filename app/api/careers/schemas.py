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
    # Subject-combination guidance (from the career's subject_rule): the subjects
    # a learner should choose from Grade 10 to keep this career open. required =
    # all_of (all needed), any_of = at least one, recommended = nice-to-have.
    required_subjects: list[str] = []
    any_of_subjects: list[str] = []
    recommended_subjects: list[str] = []


class CareersListResponse(BaseModel):
    careers: list[CareerRead]
    # True when the learner has no subjects yet (Grade 8-9): the list is the full
    # browse set rather than a subject-matched shortlist.
    explore: bool = False


# Per-university group returned by GET /careers/{id}/programmes.
# Reuses the same match-status vocabulary as /recommendations.
class CareerProgrammeMatch(BaseModel):
    id: str
    name: str
    faculty: Optional[str] = None
    qualification_type: Optional[str] = None
    duration_years: Optional[int] = None
    min_aps: Optional[int] = None
    status: str  # qualifies | borderline | not_yet | requirements
    unmet_rules: list[Any] = []
    # Admission subject rules as guidance strings — always populated, and the
    # primary payload in "requirements" mode (learner has no marks yet).
    subject_requirements: list[str] = []
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
