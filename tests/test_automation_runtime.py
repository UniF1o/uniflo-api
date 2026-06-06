import asyncio
import uuid

import pytest

from app.automation.base import FieldMapping, PortalCredentials, UniversityAdapter
from app.automation.exceptions import (
    AuthFailedError,
    HumanActionRequiredError,
    PortalChangedError,
    ValidationFailedError,
)
from app.automation.results import RunOutcome, SubmissionConfirmation
from app.automation.runtime import (
    STEPS,
    InMemoryPauseStore,
    _next_step,
    drive,
)

CREDS = PortalCredentials(username="u", password="p")
MAPPING = FieldMapping(values={"first_name": "Test"})


class FakeContext:
    def __init__(self, storage=None):
        self._storage = storage or {"cookies": [], "origins": []}

    async def storage_state(self, **_):
        return self._storage


class FakePage:
    """Stands in for a Playwright Page in unit tests — no real browser."""

    def __init__(self):
        self.context = FakeContext()
        self.shots = 0

    async def screenshot(self, **_):
        self.shots += 1
        return b"\x89PNG-fake"


class FakeAdapter(UniversityAdapter):
    university_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    slug = "fake"

    def __init__(self, *, fail_on=None, error=None, pause_on=None, delay=0.0):
        self.calls: list[str] = []
        self.fail_on = fail_on
        self.error = error
        self.pause_on = pause_on
        self.delay = delay

    async def _record(self, name):
        self.calls.append(name)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.pause_on == name:
            raise HumanActionRequiredError("captcha challenge")
        if self.fail_on == name and self.error is not None:
            raise self.error

    async def login(self, page, credentials):
        await self._record("login")

    async def fill_form(self, page, mapping):
        await self._record("fill_form")

    async def upload_documents(self, page, documents):
        await self._record("upload_documents")

    async def submit(self, page):
        await self._record("submit")

    async def verify_submission(self, page):
        await self._record("verify_submission")
        return SubmissionConfirmation(reference="REF123", marker="Application submitted")


async def _drive(adapter, page=None, **kw):
    return await drive(
        adapter,
        page or FakePage(),
        credentials=CREDS,
        mapping=MAPPING,
        **kw,
    )


# --- happy path ----------------------------------------------------------------

async def test_full_run_succeeds():
    adapter = FakeAdapter()
    page = FakePage()
    result = await _drive(adapter, page)

    assert result.outcome is RunOutcome.SUBMITTED
    assert result.ok
    assert result.confirmation.reference == "REF123"
    assert adapter.calls == list(STEPS)
    # one screenshot per completed step
    assert [s.name for s in result.screenshots] == list(STEPS)
    assert page.shots == len(STEPS)


# --- no-submit safety gate -----------------------------------------------------

async def test_no_submit_gate_stops_before_submit():
    adapter = FakeAdapter()
    result = await _drive(adapter, allow_submit=False)
    assert result.outcome is RunOutcome.FILLED
    assert adapter.calls == ["login", "fill_form", "upload_documents"]
    assert "submit" not in adapter.calls
    assert result.confirmation is None


async def test_allow_submit_runs_full_pipeline():
    adapter = FakeAdapter()
    result = await _drive(adapter, allow_submit=True)
    assert result.outcome is RunOutcome.SUBMITTED
    assert adapter.calls == [
        "login", "fill_form", "upload_documents", "submit", "verify_submission",
    ]


# --- failures map to structured JobFailure -------------------------------------

async def test_auth_failure_stops_at_login():
    adapter = FakeAdapter(fail_on="login", error=AuthFailedError("rejected"))
    result = await _drive(adapter)

    assert result.outcome is RunOutcome.FAILED
    assert result.failure.code == "invalid_credentials"
    assert result.failure.retryable is False
    assert adapter.calls == ["login"]
    assert result.screenshots[-1].name == "login__failed"


async def test_portal_changed_carries_selector():
    adapter = FakeAdapter(
        fail_on="fill_form",
        error=PortalChangedError("missing field", selector="role=textbox[name=ID]"),
    )
    result = await _drive(adapter)

    assert result.outcome is RunOutcome.FAILED
    assert result.failure.code == "portal_changed"
    assert result.failure.selector == "role=textbox[name=ID]"
    assert adapter.calls == ["login", "fill_form"]


async def test_validation_failure_carries_field():
    adapter = FakeAdapter(
        fail_on="submit",
        error=ValidationFailedError("bad id", field="id_number"),
    )
    result = await _drive(adapter)

    assert result.failure.code == "form_submit_failed"
    assert result.failure.field == "id_number"


async def test_unexpected_error_becomes_internal_error():
    adapter = FakeAdapter(fail_on="submit", error=ValueError("boom"))
    result = await _drive(adapter)

    assert result.outcome is RunOutcome.FAILED
    assert result.failure.code == "internal_error"
    assert result.failure.retryable is True


# --- timeout -------------------------------------------------------------------

async def test_timeout_returns_timeout_failure():
    adapter = FakeAdapter(delay=0.2)  # each step sleeps 0.2s
    result = await _drive(adapter, timeout_s=0.01)

    assert result.outcome is RunOutcome.FAILED
    assert result.failure.code == "timeout"
    assert result.failure.retryable is True


# --- pause and resume ----------------------------------------------------------

async def test_human_action_pauses_and_persists_state():
    adapter = FakeAdapter(pause_on="login")
    store = InMemoryPauseStore()
    page = FakePage()
    result = await _drive(adapter, page, pause_store=store)

    assert result.outcome is RunOutcome.PAUSED
    assert result.resume_token
    saved = store.load(result.resume_token)
    assert saved is not None
    assert saved["step"] == "login"
    assert saved["slug"] == "fake"
    assert saved["storage_state"] == {"cookies": [], "origins": []}
    assert result.screenshots[-1].name == "login__paused"


async def test_resume_continues_from_next_step():
    # Simulate a resume after a pause at login: drive from the next step.
    adapter = FakeAdapter()
    resume_at = _next_step("login")
    result = await _drive(adapter, start_at=resume_at)

    assert result.outcome is RunOutcome.SUBMITTED
    # login is NOT re-run on resume
    assert adapter.calls == ["fill_form", "upload_documents", "submit", "verify_submission"]


def test_next_step_walks_the_pipeline():
    assert _next_step("login") == "fill_form"
    assert _next_step("submit") == "verify_submission"
    assert _next_step("verify_submission") is None


# --- the base class is genuinely abstract --------------------------------------

def test_university_adapter_is_abstract():
    with pytest.raises(TypeError):
        UniversityAdapter()  # type: ignore[abstract]
