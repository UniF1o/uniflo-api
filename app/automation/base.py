"""The abstract adapter contract.

A `UniversityAdapter` is the only thing a new portal needs to implement. The
runtime (`runtime.py`) calls these five methods in order against a live
Playwright `Page`. Per the Phase 3 decision, adapters drive the portal off the
**accessibility tree** (visible roles/labels), not hardcoded CSS selectors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar
from uuid import UUID

from playwright.async_api import Page

from app.automation.results import SubmissionConfirmation


@dataclass
class PortalCredentials:
    """Per-applicant portal login, loaded from a secrets store — never the DB.
    `extra` holds portal-specific secrets (e.g. UJ's 5-digit PIN, a Wits
    temporary ID)."""

    username: str
    password: str
    extra: dict[str, str] = field(default_factory=dict)


@dataclass
class DocumentRef:
    """A document to upload. The runtime has already fetched the file from
    Storage to `local_path`; `doc_type` is the Uniflo `DocumentType`."""

    doc_type: str
    local_path: str
    filename: str


@dataclass
class FieldMapping:
    """The values to enter, keyed by a portal-field identifier.

    Task 2 keeps this a simple name→value map so the base class is
    self-consistent. Task 3 (AI mapping) enriches it with per-field confidence
    and a flagged-for-review set — additively, so adapters written against
    `.get(name)` keep working.
    """

    values: dict[str, Any] = field(default_factory=dict)

    def get(self, name: str, default: Any = None) -> Any:
        return self.values.get(name, default)


class UniversityAdapter(ABC):
    """One per university portal. Concrete adapters set the two class vars and
    implement the five steps; they must never touch the DB or the runtime —
    they only act on the `page` they're handed."""

    university_id: ClassVar[UUID]
    slug: ClassVar[str]  # "uct", "wits", "up", "uj"

    @abstractmethod
    async def login(self, page: Page, credentials: PortalCredentials) -> None:
        """Authenticate (or create/begin the application) so the form is
        reachable. Raise `AuthFailedError` on rejected credentials,
        `HumanActionRequiredError` on a captcha/OTP that can't be cleared."""

    @abstractmethod
    async def fill_form(self, page: Page, mapping: FieldMapping) -> None:
        """Walk the form page by page, entering each value from `mapping`. Wrap
        selector/label lookups so a missing one raises `PortalChangedError`."""

    @abstractmethod
    async def upload_documents(
        self, page: Page, documents: list[DocumentRef]
    ) -> None:
        """Attach the required documents. A no-op for portals that take none at
        application time (e.g. UJ)."""

    @abstractmethod
    async def submit(self, page: Page) -> None:
        """Perform the final submit (after the student's consent is already
        recorded). Raise `ValidationFailedError` if the portal rejects it."""

    @abstractmethod
    async def verify_submission(self, page: Page) -> SubmissionConfirmation:
        """Read the post-submit page and return the success marker (reference /
        applicant number). Raise `PortalChangedError` if it can't be confirmed."""
