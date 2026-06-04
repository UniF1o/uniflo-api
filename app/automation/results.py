"""Structured outputs of a runtime run.

The runtime never raises out of a drive; it always returns a `SubmissionResult`
describing what happened (submitted / failed / paused), the confirmation marker,
any failure, and the screenshots captured along the way.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RunOutcome(str, Enum):
    SUBMITTED = "submitted"
    FAILED = "failed"
    # Maps to the application_jobs."paused_human_action" status the plan adds.
    PAUSED = "paused_human_action"


@dataclass
class SubmissionConfirmation:
    """What `verify_submission()` read off the post-submit page — the success
    marker we key `verify_submission()` off. `reference` is the applicant /
    student / reference number; `marker` is the success text observed."""

    reference: Optional[str] = None
    marker: Optional[str] = None
    raw: Optional[dict] = None


@dataclass
class JobFailure:
    """A failure flattened for persistence into `application_jobs`. `code` is the
    stable identifier; `retryable` tells the retry path whether re-running could
    help. `selector`/`field` carry extra context for drift / validation errors."""

    code: str
    message: str
    retryable: bool = False
    selector: Optional[str] = None
    field: Optional[str] = None


@dataclass
class Screenshot:
    """A debugging screenshot captured after a step. `name` is the step (or
    `<step>__failed` / `<step>__paused`); `data` is raw PNG bytes the runtime
    later uploads to Storage and records on `application_jobs.screenshot_url`."""

    name: str
    data: bytes


@dataclass
class SubmissionResult:
    outcome: RunOutcome
    confirmation: Optional[SubmissionConfirmation] = None
    failure: Optional[JobFailure] = None
    # Set when outcome == PAUSED; the token to pass to `resume_job`.
    resume_token: Optional[str] = None
    screenshots: list[Screenshot] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.outcome is RunOutcome.SUBMITTED
