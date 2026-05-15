import logging
import random
import time
import uuid
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.config import settings
from app.db import get_engine
from app.models.application import Application
from app.models.application_job import ApplicationJob

logger = logging.getLogger(__name__)


def process_application(application_id: uuid.UUID) -> None:
    """Phase 2 stub — simulates the automation layer so the dashboard can
    show status transitions end to end. Phase 3 replaces this with real
    Playwright adapter calls."""
    if not settings.FAKE_AUTOMATION:
        logger.info(
            "process_application: FAKE_AUTOMATION disabled — skipping stub for %s",
            application_id,
        )
        return
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
                job.last_error = "Portal timed out while filling form (fake)"
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
                    job.last_error = f"internal: {type(exc).__name__}"
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
