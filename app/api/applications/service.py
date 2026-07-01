import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.applications.schemas import (
    ApplicationCreate,
    ApplicationStatus,
    FieldMappingEntryRead,
    FieldMappingRead,
)
from app.api.profiles.schemas import REQUIRED_PROFILE_FIELDS
from app.automation.screenshots import create_signed_url, is_storage_path
from app.models.application import Application
from app.models.application_choice import ApplicationChoice
from app.models.application_job import ApplicationJob
from app.models.field_mapping import FieldMappingRecord
from app.models.portal_challenge import PortalChallenge
from app.models.programme import Programme
from app.models.student_profile import StudentProfile
from app.models.university import University


def _sign_job_screenshot(job: Optional[ApplicationJob]) -> None:
    """Replace a job's stored screenshot *path* with a short-lived signed URL for
    the response. In-memory only — read endpoints never commit, so the path stays
    in the DB (do NOT call this on a code path that commits)."""
    if job is not None and is_storage_path(job.screenshot_url):
        job.screenshot_url = create_signed_url(job.screenshot_url)


def get_student_profile(session: Session, user_id: str) -> StudentProfile:
    statement = select(StudentProfile).where(
        StudentProfile.user_id == uuid.UUID(user_id)
    )
    profile = session.exec(statement).first()

    if not profile:
        raise HTTPException(status_code=403, detail="profile_not_found")

    return profile


def get_latest_job(
    session: Session, application_id: uuid.UUID
) -> Optional[ApplicationJob]:
    statement = (
        select(ApplicationJob)
        .where(ApplicationJob.application_id == application_id)
        .order_by(ApplicationJob.created_at.desc())
        .limit(1)
    )
    return session.exec(statement).first()


def get_pending_challenge(
    session: Session, application_id: uuid.UUID
) -> Optional[PortalChallenge]:
    """The latest unanswered email challenge, if the run is waiting on one
    (status `action_required`). The app renders one input per requested field."""
    statement = (
        select(PortalChallenge)
        .where(PortalChallenge.application_id == application_id)
        .where(PortalChallenge.supplied_at == None)  # noqa: E711 — SQL IS NULL
        .order_by(PortalChallenge.created_at.desc())
        .limit(1)
    )
    return session.exec(statement).first()


def get_choices(
    session: Session, application_id: uuid.UUID
) -> list[ApplicationChoice]:
    statement = (
        select(ApplicationChoice)
        .where(ApplicationChoice.application_id == application_id)
        .order_by(ApplicationChoice.choice_number)
    )
    return list(session.exec(statement).all())


_REQUIRED_PROFILE_FIELDS = REQUIRED_PROFILE_FIELDS


def _resolve_programme(
    session: Session, programme_id: uuid.UUID, university_id: uuid.UUID
) -> Programme:
    """Load a programme and assert it is active and belongs to the university."""
    prog = session.get(Programme, programme_id)
    if not prog or not prog.is_active or prog.university_id != university_id:
        raise HTTPException(status_code=422, detail="programme_not_found_or_invalid")
    return prog


