import logging
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.config import settings
from app.db import get_engine
from app.models.application import Application
from app.models.application_job import ApplicationJob

logger = logging.getLogger(__name__)

# Canonical error codes written into application_jobs.last_error.
# Phase 3 Playwright adapters must use only these values so the frontend
# copy-map stays in sync.
JOB_ERROR_CODES = frozenset([
    "internal_error",
    "portal_unavailable",
    "login_failed",
    "form_submit_failed",
    "timeout",
    "invalid_credentials",
])


def process_application(application_id: uuid.UUID) -> None:
    """Entry point queued by `POST /applications`. Routes to the real Playwright
    runtime, or to the Phase-2 simulation when `FAKE_AUTOMATION` is on (the dev
    default). The real path is **submit-gated** by `AUTOMATION_ALLOW_SUBMIT`."""
    if settings.FAKE_AUTOMATION:
        return _run_fake_automation(application_id)
    return _run_real_automation(application_id)


def _run_fake_automation(application_id: uuid.UUID) -> None:
    """Phase 2 simulation — flips status transitions so the dashboard can show
    the lifecycle end to end without touching a real portal."""
    try:
        with Session(get_engine()) as session:
            # fetch application and latest job
            application = session.get(Application, application_id)
            if not application:
                logger.error(
                    "process_application: application %s not found", application_id
                )
                return

            job_statement = (
                select(ApplicationJob)
                .where(ApplicationJob.application_id == application_id)
                .order_by(ApplicationJob.created_at.desc())
                .limit(1)
            )
            job = session.exec(job_statement).first()
            if not job:
                logger.error(
                    "process_application: no job found for application %s",
                    application_id,
                )
                return

            # transition pending → processing
            job.status = "processing"
            application.status = "processing"
            session.add(job)
            session.add(application)
            session.commit()

            # simulate portal interaction delay
            time.sleep(random.uniform(3, 10))

            # flip a coin — 80% submitted, 20% failed
            if random.random() < 0.8:
                job.status = "completed"
                job.attempts += 1
                application.status = "submitted"
                application.submitted_at = datetime.now(timezone.utc)
                logger.info(
                    "process_application: application %s submitted successfully",
                    application_id,
                )
            else:
                job.status = "failed"
                job.attempts += 1
                job.last_error = "timeout"
                application.status = "failed"
                logger.error(
                    "process_application: application %s failed — %s",
                    application_id,
                    job.last_error,
                )

            session.add(job)
            session.add(application)
            session.commit()

    except Exception as exc:
        logger.exception(
            "process_application: unhandled exception for application %s: %s",
            application_id,
            exc,
        )
        # best-effort failure persistence
        try:
            with Session(get_engine()) as session:
                job_statement = (
                    select(ApplicationJob)
                    .where(ApplicationJob.application_id == application_id)
                    .order_by(ApplicationJob.created_at.desc())
                    .limit(1)
                )
                job = session.exec(job_statement).first()
                application = session.get(Application, application_id)

                if job:
                    job.status = "failed"
                    job.last_error = "internal_error"
                    job.attempts += 1
                    session.add(job)

                if application:
                    application.status = "failed"
                    session.add(application)

                session.commit()
        except Exception as inner_exc:
            logger.exception(
                "process_application: failed to persist failure state: %s", inner_exc
            )


# --- real automation -----------------------------------------------------------

# Runtime/adapter failure codes → the canonical JOB_ERROR_CODES the frontend maps.
_ERROR_CODE_MAP = {
    "timeout": "timeout",
    "portal_changed": "form_submit_failed",
    "validation_failed": "form_submit_failed",
    "form_submit_failed": "form_submit_failed",
    "auth_failed": "login_failed",
    "login_failed": "login_failed",
    "invalid_credentials": "invalid_credentials",
    "portal_unavailable": "portal_unavailable",
    "human_action_required": "portal_unavailable",
}


def _map_error_code(code: Optional[str]) -> str:
    return _ERROR_CODE_MAP.get(code or "", "internal_error")


def _generate_pin() -> str:
    """A UJ-valid 5-digit PIN: numeric, can't start with 0, no two consecutive
    identical digits. (Stored per application as a portal secret once the submit
    is enabled; unused while AUTOMATION_ALLOW_SUBMIT is off.)"""
    digits = [str(random.randint(1, 9))]
    while len(digits) < 5:
        d = str(random.randint(0, 9))
        if d != digits[-1]:
            digits.append(d)
    return "".join(digits)


