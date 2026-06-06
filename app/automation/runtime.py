"""The runtime that drives an adapter.

`drive(adapter, page, ...)` is the testable core: it calls the adapter's five
steps in order against a given `page`, captures a screenshot after each, applies
a hard timeout, and converts any `AdapterError` into a structured
`SubmissionResult` — it never raises. `run_job` / `resume_job` wrap it with the
Playwright browser lifecycle (and so need a real browser; they aren't unit
tested — that's the Task 4 integration).

Pause-and-resume is built in from day one: when a step raises
`HumanActionRequiredError`, the runtime serialises the browser context's storage
state to a `PauseStore` against a resume token and returns a PAUSED result.
`resume_job(token)` rehydrates the context and continues from the next step. For
MVP the captcha/OTP portals solve their challenges inline (OCR + inbox-read, per
the Phase 3 decision), so nothing raises this yet — the path exists so a
human-in-the-loop handoff is a small lift later, not a rewrite.
"""

import asyncio
import logging
import uuid
from typing import Optional, Protocol

from playwright.async_api import Page, async_playwright

from app.automation.base import (
    DocumentRef,
    FieldMapping,
    PortalCredentials,
    UniversityAdapter,
)
from app.automation.exceptions import AdapterError, HumanActionRequiredError
from app.automation.results import (
    JobFailure,
    RunOutcome,
    Screenshot,
    SubmissionResult,
)

logger = logging.getLogger(__name__)

# Hard cap per application run.
DEFAULT_TIMEOUT_S = 15 * 60

# The adapter pipeline, in order. Named so resume can restart at the right step.
STEPS: tuple[str, ...] = (
    "login",
    "fill_form",
    "upload_documents",
    "submit",
    "verify_submission",
)

# The pipeline with the final submit gated off (the no-submit safety mode): fill
# everything and stop on the portal's final/agreement page. Used while building +
# verifying adapters, before a real consenting student is ready to submit.
STEPS_NO_SUBMIT: tuple[str, ...] = ("login", "fill_form", "upload_documents")


def _next_step(step: str) -> Optional[str]:
    i = STEPS.index(step)
    return STEPS[i + 1] if i + 1 < len(STEPS) else None


class PauseStore(Protocol):
    """Persists a paused browser context so a later run can resume it. Task 2
    ships only the in-memory impl; a DB-backed `paused_jobs` store is a later
    lift — the resume entry point already exists for it to plug into."""

    def save(
        self, resume_token: str, *, slug: str, step: str, storage_state: Optional[dict]
    ) -> None: ...

    def load(self, resume_token: str) -> Optional[dict]: ...


