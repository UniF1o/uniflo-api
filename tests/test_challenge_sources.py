"""Unit tests for the email-challenge capability (`app/automation/challenge.py`).

`ImapInboxSource` is driven through an injected fake IMAP client; the
`StudentRelaySource` through a mocked session factory — no real inbox or DB.
"""

import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from unittest.mock import MagicMock

import pytest

from app.automation.challenge import (
    ChallengeRequest,
    ChallengeTimeoutError,
    ImapInboxSource,
    StudentRelaySource,
    _extract_values,
    _matches_hints,
    _message_text,
    get_challenge_source,
)

APPLICATION_ID = uuid.uuid4()


def make_request(**overrides) -> ChallengeRequest:
    defaults = dict(
        slug="uct",
        application_id=APPLICATION_ID,
        applicant_email="student@example.com",
        expected_fields=("otp",),
        value_patterns={"otp": r"verification code is\s*(\d{6})"},
        sender_hint="uct.ac.za",
        timeout_s=0.0,  # first unsuccessful poll times out — keeps tests fast
        poll_interval_s=0.0,
    )
    defaults.update(overrides)
    return ChallengeRequest(**defaults)


def make_email(
    to="student@example.com",
    sender="noreply@uct.ac.za",
    subject="Confirm Email Address",
    body="Your verification code is 123456. It is valid for 15 minutes.",
    html=False,
) -> EmailMessage:
    msg = EmailMessage()
    msg["To"] = to
    msg["From"] = sender
    msg["Subject"] = subject
    if html:
        msg.add_alternative(f"<html><body><p>{body}</p></body></html>", subtype="html")
    else:
        msg.set_content(body)
    return msg


# --- parsing helpers ---------------------------------------------------------------


def test_extract_values_pulls_named_groups():
    values = _extract_values("Your verification code is 654321.", make_request())
    assert values == {"otp": "654321"}


def test_extract_values_requires_every_expected_field():
    request = make_request(
        expected_fields=("temp_id", "password"),
        value_patterns={
            "temp_id": r"Temporary ID:\s*(T\d+)",
            "password": r"Password:\s*(\S+)",
        },
    )
    assert _extract_values("Temporary ID: T12345", request) is None
    values = _extract_values("Temporary ID: T12345\nPassword: abcDEF1!", request)
    assert values == {"temp_id": "T12345", "password": "abcDEF1!"}


def test_extract_values_without_pattern_is_none():
    request = make_request(value_patterns={})
    assert _extract_values("code is 123456", request) is None


def test_matches_hints_filters_recipient_sender_and_subject():
    request = make_request(subject_hint="confirm email")
    assert _matches_hints(make_email(), request)
    assert not _matches_hints(make_email(to="other@example.com"), request)
    assert not _matches_hints(make_email(sender="noreply@wits.ac.za"), request)
    assert not _matches_hints(make_email(subject="Marketing"), request)


def test_message_text_strips_html():
    text = _message_text(make_email(html=True))
    assert "verification code is 123456" in text
    assert "<p>" not in text


# --- ImapInboxSource ---------------------------------------------------------------


class FakeImap:
    """Stands in for imaplib.IMAP4_SSL: serves a canned list of messages."""

    def __init__(self, messages):
        self._messages = messages

    def login(self, user, password):
        return "OK", []

    def select(self, mailbox, readonly=False):
        return "OK", []

    def search(self, charset, criteria):
        ids = b" ".join(str(i + 1).encode() for i in range(len(self._messages)))
        return "OK", [ids]

    def fetch(self, msg_id, parts):
        msg = self._messages[int(msg_id) - 1]
        return "OK", [(b"1 (RFC822)", msg.as_bytes())]

    def logout(self):
        return "BYE", []


def make_imap_source(messages):
    return ImapInboxSource(
        "imap.example.com", "inbox@uniflo.test", "app-password",
        client_factory=lambda host: FakeImap(messages),
    )


async def test_imap_source_returns_values_from_matching_mail():
    source = make_imap_source([make_email()])
    values = await source.get_values(make_request(timeout_s=5.0))
    assert values == {"otp": "123456"}


