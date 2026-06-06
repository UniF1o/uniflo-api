"""University of Johannesburg adapter (ITS Integrator).

UJ is the first-adapter target: no captcha, and a new applicant doesn't log in —
the entry/POPI gate leads straight into the form, and a student number + PIN are
issued at submit.

**Selector strategy — id, not accessibility tree.** Approach C (accessibility
primary) does *not* work on ITS Integrator: the inputs carry **no accessible
names** (`get_by_role(...).name` is empty), so locating by role+label fails.
Every field does carry a **stable element id** (`oapSurname`, `oapTitle`, …)
with proper `<select>` option labels — that's the reliable handle. Verified live
2026-06-05 (see docs/phase-3/task-4-adapter-uj.md). Page A (Biographical) ids are
verified; the LOV search triggers, pages B-G, and the submit page are marked
**[VERIFY LIVE]** for the next walk.
"""

import json
import logging
from pathlib import Path
from uuid import UUID

from playwright.async_api import Page

from app.automation.base import (
    DocumentRef,
    FieldMapping,
    PortalCredentials,
    UniversityAdapter,
)
from app.automation.exceptions import AuthFailedError, PortalChangedError
from app.automation.results import SubmissionConfirmation

logger = logging.getLogger(__name__)

# Seeded UJ row in `universities` (resolved by slug at wiring time; pinned here so
# the adapter satisfies the base contract). Update if the table is reseeded.
UJ_UNIVERSITY_ID = UUID("ed91f7dd-65b1-44c7-ae92-634abf9c4030")
UJ_SLUG = "uj"

ENTRY_URL = (
    "https://registration.uj.ac.za/pls/prodi41/"
    "gen.gw1pkg.gw1startup?x_processcode=ITS_OAP"
)

# Entry/POPI gate — verified ids; <select> option *values* are Y/N.
_GATE_HAVE_STUDENT_NO = "#oapOldNew"
_GATE_RETURNING = "#oapReturnYesNo"
_GATE_TOKEN = "#oapTokenYesNo"
_GATE_ACCEPT_POPI = "#oapAcceptPopi"
_GATE_NEXT = "#oapNextBtn1"

# Biographical page next button.
_PAGE_A_NEXT = "#oapNextBtn2"

_FIELDS_PATH = Path(__file__).with_name("uj.fields.json")


def load_field_schema() -> dict:
    """The UJ form field catalog (parsed lazily so importing the adapter is cheap)."""
    return json.loads(_FIELDS_PATH.read_text(encoding="utf-8"))