class InMemoryPauseStore:
    """Default `PauseStore` — process-local, for tests and single-process dev."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def save(
        self, resume_token: str, *, slug: str, step: str, storage_state: Optional[dict]
    ) -> None:
        self._store[resume_token] = {
            "slug": slug,
            "step": step,
            "storage_state": storage_state,
        }

    def load(self, resume_token: str) -> Optional[dict]:
        return self._store.get(resume_token)


async def _safe_screenshot(
    page: Page, name: str, screenshots: list[Screenshot]
) -> None:
    """Best-effort screenshot — never let a capture failure sink the run."""
    try:
        data = await page.screenshot()
        screenshots.append(Screenshot(name=name, data=data))
    except Exception:  # noqa: BLE001 — debugging aid only
        logger.warning("screenshot capture failed at %s", name, exc_info=True)


async def _call_step(
    adapter: UniversityAdapter,
    step: str,
    page: Page,
    credentials: PortalCredentials,
    mapping: FieldMapping,
    documents: list[DocumentRef],
):
    if step == "login":
        return await adapter.login(page, credentials)
    if step == "fill_form":
        return await adapter.fill_form(page, mapping)
    if step == "upload_documents":
        return await adapter.upload_documents(page, documents)
    if step == "submit":
        return await adapter.submit(page)
    if step == "verify_submission":
        return await adapter.verify_submission(page)
    raise ValueError(f"unknown step {step!r}")


async def _run_steps(
    adapter: UniversityAdapter,
    page: Page,
    *,
    credentials: PortalCredentials,
    mapping: FieldMapping,
    documents: list[DocumentRef],
    pause_store: Optional[PauseStore],
    start_at: str = "login",
    pipeline: tuple[str, ...] = STEPS,
) -> SubmissionResult:
    screenshots: list[Screenshot] = []
    confirmation = None
    step = start_at
    submitted = "submit" in pipeline
    try:
        for step in pipeline[pipeline.index(start_at):]:
            result = await _call_step(
                adapter, step, page, credentials, mapping, documents
            )
            if step == "verify_submission":
                confirmation = result
            await _safe_screenshot(page, step, screenshots)
        return SubmissionResult(
            # Stopped before submit (no-submit gate) → FILLED, not SUBMITTED.
            outcome=RunOutcome.SUBMITTED if submitted else RunOutcome.FILLED,
            confirmation=confirmation,
            screenshots=screenshots,
        )
    except HumanActionRequiredError as exc:
        token = exc.resume_token or uuid.uuid4().hex
        state = exc.browser_state
        if state is None:
            try:
                state = await page.context.storage_state()
            except Exception:  # noqa: BLE001
                logger.warning("could not capture storage state on pause", exc_info=True)
        if pause_store is not None:
            pause_store.save(token, slug=adapter.slug, step=step, storage_state=state)
        await _safe_screenshot(page, f"{step}__paused", screenshots)
        logger.info("run paused for human action at %s (%s)", step, adapter.slug)
        return SubmissionResult(
            outcome=RunOutcome.PAUSED,
            resume_token=token,
            screenshots=screenshots,
            failure=JobFailure(code=exc.code, message=exc.reason, retryable=False),
        )
    except AdapterError as exc:
        await _safe_screenshot(page, f"{step}__failed", screenshots)
        logger.warning("adapter failed at %s: %s (%s)", step, exc.code, adapter.slug)
        return SubmissionResult(
            outcome=RunOutcome.FAILED,
            screenshots=screenshots,
            failure=JobFailure(
                code=exc.code,
                message=exc.message,
                retryable=exc.retryable,
                selector=getattr(exc, "selector", None),
                field=getattr(exc, "field", None),
            ),
        )
    except Exception as exc:  # noqa: BLE001 — convert anything unanticipated
        await _safe_screenshot(page, f"{step}__error", screenshots)
        logger.exception("unexpected error at %s (%s)", step, adapter.slug)
        return SubmissionResult(
            outcome=RunOutcome.FAILED,
            screenshots=screenshots,
            failure=JobFailure(
                code="internal_error", message=str(exc), retryable=True
            ),
        )


async def drive(
    adapter: UniversityAdapter,
    page: Page,
    *,
    credentials: PortalCredentials,
    mapping: FieldMapping,
    documents: Optional[list[DocumentRef]] = None,
    pause_store: Optional[PauseStore] = None,
    start_at: str = "login",
    allow_submit: bool = True,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> SubmissionResult:
    """Run the pipeline against an existing page under a hard timeout. Never
    raises — returns a `SubmissionResult` describing the outcome. With
    `allow_submit=False` the final submit/verify steps are skipped (the outcome
    is `FILLED`) — the safety gate that lets us drive real portals end-to-end
    without submitting until a consenting student is ready."""
    pipeline = STEPS if allow_submit else STEPS_NO_SUBMIT
    try:
        return await asyncio.wait_for(
            _run_steps(
                adapter,
                page,
                credentials=credentials,
                mapping=mapping,
                documents=documents or [],
                pause_store=pause_store,
                start_at=start_at,
                pipeline=pipeline,
            ),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        logger.error("run exceeded %ss for %s", timeout_s, adapter.slug)
        return SubmissionResult(
            outcome=RunOutcome.FAILED,
            failure=JobFailure(
                code="timeout",
                message=f"Run exceeded the {timeout_s:g}s cap",
                retryable=True,
            ),
        )


async def run_job(
    adapter: UniversityAdapter,
    *,
    credentials: PortalCredentials,
    mapping: FieldMapping,
    documents: Optional[list[DocumentRef]] = None,
    pause_store: Optional[PauseStore] = None,
    headless: bool = True,
    allow_submit: bool = True,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> SubmissionResult:
    """Production entry: spin up a fresh Chromium context, drive the adapter,
    tear the browser down cleanly even on failure. `allow_submit=False` runs the
    no-submit safety gate (fills the form, stops before submit)."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context()
        try:
            page = await context.new_page()
            return await drive(
                adapter,
                page,
                credentials=credentials,
                mapping=mapping,
                documents=documents,
                pause_store=pause_store,
                allow_submit=allow_submit,
                timeout_s=timeout_s,
            )
        finally:
            await context.close()
            await browser.close()


async def resume_job(
    adapter: UniversityAdapter,
    resume_token: str,
    *,
    credentials: PortalCredentials,
    mapping: FieldMapping,
    pause_store: PauseStore,
    documents: Optional[list[DocumentRef]] = None,
    headless: bool = True,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> SubmissionResult:
    """Rehydrate a paused run from its stored context and continue from the step
    after the one that paused. (Browser-backed; exercised by Task 4 integration,
    not the unit tests — those drive the resume path through `drive(start_at=…)`.)"""
    saved = pause_store.load(resume_token)
    if saved is None:
        raise KeyError(f"no paused job for token {resume_token!r}")
    resume_at = _next_step(saved["step"])
    if resume_at is None:
        # Paused on the final step — nothing left to do but re-verify.
        resume_at = "verify_submission"
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(storage_state=saved.get("storage_state"))
        try:
            page = await context.new_page()
            return await drive(
                adapter,
                page,
                credentials=credentials,
                mapping=mapping,
                documents=documents,
                pause_store=pause_store,
                start_at=resume_at,
                timeout_s=timeout_s,
            )
        finally:
            await context.close()
            await browser.close()