async def test_imap_source_prefers_newest_matching_mail():
    older = make_email(body="Your verification code is 111111.")
    newer = make_email(body="Your verification code is 222222.")
    source = make_imap_source([older, newer])
    values = await source.get_values(make_request(timeout_s=5.0))
    assert values == {"otp": "222222"}


async def test_imap_source_ignores_other_recipients_then_times_out():
    source = make_imap_source([make_email(to="someone-else@example.com")])
    with pytest.raises(ChallengeTimeoutError):
        await source.get_values(make_request())


async def test_imap_source_survives_connection_errors():
    def flaky_factory(host):
        raise ConnectionError("boom")

    source = ImapInboxSource(
        "imap.example.com", "inbox@uniflo.test", "pw", client_factory=flaky_factory
    )
    with pytest.raises(ChallengeTimeoutError):
        await source.get_values(make_request())


# --- StudentRelaySource --------------------------------------------------------------


def make_session_factory(session):
    factory = MagicMock()
    factory.return_value.__enter__ = MagicMock(return_value=session)
    factory.return_value.__exit__ = MagicMock(return_value=False)
    return factory


def test_open_challenge_creates_row_and_flags_action_required():
    session = MagicMock()
    application = MagicMock()
    job = MagicMock()
    session.get.side_effect = lambda cls, _id: application
    session.exec.return_value.first.return_value = job

    source = StudentRelaySource(make_session_factory(session))
    challenge_id = source._open_challenge(make_request())

    assert isinstance(challenge_id, uuid.UUID)
    added = session.add.call_args_list[0].args[0]
    assert added.application_id == APPLICATION_ID
    assert added.portal_slug == "uct"
    assert added.requested_fields == ["otp"]
    assert application.status == "action_required"
    assert job.status == "action_required"
    session.commit.assert_called_once()


def test_consume_supplied_returns_values_and_clears_them():
    challenge = MagicMock()
    challenge.application_id = APPLICATION_ID
    challenge.supplied_at = datetime.now(timezone.utc)
    challenge.supplied_values = {"otp": "123456"}
    application = MagicMock()
    job = MagicMock()

    session = MagicMock()
    session.get.side_effect = (
        lambda cls, _id: challenge if cls.__name__ == "PortalChallenge" else application
    )
    session.exec.return_value.first.return_value = job

    source = StudentRelaySource(make_session_factory(session))
    values = source._consume_supplied(uuid.uuid4())

    assert values == {"otp": "123456"}
    assert challenge.supplied_values is None  # secrets cleared once consumed
    assert application.status == "processing"
    assert job.status == "processing"


def test_consume_supplied_is_none_while_unanswered():
    challenge = MagicMock()
    challenge.supplied_at = None
    session = MagicMock()
    session.get.return_value = challenge

    source = StudentRelaySource(make_session_factory(session))
    assert source._consume_supplied(uuid.uuid4()) is None
    session.commit.assert_not_called()


async def test_relay_source_times_out_without_an_answer():
    challenge = MagicMock()
    challenge.supplied_at = None
    session = MagicMock()
    session.get.return_value = challenge
    session.exec.return_value.first.return_value = MagicMock()

    source = StudentRelaySource(make_session_factory(session))
    with pytest.raises(ChallengeTimeoutError):
        await source.get_values(make_request())


# --- source selection ---------------------------------------------------------------


def test_get_challenge_source_defaults_to_relay(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "EMAIL_CHALLENGE_SOURCE", "relay")
    source = get_challenge_source(MagicMock())
    assert isinstance(source, StudentRelaySource)


def test_get_challenge_source_imap_when_configured(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "EMAIL_CHALLENGE_SOURCE", "imap")
    monkeypatch.setattr(settings, "IMAP_USER", "inbox@uniflo.test")
    monkeypatch.setattr(settings, "IMAP_APP_PASSWORD", "app-password")
    source = get_challenge_source(MagicMock())
    assert isinstance(source, ImapInboxSource)


def test_get_challenge_source_imap_without_creds_falls_back(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "EMAIL_CHALLENGE_SOURCE", "imap")
    monkeypatch.setattr(settings, "IMAP_USER", None)
    monkeypatch.setattr(settings, "IMAP_APP_PASSWORD", None)
    source = get_challenge_source(MagicMock())
    assert isinstance(source, StudentRelaySource)
