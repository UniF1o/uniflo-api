from __future__ import annotations

import re
import uuid
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.academic_records.schemas import SubjectIn
from app.api.careers.schemas import (
    CareerProgrammeMatch,
    CareerProgrammesResponse,
    CareerRead,
    CareersListResponse,
    CareerUniversityGroup,
    CompensationOut,
    EmployabilityOut,
)
from app.api.recommendations.schemas import UnmetRule
from app.api.recommendations.scoring import aps_margin_for, compute_aps, evaluate
from app.api.recommendations.service import (
    _APS_MAX,
    _STATUS_ORDER,
    _best_available_record,
    _get_profile,
    _load_active_programmes,
    _load_faculties,
)
from app.intake import active_intake_year
from app.models.career import Career
from app.models.university import University


def _passes_subject_rule(student_subjects: set[str], subject_rule: dict) -> bool:
    all_of: list[str] = subject_rule.get("all_of", [])
    any_of: list[str] = subject_rule.get("any_of", [])
    if all_of and not all(s in student_subjects for s in all_of):
        return False
    if any_of and not any(s in student_subjects for s in any_of):
        return False
    return True


def _keyword_matches(programme_name: str, keyword: str) -> bool:
    # Word-boundary match — prevents "law" catching "Economics with Law"
    # when the keyword is intended to match dedicated law programmes.
    pattern = r"\b" + re.escape(keyword.strip()) + r"\b"
    return bool(re.search(pattern, programme_name, re.IGNORECASE))


def _matches_keywords(programme_name: str, keywords: list[str]) -> bool:
    return any(_keyword_matches(programme_name, kw) for kw in keywords)


def _career_to_read(career: Career) -> CareerRead:
    comp = career.compensation or {}
    emp = career.employability or {}
    return CareerRead(
        id=str(career.id),
        slug=career.slug,
        title=career.title,
        industry=career.industry,
        description=career.description,
        compensation=CompensationOut(
            entry=comp.get("entry", 0),
            mid=comp.get("mid", 0),
            senior=comp.get("senior", 0),
            currency=comp.get("currency", "ZAR"),
            period=comp.get("period", "month"),
            display=comp.get("display", ""),
        ),
        employability=EmployabilityOut(
            demand=emp.get("demand", ""),
            outlook=emp.get("outlook", ""),
            pathways=emp.get("pathways", []),
            employment_note=emp.get("employment_note"),
        ),
        recommended_subjects=career.recommended_subjects or None,
    )


def list_careers(
    session: Session,
    user_id: str,
    intake_year: Optional[int] = None,
) -> CareersListResponse:
    profile = _get_profile(session, user_id)
    record = _best_available_record(session, profile.id, None)
    if record is None:
        raise HTTPException(status_code=409, detail={"code": "no_academic_record"})

    student_subjects: set[str] = {
        s.get("name", "") for s in (record.subjects or []) if s.get("name")
    }

    careers = session.exec(
        select(Career).where(Career.is_active == True)  # noqa: E712
    ).all()

    matched = [
        _career_to_read(c)
        for c in careers
        if _passes_subject_rule(student_subjects, c.subject_rule or {})
    ]

    return CareersListResponse(careers=matched)


def list_career_programmes(
    session: Session,
    user_id: str,
    career_id: uuid.UUID,
    intake_year: Optional[int] = None,
) -> CareerProgrammesResponse:
    profile = _get_profile(session, user_id)
    record = _best_available_record(session, profile.id, None)
    if record is None:
        raise HTTPException(status_code=409, detail={"code": "no_academic_record"})

    career = session.get(Career, career_id)
    if not career or not career.is_active:
        raise HTTPException(status_code=404, detail="career_not_found")

    keywords: list[str] = career.programme_keywords or []
    active_year = intake_year or active_intake_year()
    subjects = [SubjectIn(**s) for s in (record.subjects or [])]

    universities = session.exec(select(University)).all()

    university_groups: list[CareerUniversityGroup] = []
    for uni in universities:
        method = uni.scoring_method or "up_aps"
        aps = compute_aps(subjects, method)
        aps_max = _APS_MAX.get(method, 42)
        margin = aps_margin_for(method)

        faculties = _load_faculties(session, uni.id)
        programmes = _load_active_programmes(session, uni.id, active_year)

        matched_progs = [p for p in programmes if _matches_keywords(p.name, keywords)]
        if not matched_progs:
            continue

        sorted_matches = []
        for prog in matched_progs:
            result = evaluate(subjects, aps, prog, aps_margin=margin)
            sorted_matches.append((prog, result))

        sorted_matches.sort(
            key=lambda item: (
                _STATUS_ORDER.get(item[1].status, 99),
                max(0, (item[0].min_aps or 0) - aps),
            )
        )

        programme_matches = []
        for prog, result in sorted_matches:
            faculty = faculties.get(prog.faculty_id)
            programme_matches.append(
                CareerProgrammeMatch(
                    id=str(prog.id),
                    name=prog.name,
                    faculty=faculty.name if faculty else None,
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

        university_groups.append(
            CareerUniversityGroup(
                university_id=str(uni.id),
                university_name=uni.name,
                scoring_method=uni.scoring_method,
                aps=aps,
                aps_max=aps_max,
                programmes=programme_matches,
            )
        )

    return CareerProgrammesResponse(
        career_id=str(career_id),
        career_title=career.title,
        universities=university_groups,
        tvet_only=len(university_groups) == 0,
    )