def _apply_result(application, job, result) -> None:
    """Mutate the application + job from a runtime SubmissionResult. Pure (no
    DB / commit) so it unit-tests without a session."""
    from app.automation.results import RunOutcome

    job.attempts += 1
    if result.outcome is RunOutcome.SUBMITTED:
        job.status = "submitted"
        job.last_error = None
        application.status = "submitted"
        application.submitted_at = datetime.now(timezone.utc)
    elif result.outcome is RunOutcome.FILLED:
        # Filled the whole form but the submit gate is off — left mid-flight.
        job.status = "processing"
        job.last_error = None
        application.status = "processing"
    elif result.outcome is RunOutcome.PAUSED:
        job.status = "processing"
        application.status = "processing"
    else:  # FAILED
        job.status = "failed"
        job.last_error = _map_error_code(
            result.failure.code if result.failure else None
        )
        application.status = "failed"


def _run_real_automation(application_id: uuid.UUID) -> None:
    """Resolve the portal adapter, build the field mapping from the student's
    data, and drive the runtime (submit-gated). Persists the outcome to
    application_jobs / applications. Never raises."""
    import asyncio

    from app.automation.adapters import get_adapter_for_university
    from app.automation.base import PortalCredentials
    from app.automation.mapping import build_field_mapping
    from app.automation.runtime import run_job
    from app.models.academic_record import AcademicRecord
    from app.models.contact import Contact
    from app.models.student_profile import StudentProfile
    from app.models.user import User

    try:
        with Session(get_engine()) as session:
            application = session.get(Application, application_id)
            if not application:
                logger.error("automation: application %s not found", application_id)
                return
            job = _latest_job(session, application_id)
            if not job:
                logger.error("automation: no job for application %s", application_id)
                return

            adapter = get_adapter_for_university(application.university_id)
            if adapter is None:
                logger.error(
                    "automation: no adapter for university %s",
                    application.university_id,
                )
                job.status = "failed"
                job.last_error = "internal_error"
                job.attempts += 1
                application.status = "failed"
                session.add_all([job, application])
                session.commit()
                return

            profile = session.get(StudentProfile, application.student_id)
            record = session.exec(
                select(AcademicRecord)
                .where(AcademicRecord.student_id == application.student_id)
                .order_by(AcademicRecord.year.desc())
                .limit(1)
            ).first()
            contacts = list(
                session.exec(
                    select(Contact).where(
                        Contact.student_id == application.student_id
                    )
                ).all()
            )
            user = session.get(User, profile.user_id) if profile else None
            email = getattr(user, "email", None)

            mapping = build_field_mapping(
                adapter.slug,
                profile=profile,
                application=application,
                academic_record=record,
                contacts=contacts,
                email=email,
            )
            credentials = PortalCredentials(
                username="", password="", extra={"pin": _generate_pin()}
            )

            # transition pending → processing before the (slow) browser run
            job.status = "processing"
            application.status = "processing"
            session.add_all([job, application])
            session.commit()

            result = asyncio.run(
                run_job(
                    adapter,
                    credentials=credentials,
                    mapping=mapping,
                    allow_submit=settings.AUTOMATION_ALLOW_SUBMIT,
                )
            )
            # TODO: upload result.screenshots to Storage and set job.screenshot_url.
            _apply_result(application, job, result)
            logger.info(
                "automation: application %s -> %s (%d screenshots)",
                application_id, result.outcome.value, len(result.screenshots),
            )
            session.add_all([job, application])
            session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("automation: unhandled error for %s: %s", application_id, exc)
        _persist_failure(application_id, "internal_error")


def _latest_job(session, application_id):
    return session.exec(
        select(ApplicationJob)
        .where(ApplicationJob.application_id == application_id)
        .order_by(ApplicationJob.created_at.desc())
        .limit(1)
    ).first()


def _persist_failure(application_id: uuid.UUID, code: str) -> None:
    try:
        with Session(get_engine()) as session:
            job = _latest_job(session, application_id)
            application = session.get(Application, application_id)
            if job:
                job.status = "failed"
                job.last_error = code
                job.attempts += 1
                session.add(job)
            if application:
                application.status = "failed"
                session.add(application)
            session.commit()
    except Exception as inner:  # noqa: BLE001
        logger.exception("automation: failed to persist failure: %s", inner)
