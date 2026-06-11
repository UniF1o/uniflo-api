import hashlib
import hmac
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
    "consent_required",
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
    # Email-challenge values (OTP / emailed login) never arrived — retryable.
    "challenge_timeout": "timeout",
    # Vision model couldn't read the portal captcha — retryable (fresh captcha).
    "captcha_unsolved": "portal_unavailable",
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


def _ai_configured() -> bool:
    """Whether an API key is set for the configured AI provider."""
    provider = (settings.AI_PROVIDER or "gemini").lower()
    if provider == "gemini":
        return bool(settings.GEMINI_API_KEY)
    if provider == "anthropic":
        return bool(settings.ANTHROPIC_API_KEY)
    return False


def _portal_form_schema(adapter):
    """Adapter's field catalog -> the AI layer's PortalFormSchema."""
    import uuid as _uuid

    from app.ai.schemas import PortalField, PortalFormSchema

    raw = adapter.form_schema()
    fields = [
        PortalField(
            field_id=f["field_id"],
            label=f.get("label", ""),
            type=f.get("type", "text"),
            required=f.get("required", False),
            options=f.get("options"),
            help_text=f.get("help_text"),
        )
        for f in raw.get("fields", [])
    ]
    return PortalFormSchema(
        university_id=_uuid.UUID(str(raw["university_id"])),
        slug=raw["slug"],
        fields=fields,
    )


def _generate_ai_mapping(session, application, adapter, profile, academic_record) -> None:
    """Best-effort: produce the AI field mapping for Partner-A's review screen and
    persist it to `field_mappings`. Skipped (logged) if AI isn't configured or the
    adapter exposes no form schema; a failure never sinks the run (the bot fills
    via the deterministic mapper either way)."""
    if not _ai_configured() or not hasattr(adapter, "form_schema"):
        logger.info("AI mapping skipped for %s (AI not configured)", application.id)
        return
    try:
        import asyncio

        from app.ai.client import AIClient
        from app.ai.field_mapping import (
            build_profile_payload,
            map_application_to_portal,
            persist_field_mapping,
        )

        client = AIClient.from_env()
        form = _portal_form_schema(adapter)
        payload = build_profile_payload(
            profile, [academic_record] if academic_record else None
        )
        response = asyncio.run(
            map_application_to_portal(
                application_id=application.id, profile=payload, form=form, client=client
            )
        )
        persist_field_mapping(session, response)
        session.commit()
        logger.info(
            "AI field mapping persisted for %s (overall_confidence=%.2f)",
            application.id, response.overall_confidence,
        )
    except Exception:  # noqa: BLE001 — review-screen data is non-critical to the run
        logger.warning("AI field mapping generation failed (continuing)", exc_info=True)


def _consent_gate(application) -> tuple[bool, bool]:
    """(can_run, allow_submit) from the recorded consent + the submit setting.
    The bot won't even fill the form (which ticks POPI) without POPI consent, and
    won't submit without the application-agreement consent — both surfaced to and
    accepted by the student upstream (the bot ticks only what it was told to)."""
    can_run = application.popi_consent_at is not None
    allow_submit = (
        settings.AUTOMATION_ALLOW_SUBMIT
        and application.agreement_consent_at is not None
    )
    return can_run, allow_submit


def derive_portal_pin(application_id: uuid.UUID) -> str:
    """A UJ-valid 5-digit PIN (numeric, can't start with 0, no two consecutive
    identical digits) derived **deterministically** from the application id + a
    server secret. Deterministic so a retry/resume reuses the same PIN (the PIN
    is the student's portal login after submit) without persisting it in the DB;
    recompute it any time from the same secret."""
    secret = settings.AUTOMATION_PIN_SECRET or settings.SUPABASE_JWT_SECRET or "uniflo"
    digest = hmac.new(
        secret.encode(), str(application_id).encode(), hashlib.sha256
    ).digest()
    digits: list[str] = []
    for byte in digest:
        if len(digits) >= 5:
            break
        if not digits:
            digits.append(str(byte % 9 + 1))  # 1-9 (can't start with 0)
        else:
            d = byte % 10
            if str(d) == digits[-1]:  # no two consecutive identical digits
                d = (d + 1) % 10
            digits.append(str(d))
    return "".join(digits)


