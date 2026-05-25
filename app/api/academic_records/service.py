import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.academic_records.schemas import (
    AcademicRecordCreate,
    AcademicRecordPatch,
    SubjectIn,
)
from app.models.academic_record import AcademicRecord
from app.models.student_profile import StudentProfile

# Sentinel for a free-text subject. The frozen NSC subject list is owned by
# the frontend (lib/constants/nsc-subjects.ts) for now, so the backend trusts
# the names it receives and only enforces the structural rules below.
OTHER = "Other"


def _resolve_profile(session: Session, user_id: str) -> Optional[StudentProfile]:
    statement = select(StudentProfile).where(
        StudentProfile.user_id == uuid.UUID(user_id)
    )
    return session.exec(statement).first()


def _require_profile(session: Session, user_id: str) -> StudentProfile:
    profile = _resolve_profile(session, user_id)
    if profile is None:
        # Mirrors applications: a write needs the student_profiles FK target.
        raise HTTPException(status_code=403, detail="profile_not_found")
    return profile


def _bad(message: str) -> HTTPException:
    # Plain-string detail so the frontend renders it verbatim.
    return HTTPException(status_code=422, detail=message)


def _validate_and_normalize(
    institution: str, year: int, subjects: list[SubjectIn]
) -> tuple[str, int, list[dict]]:
    institution = (institution or "").strip()
    if not institution:
        raise _bad("Institution is required.")

    max_year = datetime.now(timezone.utc).year + 1
    if year < 2000 or year > max_year:
        raise _bad(f"Year must be between 2000 and {max_year}.")

    if not subjects:
        raise _bad("At least one subject is required.")

    normalized: list[dict] = []
    seen_names: set[str] = set()

    for subject in subjects:
        name = (subject.name or "").strip()
        custom = (subject.custom_name or "").strip()
        label = custom or name or "subject"

        if not isinstance(subject.mark, int) or not 0 <= subject.mark <= 100:
            raise _bad(f"Mark for '{label}' must be between 0 and 100.")

        if name == OTHER:
            if not custom:
                raise _bad(
                    "custom_name is required when subject name is 'Other'."
                )
            normalized.append(
                {"name": OTHER, "mark": subject.mark, "custom_name": custom}
            )
            continue

        if not name:
            raise _bad("Subject name is required.")
        if custom:
            raise _bad(
                "custom_name is only allowed when subject name is 'Other'."
            )
        if name in seen_names:
            raise _bad(f"Duplicate subject: '{name}'.")
        seen_names.add(name)
        normalized.append({"name": name, "mark": subject.mark, "custom_name": None})

    return institution, year, normalized


def _compute_aggregate(subjects: list[dict]) -> float:
    """Authoritative aggregate: the unweighted mean of every subject mark
    (Life Orientation included; this is a naive average, not an APS score),
    rounded to one decimal place. The client-sent value is never trusted.
    """
    marks = [s["mark"] for s in subjects]
    return round(sum(marks) / len(marks), 1)


def get_record(
    session: Session, user_id: str, record_type: str = "grade_11_final"
) -> Optional[AcademicRecord]:
    profile = _resolve_profile(session, user_id)
    if profile is None:
        return None
    statement = select(AcademicRecord).where(
        AcademicRecord.student_id == profile.id,
        AcademicRecord.record_type == record_type,
    )
    return session.exec(statement).first()


def upsert_record(
    session: Session, user_id: str, data: AcademicRecordCreate
) -> AcademicRecord:
    profile = _require_profile(session, user_id)
    institution, year, subjects = _validate_and_normalize(
        data.institution, data.year, data.subjects
    )
    aggregate = _compute_aggregate(subjects)

    record_type = data.record_type.value
    statement = select(AcademicRecord).where(
        AcademicRecord.student_id == profile.id,
        AcademicRecord.record_type == record_type,
    )
    record = session.exec(statement).first()

    if record:
        record.institution = institution
        record.year = year
        record.subjects = subjects
        record.aggregate = aggregate
    else:
        record = AcademicRecord(
            student_id=profile.id,
            record_type=record_type,
            institution=institution,
            year=year,
            subjects=subjects,
            aggregate=aggregate,
        )
        session.add(record)

    session.commit()
    session.refresh(record)
    return record


def patch_record(
    session: Session,
    user_id: str,
    data: AcademicRecordPatch,
    record_type: str = "grade_11_final",
) -> AcademicRecord:
    profile = _require_profile(session, user_id)
    statement = select(AcademicRecord).where(
        AcademicRecord.student_id == profile.id,
        AcademicRecord.record_type == record_type,
    )
    record = session.exec(statement).first()
    if record is None:
        raise HTTPException(
            status_code=404, detail="academic_record_not_found"
        )

    institution = (
        data.institution if data.institution is not None else record.institution
    )
    year = data.year if data.year is not None else record.year
    if data.subjects is not None:
        raw_subjects = data.subjects
    else:
        raw_subjects = [SubjectIn(**s) for s in (record.subjects or [])]

    institution, year, subjects = _validate_and_normalize(
        institution, year, raw_subjects
    )

    record.institution = institution
    record.year = year
    record.subjects = subjects
    record.aggregate = _compute_aggregate(subjects)

    session.add(record)
    session.commit()
    session.refresh(record)
    return record