def create_application(
    session: Session, user_id: str, data: ApplicationCreate
) -> Application:
    # resolve student profile
    profile = get_student_profile(session, user_id)

    incomplete = [f for f in _REQUIRED_PROFILE_FIELDS if getattr(profile, f) is None]
    if incomplete:
        raise HTTPException(
            status_code=422,
            detail={"code": "profile_incomplete", "missing_fields": incomplete},
        )

    # POPIA: a minor's application needs recorded guardian consent before we
    # process and submit their personal data on their behalf.
    dob = profile.date_of_birth
    if isinstance(dob, date):
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18 and getattr(profile, "guardian_consent_at", None) is None:
            raise HTTPException(
                status_code=422, detail={"code": "guardian_consent_required"}
            )

    # validate university exists and is active
    university = session.get(University, data.university_id)
    if not university:
        raise HTTPException(status_code=400, detail="university_not_found")
    if not university.is_active:
        raise HTTPException(status_code=400, detail="university_inactive")

    # validate application deadline
    if university.close_date and university.close_date < date.today():
        raise HTTPException(
            status_code=400,
            detail={
                "code": "applications_closed",
                "close_date": university.close_date.isoformat(),
            },
        )

    # Resolve primary programme — id is authoritative; name is derived from catalogue
    # when programme_id is supplied, and taken from the free-text field otherwise.
    programme_name = data.programme
    resolved_programme_id: Optional[uuid.UUID] = data.programme_id
    if data.programme_id is not None:
        prog = _resolve_programme(session, data.programme_id, data.university_id)
        programme_name = prog.name

    # Resolve additional choices: zip ids + names (ids win when both are present)
    additional_progs = data.additional_programmes or []
    additional_ids = data.additional_programme_ids or []
    n_additional = max(len(additional_progs), len(additional_ids))
    additional_choices: list[tuple[str, Optional[uuid.UUID]]] = []
    for i in range(n_additional):
        prog_id = additional_ids[i] if i < len(additional_ids) else None
        prog_name = additional_progs[i] if i < len(additional_progs) else None
        if prog_id is not None:
            prog = _resolve_programme(session, prog_id, data.university_id)
            additional_choices.append((prog.name, prog_id))
        else:
            additional_choices.append((prog_name, None))  # type: ignore[arg-type]

    # create application, job, and programme choices in the same transaction
    application = Application(
        student_id=profile.id,
        university_id=data.university_id,
        programme=programme_name,
        programme_id=resolved_programme_id,
        application_year=data.application_year,
        status=ApplicationStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    session.add(application)
    session.flush()  # get application.id without committing

    job = ApplicationJob(
        application_id=application.id,
        status=ApplicationStatus.PENDING,
        attempts=0,
    )
    session.add(job)

    # Choice 1 mirrors the primary programme
    session.add(
        ApplicationChoice(
            application_id=application.id,
            choice_number=1,
            programme=programme_name,
            programme_id=resolved_programme_id,
        )
    )

    # Choices 2+ from additional
    for choice_number, (name, prog_id) in enumerate(additional_choices, start=2):
        session.add(
            ApplicationChoice(
                application_id=application.id,
                choice_number=choice_number,
                programme=name,
                programme_id=prog_id,
            )
        )

    session.commit()
    session.refresh(application)
    session.refresh(job)

    application.latest_job = job
    application.choices = get_choices(session, application.id)
    application.pending_challenge = None
    return application


def retry_application(
    session: Session, user_id: str, application_id: uuid.UUID
) -> Application:
    """Queue a fresh automation attempt for a failed application: a new
    ApplicationJob (preserving the failed one) + status back to pending. The
    router enqueues `process_application` after this returns."""
    profile = get_student_profile(session, user_id)
    application = session.get(Application, application_id)
    if not application or application.student_id != profile.id:
        raise HTTPException(status_code=404, detail="application_not_found")

    if application.status == ApplicationStatus.SUBMITTED:
        raise HTTPException(status_code=409, detail={"code": "already_submitted"})
    latest = get_latest_job(session, application_id)
    if latest and latest.status in (
        ApplicationStatus.PENDING,
        ApplicationStatus.PROCESSING,
        ApplicationStatus.ACTION_REQUIRED,
    ):
        raise HTTPException(status_code=409, detail={"code": "already_in_progress"})

    job = ApplicationJob(
        application_id=application.id,
        status=ApplicationStatus.PENDING,
        attempts=0,
    )
    session.add(job)
    application.status = ApplicationStatus.PENDING
    application.updated_at = datetime.now(timezone.utc)
    session.add(application)
    session.commit()
    session.refresh(application)
    session.refresh(job)

    application.latest_job = job
    application.choices = get_choices(session, application.id)
    application.pending_challenge = get_pending_challenge(session, application.id)
    return application


def supply_challenge(
    session: Session,
    user_id: str,
    application_id: uuid.UUID,
    values: dict[str, str],
) -> Application:
    """Answer the pending email challenge (e.g. type in the OTP the portal sent).
    The waiting automation run polls the row and continues once the values land;
    it clears them after consumption."""
    profile = get_student_profile(session, user_id)
    application = session.get(Application, application_id)
    if not application or application.student_id != profile.id:
        raise HTTPException(status_code=404, detail="application_not_found")

    challenge = get_pending_challenge(session, application_id)
    if challenge is None:
        raise HTTPException(status_code=404, detail="no_pending_challenge")

    requested = list(challenge.requested_fields or [])
    missing = [f for f in requested if not values.get(f)]
    if missing:
        raise HTTPException(
            status_code=422,
            detail={"code": "missing_challenge_fields", "missing_fields": missing},
        )

    # Store only what was asked for — extra keys are dropped.
    challenge.supplied_values = {f: values[f] for f in requested}
    challenge.supplied_at = datetime.now(timezone.utc)
    session.add(challenge)
    session.commit()
    session.refresh(application)

    application.latest_job = get_latest_job(session, application.id)
    _sign_job_screenshot(application.latest_job)
    application.choices = get_choices(session, application.id)
    application.pending_challenge = get_pending_challenge(session, application.id)
    return application


def record_consent(
    session: Session,
    user_id: str,
    application_id: uuid.UUID,
    *,
    popi: bool,
    agreement: bool,
) -> Application:
    """Record the student's explicit POPI / agreement acceptance (timestamps).
    At least one flag must be true. The automation gate reads these before it
    ticks POPI / submits on the student's behalf."""
    if not (popi or agreement):
        raise HTTPException(
            status_code=422, detail={"code": "no_consent_specified"}
        )
    profile = get_student_profile(session, user_id)
    application = session.get(Application, application_id)
    if not application or application.student_id != profile.id:
        raise HTTPException(status_code=404, detail="application_not_found")

    now = datetime.now(timezone.utc)
    if popi:
        application.popi_consent_at = now
    if agreement:
        application.agreement_consent_at = now
    application.updated_at = now
    session.add(application)
    session.commit()
    session.refresh(application)

    application.latest_job = get_latest_job(session, application.id)
    _sign_job_screenshot(application.latest_job)
    application.choices = get_choices(session, application.id)
    application.pending_challenge = get_pending_challenge(session, application.id)
    return application


def list_applications(session: Session, user_id: str) -> list[Application]:
    profile = get_student_profile(session, user_id)

    statement = (
        select(Application)
        .where(Application.student_id == profile.id)
        .order_by(Application.created_at.desc())
    )
    applications = session.exec(statement).all()

    # attach latest job + ordered choices to each application
    for app in applications:
        app.latest_job = get_latest_job(session, app.id)
        _sign_job_screenshot(app.latest_job)
        app.choices = get_choices(session, app.id)
        app.pending_challenge = get_pending_challenge(session, app.id)

    return applications


def get_field_mapping(
    session: Session, user_id: str, application_id: uuid.UUID
) -> FieldMappingRead:
    """The AI-proposed mapping for Partner-A's review screen. 404 if the
    application isn't the student's, or no mapping has been produced yet."""
    profile = get_student_profile(session, user_id)
    application = session.get(Application, application_id)
    if not application or application.student_id != profile.id:
        raise HTTPException(status_code=404, detail="application_not_found")

    record = session.exec(
        select(FieldMappingRecord).where(
            FieldMappingRecord.application_id == application_id
        )
    ).first()
    if record is None:
        raise HTTPException(status_code=404, detail="field_mapping_not_found")

    threshold = record.confidence_threshold
    entries = [
        FieldMappingEntryRead(
            field_id=e.get("field_id"),
            value=e.get("value"),
            confidence=e.get("confidence", 0.0),
            flagged=e.get("confidence", 0.0) < threshold,
            reasoning=e.get("reasoning", ""),
            source_profile_field=e.get("source_profile_field"),
        )
        for e in (record.entries or [])
    ]
    return FieldMappingRead(
        application_id=record.application_id,
        university_id=record.university_id,
        overall_confidence=record.overall_confidence,
        confidence_threshold=threshold,
        entries=entries,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def get_application(
    session: Session, user_id: str, application_id: uuid.UUID
) -> Application:
    profile = get_student_profile(session, user_id)

    application = session.get(Application, application_id)

    if not application or application.student_id != profile.id:
        raise HTTPException(status_code=404, detail="application_not_found")

    application.latest_job = get_latest_job(session, application.id)
    application.choices = get_choices(session, application.id)
    application.pending_challenge = get_pending_challenge(session, application.id)
    return application
