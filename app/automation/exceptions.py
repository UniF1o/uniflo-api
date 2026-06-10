"""Adapter exception taxonomy.

Every adapter signals failure by raising an `AdapterError` subclass; the runtime
catches them and turns them into a structured `JobFailure`. Each class carries a
`code` (the stable identifier the frontend copy-map keys off) and a `retryable`
hint. The Phase 2 stub froze a small `JOB_ERROR_CODES` set
(`app/api/automation/background.py`); the `portal_changed` and
`human_action_required` codes below extend it for Phase 3 — reconcile the
canonical set in Task 4 when the failure taxonomy is finalised with Partner A.
"""

from typing import Any, Optional


class AdapterError(Exception):
    """Base for every adapter failure. Subclasses set `code` + `retryable`."""

    code: str = "internal_error"
    retryable: bool = False

    def __init__(self, message: str = "", *, detail: Optional[Any] = None):
        self.message = message or self.__class__.__name__
        self.detail = detail
        super().__init__(self.message)


class AuthFailedError(AdapterError):
    """Credentials rejected by the portal login."""

    code = "invalid_credentials"
    retryable = False


class PortalChangedError(AdapterError):
    """A selector/label wasn't found or the page shape was unexpected — the
    canary for portal drift. Carries the selector/label that broke so health
    monitoring (Task 6) can point at the exact breakage."""

    code = "portal_changed"
    retryable = False

    def __init__(
        self,
        message: str = "",
        *,
        selector: Optional[str] = None,
        detail: Optional[Any] = None,
    ):
        super().__init__(message, detail=detail)
        self.selector = selector


class ValidationFailedError(AdapterError):
    """The portal rejected our submission with a field-level validation error
    (e.g. 'ID number invalid'). Not retryable without different data."""

    code = "form_submit_failed"
    retryable = False

    def __init__(
        self,
        message: str = "",
        *,
        field: Optional[str] = None,
        detail: Optional[Any] = None,
    ):
        super().__init__(message, detail=detail)
        self.field = field


class HumanActionRequiredError(AdapterError):
    """The run hit a captcha / OTP / MFA challenge that can't be cleared in this
    pass. The runtime pauses: it serialises the browser context and stores it
    against a resume token so a later run (human-in-the-loop, or an automated
    OCR/inbox solve) can continue. `resume_token`/`browser_state` are filled by
    the runtime if the adapter doesn't supply them."""

    code = "human_action_required"
    retryable = False

    def __init__(
        self,
        reason: str,
        *,
        resume_token: Optional[str] = None,
        browser_state: Optional[dict] = None,
        detail: Optional[Any] = None,
    ):
        super().__init__(reason, detail=detail)
        self.reason = reason
        self.resume_token = resume_token
        self.browser_state = browser_state


class CaptchaUnsolvedError(AdapterError):
    """The vision model couldn't produce a valid reading of a captcha image
    after the configured attempts. Retryable — a fresh run gets a fresh
    captcha (and the adapter may refresh the image between solve calls)."""

    code = "captcha_unsolved"
    retryable = True


class UnknownAdapterError(AdapterError):
    """Catch-all for anything we didn't anticipate. Retryable — the next attempt
    might land on a transient hiccup rather than a real defect."""

    code = "internal_error"
    retryable = True
