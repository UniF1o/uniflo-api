from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.academic_records.schemas import SubjectIn
from app.api.recommendations.schemas import (
    FacultyGroup,
    MatchStatus,
    ProgrammeCatalogueItem,
    ProgrammeMatch,
    ProgrammesCatalogueResponse,
    RecommendationsResponse,
    UnmetRule,
)
from app.api.recommendations.scoring import compute_aps, evaluate
from app.intake import active_intake_year
from app.models.academic_record import AcademicRecord
from app.models.faculty import Faculty
from app.models.programme import Programme
from app.models.student_profile import StudentProfile
from app.models.university import University

# Preference order for "best available" record selection.
_RECORD_PREFERENCE = ["grade_12_june", "grade_12_april", "grade_11_final"]

# Maximum possible APS per scoring method (best-6 at level 7).
_APS_MAX: dict[str, int] = {"up_aps": 42}

# Status sort order for the response.
_STATUS_ORDER: dict[str, int] = {
    MatchStatus.QUALIFIES: 0,
    MatchStatus.BORDERLINE: 1,
    MatchStatus.NOT_YET: 2,
}


def _get_profile(session: Session, user_id: str) -> StudentProfile:
    profile = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == uuid.UUID(user_id))
    ).first()
    if not profile:
        raise HTTPException(status_code=403, detail="profile_not_found")
    return profile


def _best_available_record(
    session: Session, profile_id: uuid.UUID, record_type: Optional[str]
) -> Optional[AcademicRecord]:
    if record_type:
        return session.exec(
            select(AcademicRecord).where(
                AcademicRecord.student_id == profile_id,
                AcademicRecord.record_type == record_type,
            )
        ).first()
    for rt in _RECORD_PREFERENCE:
        record = session.exec(
            select(AcademicRecord).where(
                AcademicRecord.student_id == profile_id,
                AcademicRecord.record_type == rt,
            )
        ).first()
        if record:
            return record
    return None


def _load_faculties(session: Session, university_id: uuid.UUID) -> dict[uuid.UUID, Faculty]:
    rows = session.exec(
        select(Faculty).where(Faculty.university_id == university_id)
    ).all()
    return {f.id: f for f in rows}


def _load_active_programmes(
    session: Session, university_id: uuid.UUID, intake_year: int
) -> list[Programme]:
    return list(
        session.exec(
            select(Programme).where(
                Programme.university_id == university_id,
                Programme.intake_year == intake_year,
                Programme.is_active == True,  # noqa: E712
            )
        ).all()
    )


def get_recommendations(
    session: Session,
    user_id: str,
    university_id: uuid.UUID,
    record_type: Optional[str] = None,
    intake_year: Optional[int] = None,
) -> RecommendationsResponse:
    profile = _get_profile(session, user_id)

    record = _best_available_record(session, profile.id, record_type)
    if record is None:
        raise HTTPException(
            status_code=409, detail={"code": "no_academic_record"}
        )

    university = session.get(University, university_id)
    if not university:
        raise HTTPException(status_code=404, detail="university_not_found")

    active_year = intake_year or active_intake_year()
    faculties = _load_faculties(session, university_id)
    programmes = _load_active_programmes(session, university_id, active_year)

    subjects = [SubjectIn(**s) for s in (record.subjects or [])]
    method = university.scoring_method or "up_aps"
    aps = compute_aps(subjects, method)
    aps_max = _APS_MAX.get(method, 42)

    matches: list[tuple[Programme, object]] = []
    for prog in programmes:
        result = evaluate(subjects, aps, prog)
        matches.append((prog, result))

    def _sort_key(item: tuple[Programme, object]) -> tuple[int, int]:
        prog, result = item
        aps_gap = max(0, (prog.min_aps or 0) - aps)
        return (_STATUS_ORDER.get(result.status, 99), aps_gap)

    matches.sort(key=_sort_key)

    programme_matches = []
    for prog, result in matches:
        faculty = faculties.get(prog.faculty_id)
        programme_matches.append(
            ProgrammeMatch(
                id=str(prog.id),
                name=prog.name,
                faculty=faculty.name if faculty else None,
                qualification_code=prog.qualification_code,
                qualification_type=prog.qualification_type,
                duration_years=prog.duration_years,
                min_aps=prog.min_aps,
                status=result.status,
                unmet_rules=[
                    UnmetRule(
                        requirement=r.requirement,
                        have=r.have,
                        shortfall=r.shortfall,
                    )
                    for r in result.unmet_rules
                ],
                notes=prog.notes,
            )
        )

    return RecommendationsResponse(
        university_id=str(university_id),
        intake_year=active_year,
        record_type_used=record.record_type,
        aps=aps,
        aps_max=aps_max,
        programmes=programme_matches,
    )


def list_university_programmes(
    session: Session,
    university_id: uuid.UUID,
    intake_year: Optional[int] = None,
) -> ProgrammesCatalogueResponse:
    university = session.get(University, university_id)
    if not university:
        raise HTTPException(status_code=404, detail="university_not_found")

    active_year = intake_year or active_intake_year()
    faculties = _load_faculties(session, university_id)
    programmes = _load_active_programmes(session, university_id, active_year)

    # Group programmes by faculty, preserving faculty order.
    groups: dict[uuid.UUID, list[Programme]] = {}
    for prog in programmes:
        groups.setdefault(prog.faculty_id, []).append(prog)

    faculty_groups = []
    for faculty_id, progs in groups.items():
        faculty = faculties.get(faculty_id)
        faculty_groups.append(
            FacultyGroup(
                faculty_id=str(faculty_id),
                faculty_name=faculty.name if faculty else "Unknown",
                close_date=faculty.close_date if faculty else None,
                programmes=[
                    ProgrammeCatalogueItem(
                        id=str(p.id),
                        name=p.name,
                        qualification_code=p.qualification_code,
                        qualification_type=p.qualification_type,
                        duration_years=p.duration_years,
                        min_aps=p.min_aps,
                        notes=p.notes,
                    )
                    for p in progs
                ],
            )
        )

    return ProgrammesCatalogueResponse(
        university_id=str(university_id),
        intake_year=active_year,
        faculties=faculty_groups,
    )
