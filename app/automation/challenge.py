"""Email-challenge capability.

Portals deliver mid-run secrets by email: UCT's account-creation OTP, Wits'
temporary ID + password, UP's Application-ID + password. An adapter that hits
such a gate asks its `EmailChallengeSource` for the named values and waits
**in place** — the browser stays open on the gate, because a serialize/resume
round-trip would lose mid-modal state (e.g. UCT's OTP dialog).

Two interchangeable sources, selected by `EMAIL_CHALLENGE_SOURCE`:

- `StudentRelaySource` ("relay", the default): the portal is registered with the
  student's real email. The source records a `portal_challenges` row (flipping
  the job to ``action_required`` so the app prompts), then polls until
  `POST /applications/{id}/challenge` supplies the values.
- `ImapInboxSource` ("imap"): polls an inbox Uniflo controls (the dev/test Gmail
  today; a managed catch-all mailbox later) and parses the values straight out
  of the portal's email — fully unattended.

Adapters depend only on the `EmailChallengeSource` protocol, so the choice is
deployment config, not adapter code.
"""

import asyncio
import email
import email.policy
import imaplib
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Callable, Optional, Protocol

from sqlmodel import Session, select

from app.automation.exceptions import AdapterError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 600.0
DEFAULT_POLL_INTERVAL_S = 5.0


class ChallengeTimeoutError(AdapterError):
    """The expected email values never arrived (or the student never supplied
    them) within the timeout. Retryable — a fresh run re-issues the challenge."""

    code = "challenge_timeout"
    retryable = True


@dataclass
class ChallengeRequest:
    """What the adapter is waiting for. `value_patterns` (field name → regex
    with one capture group) tells `ImapInboxSource` how to parse the portal's
    email; `StudentRelaySource` only needs `expected_fields`."""

    slug: str
    application_id: uuid.UUID
    applicant_email: str
    expected_fields: tuple[str, ...]
    value_patterns: dict[str, str] = field(default_factory=dict)
    sender_hint: Optional[str] = None  # substring of the From header
    subject_hint: Optional[str] = None  # substring of the Subject header
    timeout_s: float = DEFAULT_TIMEOUT_S
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S


class EmailChallengeSource(Protocol):
    async def get_values(self, request: ChallengeRequest) -> dict[str, str]:
        """Block until every `expected_fields` value is available, then return
        them. Raises `ChallengeTimeoutError` when the timeout lapses."""
        ...


# --- IMAP inbox -----------------------------------------------------------------


def _message_text(msg: EmailMessage) -> str:
    """Plain text of a message — text/plain part preferred, tag-stripped HTML as
    the fallback (portal OTP mails are frequently HTML-only)."""
    body = msg.get_body(preferencelist=("plain", "html"))
    if body is None:
        return ""
    content = body.get_content()
    if body.get_content_type() == "text/html":
        content = re.sub(r"<[^>]+>", " ", content)
    return content


def _matches_hints(msg: EmailMessage, request: ChallengeRequest) -> bool:
    to_header = str(msg.get("To", ""))
    if request.applicant_email.lower() not in to_header.lower():
        return False
    if request.sender_hint:
        if request.sender_hint.lower() not in str(msg.get("From", "")).lower():
            return False
    if request.subject_hint:
        if request.subject_hint.lower() not in str(msg.get("Subject", "")).lower():
            return False
    return True


def _extract_values(text: str, request: ChallengeRequest) -> Optional[dict[str, str]]:
    """Apply every value pattern; all expected fields must match or the message
    isn't the one we're waiting for (None, keep polling)."""
    values: dict[str, str] = {}
    for name in request.expected_fields:
        pattern = request.value_patterns.get(name)
        if pattern is None:
            return None
        match = re.search(pattern, text, re.IGNORECASE)
        if match is None:
            return None
        values[name] = match.group(1).strip()
    return values