def derive_portal_credentials(seed_id: uuid.UUID, slug: str) -> tuple[str, str]:
    """Deterministic per-student portal credentials (UCT-style self-created
    accounts), HMAC-derived like `derive_portal_pin` — nothing persisted, any
    retry recomputes the same pair. Keyed on the **student profile id** (the
    portal account is per-student, reused across applications/runs).

    Satisfies UCT's rules: username >=10 chars from [a-z0-9.] and not an email;
    password >=16 chars with upper + lower + digit + special guaranteed by the
    prefix. Generic enough for other portals (Wits permanent password later)."""
    secret = settings.AUTOMATION_PIN_SECRET or settings.SUPABASE_JWT_SECRET or "uniflo"

    def digest(purpose: str) -> str:
        return hmac.new(
            secret.encode(), f"{seed_id}:{slug}:{purpose}".encode(), hashlib.sha256
        ).hexdigest()

    # No product branding in portal usernames (user rule, 2026-06-10).
    username = f"apply.{digest('username')[:10]}"
    password = f"Uf!2{digest('password')[:16]}"
    return username, password


def _wire_challenge_source(adapter, application_id: uuid.UUID, email) -> None:
    """Hand the configured EmailChallengeSource to adapters that take one (UCT's
    OTP; Wits/UP login deliveries later). The relay source polls the DB, so it
    gets a fresh-session factory."""
    if not hasattr(adapter, "set_challenge_source"):
        return
    from app.automation.challenge import get_challenge_source

    source = get_challenge_source(lambda: Session(get_engine()))
    adapter.set_challenge_source(
        source, application_id=application_id, applicant_email=email or ""
    )


def _account_extra(profile, application, email) -> dict:
    """Account-creation fields for portals with self-created accounts (UCT,
    Wits' Create Application ID — which also wants title/gender/phone) —
    passed via credentials.extra because the runtime hands the mapping to
    fill_form only after login()."""
    extra: dict[str, str] = {}
    if profile is not None:
        for key in ("first_name", "middle_names", "last_name", "id_number",
                    "title", "gender", "phone"):
            if value := getattr(profile, key, None):
                extra[key] = value
        if getattr(profile, "date_of_birth", None):
            extra["date_of_birth"] = profile.date_of_birth.strftime("%d/%m/%Y")
    if email:
        extra["email"] = email
    year = getattr(application, "application_year", None)
    if year:
        extra["application_year"] = str(year)
    return extra


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

    from app.automation.adapters import (
        get_adapter,
        get_adapter_for_university,
        slug_for_website,
    )
    from app.automation.base import PortalCredentials
    from app.automation.mapping import build_field_mapping
    from app.automation.runtime import run_job
    from app.automation.screenshots import upload_screenshots
    from app.models.academic_record import AcademicRecord
    from app.models.contact import Contact
    from app.models.student_profile import StudentProfile
    from app.models.university import University
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

            # Pinned-id resolution (UJ), else by the university row's website
            # domain (seeded row ids are uuid4 — nothing stable to pin).
            adapter = get_adapter_for_university(application.university_id)
            if adapter is None:
                university = session.get(University, application.university_id)
                slug = slug_for_website(getattr(university, "website", None))
                adapter = get_adapter(slug) if slug else None
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

            # Consent gate: don't tick POPI / fill the form without POPI consent;
            # submit only when the agreement consent is also recorded.
            can_run, allow_submit = _consent_gate(application)
            if not can_run:
                logger.info(
                    "automation: %s blocked — POPI consent not recorded",
                    application_id,
                )
                job.status = "failed"
                job.last_error = "consent_required"
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
            # Produce + persist the AI mapping for the review screen (best-effort;
            # the bot fills via the deterministic mapping above regardless).
            _generate_ai_mapping(session, application, adapter, profile, record)
            username, password = derive_portal_credentials(
                profile.id if profile else application.student_id, adapter.slug
            )
            extra = {"pin": derive_portal_pin(application_id)}
            extra.update(_account_extra(profile, application, email))
            # Wits orders its indemnity step before document uploads — the
            # adapter accepts it only when this consent is recorded.
            if application.agreement_consent_at is not None:
                extra["agreement_consented"] = "true"
            credentials = PortalCredentials(
                username=username, password=password, extra=extra
            )
            # Email-challenge wiring (UCT OTP etc.) for adapters that take it.
            _wire_challenge_source(adapter, application_id, email)

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
                    allow_submit=allow_submit,
                )
            )
            _apply_result(application, job, result)
            # upload the per-step screenshots and keep the primary (final/failure)
            # one's storage path on the job (signed for the dashboard on read).
            primary = upload_screenshots(application_id, job.id, result.screenshots)
            if primary:
                job.screenshot_url = primary
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
