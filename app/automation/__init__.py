"""Phase 3 portal-automation framework.

`base.py` defines the abstract `UniversityAdapter` every portal adapter
implements; `runtime.py` drives an adapter through a Playwright browser and
turns the outcome into a structured `SubmissionResult`. No concrete adapter
lives here yet — the first one lands in Task 4 under `adapters/`.
"""

from app.automation.base import (
    DocumentRef,
    FieldMapping,
    PortalCredentials,
    UniversityAdapter,
)
from app.automation.exceptions import (
    AdapterError,
    AuthFailedError,
    HumanActionRequiredError,
    PortalChangedError,
    UnknownAdapterError,
    ValidationFailedError,
)
from app.automation.results import (
    JobFailure,
    RunOutcome,
    Screenshot,
    SubmissionConfirmation,
    SubmissionResult,
)
from app.automation.runtime import (
    DEFAULT_TIMEOUT_S,
    InMemoryPauseStore,
    PauseStore,
    drive,
    resume_job,
    run_job,
)

__all__ = [
    "UniversityAdapter",
    "PortalCredentials",
    "FieldMapping",
    "DocumentRef",
    "AdapterError",
    "AuthFailedError",
    "PortalChangedError",
    "ValidationFailedError",
    "HumanActionRequiredError",
    "UnknownAdapterError",
    "SubmissionResult",
    "SubmissionConfirmation",
    "JobFailure",
    "Screenshot",
    "RunOutcome",
    "drive",
    "run_job",
    "resume_job",
    "PauseStore",
    "InMemoryPauseStore",
    "DEFAULT_TIMEOUT_S",
]