class ImapInboxSource:
    """Polls an IMAP inbox for the portal's email and parses the values out.
    A fresh connection per poll keeps the loop robust against dropped sessions;
    at a few polls a minute that's well within Gmail's limits."""

    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        *,
        mailbox: str = "INBOX",
        client_factory: Optional[Callable[[str], imaplib.IMAP4]] = None,
    ) -> None:
        self._host = host
        self._user = user
        self._password = password
        self._mailbox = mailbox
        self._client_factory = client_factory or imaplib.IMAP4_SSL

    async def get_values(self, request: ChallengeRequest) -> dict[str, str]:
        started = datetime.now(timezone.utc)
        deadline = asyncio.get_event_loop().time() + request.timeout_s
        while True:
            values = await asyncio.to_thread(self._poll_once, request, started)
            if values is not None:
                logger.info(
                    "challenge values found in inbox for %s (%s)",
                    request.application_id, request.slug,
                )
                return values
            if asyncio.get_event_loop().time() >= deadline:
                raise ChallengeTimeoutError(
                    f"No matching email for {request.slug} within "
                    f"{request.timeout_s:g}s"
                )
            await asyncio.sleep(request.poll_interval_s)

    def _poll_once(
        self, request: ChallengeRequest, started: datetime
    ) -> Optional[dict[str, str]]:
        try:
            client = self._client_factory(self._host)
            try:
                client.login(self._user, self._password)
                client.select(self._mailbox, readonly=True)
                # SINCE is day-granular; the date filter just bounds the scan.
                since = (started - timedelta(days=1)).strftime("%d-%b-%Y")
                criteria = f'(SINCE {since} TO "{request.applicant_email}")'
                status, data = client.search(None, criteria)
                if status != "OK" or not data or not data[0]:
                    return None
                # Newest first — a re-sent OTP supersedes the earlier one.
                for msg_id in reversed(data[0].split()):
                    status, parts = client.fetch(msg_id, "(RFC822)")
                    if status != "OK" or not parts or parts[0] is None:
                        continue
                    msg = email.message_from_bytes(
                        parts[0][1], policy=email.policy.default
                    )
                    if not _matches_hints(msg, request):
                        continue
                    values = _extract_values(_message_text(msg), request)
                    if values is not None:
                        return values
                return None
            finally:
                try:
                    client.logout()
                except Exception:  # noqa: BLE001 — best-effort teardown
                    pass
        except ChallengeTimeoutError:
            raise
        except Exception:  # noqa: BLE001 — transient IMAP errors: keep polling
            logger.warning("IMAP poll failed (will retry)", exc_info=True)
            return None


# --- student relay ----------------------------------------------------------------


class StudentRelaySource:
    """Waits for the student to supply the values in-app. Creates a
    `portal_challenges` row, flips the latest job (and application) to
    ``action_required`` so the frontend prompts, then polls the row until
    `POST /applications/{id}/challenge` fills it. Sessions come from the
    injected factory so the source stays unit-testable without an engine."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    async def get_values(self, request: ChallengeRequest) -> dict[str, str]:
        challenge_id = await asyncio.to_thread(self._open_challenge, request)
        deadline = asyncio.get_event_loop().time() + request.timeout_s
        while True:
            values = await asyncio.to_thread(self._consume_supplied, challenge_id)
            if values is not None:
                logger.info(
                    "challenge values supplied by student for %s (%s)",
                    request.application_id, request.slug,
                )
                return values
            if asyncio.get_event_loop().time() >= deadline:
                raise ChallengeTimeoutError(
                    f"Student did not supply {request.slug} values within "
                    f"{request.timeout_s:g}s"
                )
            await asyncio.sleep(request.poll_interval_s)

    def _open_challenge(self, request: ChallengeRequest) -> uuid.UUID:
        from app.models.application import Application
        from app.models.application_job import ApplicationJob
        from app.models.portal_challenge import PortalChallenge

        with self._session_factory() as session:
            challenge = PortalChallenge(
                application_id=request.application_id,
                portal_slug=request.slug,
                requested_fields=list(request.expected_fields),
            )
            session.add(challenge)
            self._set_status(session, Application, ApplicationJob,
                             request.application_id, "action_required")
            session.commit()
            return challenge.id

    def _consume_supplied(self, challenge_id: uuid.UUID) -> Optional[dict[str, str]]:
        from app.models.application import Application
        from app.models.application_job import ApplicationJob
        from app.models.portal_challenge import PortalChallenge

        with self._session_factory() as session:
            challenge = session.get(PortalChallenge, challenge_id)
            if challenge is None or challenge.supplied_at is None:
                return None
            values = dict(challenge.supplied_values or {})
            # Clear the secrets now they're consumed; supplied_at stays as audit.
            challenge.supplied_values = None
            session.add(challenge)
            self._set_status(session, Application, ApplicationJob,
                             challenge.application_id, "processing")
            session.commit()
            return values

    @staticmethod
    def _set_status(session, application_cls, job_cls, application_id, status) -> None:
        application = session.get(application_cls, application_id)
        if application is not None:
            application.status = status
            session.add(application)
        job = session.exec(
            select(job_cls)
            .where(job_cls.application_id == application_id)
            .order_by(job_cls.created_at.desc())
            .limit(1)
        ).first()
        if job is not None:
            job.status = status
            session.add(job)


def get_challenge_source(
    session_factory: Callable[[], Session],
) -> EmailChallengeSource:
    """The configured source. `relay` is the default; `imap` requires the IMAP
    credentials and falls back to relay (logged) if they're missing, so a
    misconfigured deploy degrades to prompting the student instead of failing."""
    from app.config import settings

    if settings.EMAIL_CHALLENGE_SOURCE.lower() == "imap":
        if settings.IMAP_USER and settings.IMAP_APP_PASSWORD:
            return ImapInboxSource(
                settings.IMAP_HOST, settings.IMAP_USER, settings.IMAP_APP_PASSWORD
            )
        logger.warning(
            "EMAIL_CHALLENGE_SOURCE=imap but IMAP_USER/IMAP_APP_PASSWORD unset — "
            "falling back to the student relay"
        )
    return StudentRelaySource(session_factory)