class UJAdapter(UniversityAdapter):
    university_id = UJ_UNIVERSITY_ID
    slug = UJ_SLUG

    def __init__(self) -> None:
        # Stashed in login() so submit() can read the 5-digit PIN.
        self._credentials: PortalCredentials | None = None

    # --- pipeline -------------------------------------------------------------

    async def login(self, page: Page, credentials: PortalCredentials) -> None:
        """UJ new applicants don't authenticate — pass the entry/POPI gate into
        the biographical form. POPI must already be consented by the student
        upstream (consent is surfaced, not auto-accepted); the bot only ticks the
        box it was told to. Verified live 2026-06-05."""
        self._credentials = credentials
        await page.goto(ENTRY_URL, wait_until="domcontentloaded")
        # option value "N" == "No"; each answer reveals the next control.
        await self._select_value(page, _GATE_HAVE_STUDENT_NO, "N")
        await self._select_value(page, _GATE_RETURNING, "N")
        await self._select_value(page, _GATE_TOKEN, "N")
        await self._check(page, _GATE_ACCEPT_POPI)
        await self._click(page, _GATE_NEXT)

    async def fill_form(self, page: Page, mapping: FieldMapping) -> None:
        """Enter each mapped value via its field's id. Acts only on fields with a
        verified `selector`; the rest (pages B-G, LOV triggers) are skipped with a
        log until the next live walk wires them. **[VERIFY LIVE]:** UJ is
        multi-page, so the full flow must click **Save and Continue**
        (#oapNextBtn2 …) between pages and loop the Add-Subject rows — wired next."""
        for field in load_field_schema()["fields"]:
            selector = field.get("selector")
            value = mapping.get(field["field_id"])
            if value is None:
                continue  # unmapped / low-confidence — handled upstream
            if not selector:
                logger.info(
                    "UJ fill_form: %s has no verified selector yet — skipping",
                    field["field_id"],
                )
                continue
            try:
                await self._apply(page, field, selector, str(value))
            except PortalChangedError:
                # Conditionally-shown fields (e.g. gender auto-derived from the
                # ID number) may not be actionable — skip rather than fail the run.
                if field.get("conditional"):
                    logger.info(
                        "UJ fill_form: conditional %s not actionable — skipping",
                        field["field_id"],
                    )
                    continue
                raise

    async def _apply(
        self, page: Page, field: dict, selector: str, value: str
    ) -> None:
        ftype = field["type"]
        if ftype == "text":
            await self._fill(page, selector, value)
        elif ftype == "date":
            await self._set_date(page, selector, value)
        elif ftype == "select":
            await self._select_label(page, selector, value)
        elif ftype == "checkbox":
            if value.strip().lower() in ("true", "yes", "1"):
                await self._check(page, selector)
        elif ftype == "lov":
            # short lists (citizenship) click the row directly; long lists
            # (postal codes) filter first via `lov_search`.
            search = value if field.get("lov_search") else None
            await self.select_from_lov(page, selector, value, search_term=search)

    async def upload_documents(
        self, page: Page, documents: list[DocumentRef]
    ) -> None:
        """No-op — UJ requires no document upload for the initial application
        (confirmed). Any documents are submitted later/out of band."""
        return

    async def submit(self, page: Page) -> None:
        """Page G: enter the 5-digit PIN, tick I Accept, click Submit
        Application. **Never** click Quit Application (it deletes all data).
        **[VERIFY LIVE]:** the Page G element ids aren't captured yet."""
        pin = self._credentials.extra.get("pin") if self._credentials else None
        if not pin:
            raise AuthFailedError(
                "UJ submit needs a 5-digit PIN in credentials.extra['pin']"
            )
        await self._fill(page, "#oapLoginPin", pin)
        await self._check(page, "#oapAcceptAgreement")
        await self._click(page, "#oapSubmitBtn")

    async def verify_submission(self, page: Page) -> SubmissionConfirmation:
        """**[VERIFY LIVE]:** the post-submit success page wasn't captured (no
        fake submissions). Best-effort read of a student/reference number; pin the
        real marker during the supervised first live submit."""
        marker = None
        try:
            marker = await page.get_by_text(
                "student number", exact=False
            ).first.inner_text()
        except Exception:  # noqa: BLE001
            logger.warning("UJ verify_submission: success marker not pinned yet")
        return SubmissionConfirmation(reference=None, marker=marker)

    # --- id-based helpers (the verified strategy for ITS) ---------------------

    async def _fill(self, page: Page, selector: str, value: str) -> None:
        try:
            await page.fill(selector, value)
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                f"field {selector} not found", selector=selector
            ) from exc

    async def _select_label(self, page: Page, selector: str, label: str) -> None:
        try:
            await page.select_option(selector, label=label)
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                f"dropdown {selector} has no option {label!r}", selector=selector
            ) from exc

    async def _select_value(self, page: Page, selector: str, value: str) -> None:
        try:
            await page.select_option(selector, value=value)
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                f"dropdown {selector} has no value {value!r}", selector=selector
            ) from exc

    async def _set_date(self, page: Page, selector: str, value: str) -> None:
        """ITS date fields (e.g. `#oapBirthdate`) are **readonly** calendar
        widgets — `fill` won't stick. Set the value and fire change/blur directly.
        Value must already be in UJ's `DD-MON-YYYY` format (e.g. `12-MAR-2008`).
        Verified live 2026-06-05 (Page A saved with this)."""
        try:
            await page.evaluate(
                """([sel, val]) => {
                  const el = document.querySelector(sel);
                  if (!el) throw new Error('date field missing');
                  el.removeAttribute('readonly');
                  el.value = val;
                  el.dispatchEvent(new Event('change', {bubbles: true}));
                  el.dispatchEvent(new Event('blur', {bubbles: true}));
                }""",
                [selector, value],
            )
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                f"date field {selector} could not be set", selector=selector
            ) from exc

    async def _check(self, page: Page, selector: str) -> None:
        try:
            await page.check(selector)
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                f"checkbox {selector} not found", selector=selector
            ) from exc

    async def _click(self, page: Page, selector: str) -> None:
        try:
            await page.click(selector)
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                f"control {selector} not found", selector=selector
            ) from exc

    async def select_from_lov(
        self,
        page: Page,
        code_selector: str,
        target_text: str,
        *,
        search_term: str | None = None,
    ) -> None:
        """ITS "List of Values" handler (verified for the citizenship list,
        2026-06-05). The code field (`#oapCitzCode`) is readonly; a sibling
        anchor `a[href*=<fieldId>]` calls `runWizardLov(...)` which opens a
        **popup window** (`gw1lovbind`) with an `x_thefilter` search box, a
        Search button, and result rows as `<a onclick="resetDependant(...)">`.
        Short option lists load in full (click the row directly); long lists
        (e.g. postal codes) need `search_term` first."""
        lov = await self._open_lov(page, code_selector)
        await self._pick_from_lov(lov, code_selector, target_text, search_term)

    async def _open_lov(self, page: Page, code_selector: str):
        field_id = code_selector.lstrip("#")
        try:
            async with page.expect_popup() as info:
                await page.click(f"a[href*={field_id}]")
            return await info.value
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                f"LOV popup did not open for {field_id}", selector=code_selector
            ) from exc

    async def _pick_from_lov(
        self, lov, code_selector: str, target_text: str, search_term: str | None
    ) -> None:
        try:
            await lov.wait_for_load_state("domcontentloaded")
            if search_term:
                await lov.fill("input[name=x_thefilter]", search_term)
                await lov.get_by_role("button", name="Search").click()
                await lov.get_by_role("link", name=target_text).first.click()
            else:
                await lov.get_by_role(
                    "link", name=target_text, exact=True
                ).first.click()
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                f"LOV row {target_text!r} not selectable for {code_selector}",
                selector=code_selector,
            ) from exc
