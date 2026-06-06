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

from app.automation.adapters.uj_programmes import (
    best_programme_match,
    faculty_search_term,
    resolve_faculty,
)
from app.automation.base import (
    DocumentRef,
    FieldMapping,
    PortalCredentials,
    UniversityAdapter,
)
from app.automation.exceptions import AuthFailedError, PortalChangedError
from app.automation.results import SubmissionConfirmation
from app.automation.subjects import best_subject_match, subject_search_term

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

# "Save and Continue" button per page (each advances to the next wizard page).
_PAGE_A_NEXT = "#oapNextBtn2"  # Biographical -> Next of Kin
_PAGE_B_NEXT = "#oapNextBtn2_1"  # Next of Kin -> Matric
_PAGE_C_NEXT = "#oapNextBtn3"  # Matric -> Previous Studies
_PAGE_D_NEXT = "#oapNextBtn4"  # Previous Studies -> Qualifications

# Page C (Matric/Results) ids — verified live 2026-06-06.
_C_MATRIC_YEAR = "#oapMatYear"
_C_UG_ONLY = "#oapUGPGUGOnly"  # UG-only select shown after matric year (not #oapUGPG)
_C_UPGRADING = "#oapStudUpgrade"
_C_MATRIC_TYPE = "#oapTypeMatric"
_C_ENDORSEMENT = "#oapMatType"  # LOV, gates the subject-capture fields
_C_SUBJECT = "#oapMSubj"  # LOV
_C_GRADE = "#oapMGrade"  # LOV ("NSC")
_C_PERCENT = "#oapsymbGr11"  # LOV — the "symbol" field holds the Gr11 percentage
_C_ADD_SUBJECT = "#oapAddMatric"

# Page D (Previous Studies) ids.
_D_SCHOOL = "#oapSchool"  # LOV
_D_PRESENT_ACTIVITY = "#oapPact"  # LOV ("GRADE 12 PUPIL")
_D_STUDIED_BEFORE = "#oapPrevQualInd"  # select Yes/No

# Page E (Qualifications) ids — verified live 2026-06-06.
_E_ACADEMIC_YEAR = "#oapAcademicYear"  # select (2027/2026)
_E_APPLYING_FOR = "#oapECSLP"  # select — GATES the faculty LOV (Curricular Courses)
_E_FACULTY = "#oapFaculty"  # LOV
_E_PROGRAMME = "#oapQualification"  # LOV — code-keyed rows; desc has (ELIGIBLE TO APPLY-Y/N)
_E_STUDY_PERIOD = "#oapStudyPeriod"  # LOV (FIRST YEAR)
_E_OFFERING = "#oapOfferingType"  # LOV — auto-populates from the programme
_E_BLOCK = "#oapBlock"  # LOV — auto-populates from the programme
_PAGE_E_NEXT = "#oapNextBtn6"

# Page G (Rules and Agreement) ids — INSPECTED 2026-06-06 (never submitted).
_G_PIN = "#oapLoginPin"  # 5-digit PIN
_G_ACCEPT = "#oapAcceptApplRAR"  # "I Accept"
_G_SUBMIT = "#oapNextBtn8"  # "Submit Application"
_G_QUIT = "#oapExitBtn8"  # "Quit Application" — NEVER click (deletes all data)

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
        """Runtime contract method. UJ is multi-page, so this drives the **whole**
        form after `login()`: Page A → Save → B → Save → C → Save → D → Save → E →
        Save → F → Continue, landing on **Page G**. It never submits — the runtime
        calls `submit()` as the next step (see `runtime.py`). Live-verified
        end-to-end 2026-06-06.

        Pages A/B are filled generically by `_fill_simple`; Pages C/D/E need
        reveal-ordering, the subject loop, and LOV gating, so they have dedicated
        methods. `_save_and_continue` clicks each page's Save (force-enabling Page
        E's, which ITS leaves disabled after automated fills — the server still
        validates)."""
        await self._fill_simple(page, mapping, "A")           # Biographical
        await self._save_and_continue(page, _PAGE_A_NEXT)
        await self._fill_simple(page, mapping, "B")           # Next of Kin + Account
        await self._save_and_continue(page, _PAGE_B_NEXT)
        await self.fill_matric_page(page, mapping)            # Matric (C)
        await self._save_and_continue(page, _PAGE_C_NEXT)
        await self.fill_previous_studies_page(page, mapping)  # Previous Studies (D)
        await self._save_and_continue(page, _PAGE_D_NEXT)
        await self.fill_qualifications_page(page, mapping)    # Qualifications (E)
        await self._save_and_continue(page, _PAGE_E_NEXT, force=True)
        await self._continue_summary(page)                    # Summary (F) → Page G
        logger.info("UJ fill_form: reached Page G (agreement) — awaiting submit()")

    async def _fill_simple(
        self, page: Page, mapping: FieldMapping, page_key: str | None = None
    ) -> None:
        """Apply the simple fields (optionally scoped to one wizard page). Skips
        `manual` fields, unmapped values, and conditional fields that aren't
        currently visible (so a hidden auto-derived control doesn't stall)."""
        for field in load_field_schema()["fields"]:
            if page_key is not None and field.get("page") != page_key:
                continue
            selector = field.get("selector")
            value = mapping.get(field["field_id"])
            if value is None or field.get("manual"):
                continue
            if not selector:
                logger.info("UJ fill: %s has no selector — skipping", field["field_id"])
                continue
            if field.get("conditional") and not await self._is_visible(page, selector):
                continue
            try:
                await self._apply(page, field, selector, str(value))
            except PortalChangedError:
                if field.get("conditional"):
                    logger.info("UJ fill: conditional %s not actionable — skipping",
                                field["field_id"])
                    continue
                raise

    async def run_application(
        self, page: Page, mapping: FieldMapping, *, do_submit: bool = False
    ) -> SubmissionConfirmation | None:
        """Standalone convenience for integration/smoke runs — the runtime instead
        calls the pipeline steps (`fill_form` → `upload_documents` → `submit` →
        `verify_submission`) individually. Assumes `login()` already cleared the
        gate onto Page A. With `do_submit=False` (default) it fills the whole form
        and stops **on Page G without clicking Submit**; with `do_submit=True` it
        performs the final submit + reads the confirmation."""
        await self.fill_form(page, mapping)
        await self.upload_documents(page, [])
        if do_submit:
            await self.submit(page)
            return await self.verify_submission(page)
        logger.info("UJ run_application: stopped on Page G (do_submit=False)")
        return None

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

    # --- Page C / D: dedicated flows (reveal-ordering + the subject loop) -----

    async def fill_matric_page(self, page: Page, mapping: FieldMapping) -> None:
        """Page C (Matric/Results). ITS reveals this page's fields progressively
        and the endorsement LOV silently resets matric-type, so the ordering and
        a re-assert matter (all verified live 2026-06-06):

        1. Matric year first — its onchange (`eventRun(5.4)`) reveals the rest.
        2. UG/PG auto-resolves to the UG-only select (`#oapUGPGUGOnly`); the
           choice control `#oapUGPG` hides.
        3. Upgrading + matric-type, then the endorsement LOV (which gates the
           subject-capture LOVs **and** wipes matric-type → re-assert it).
        4. Loop the subjects (each: subject + grade(NSC) + Gr11 % + Add Subject).
        """
        matric_type = mapping.get("matric_type", "SA Matric")
        await self._fill(page, _C_MATRIC_YEAR, str(mapping.get("matric_year", "")))
        await self._fire(page, _C_MATRIC_YEAR, "change", "blur")
        await self._select_label(
            page, _C_UG_ONLY, mapping.get("ug_or_pg", "Undergraduate")
        )
        await self._select_label(page, _C_UPGRADING, mapping.get("upgrading", "No"))
        await self._select_label(page, _C_MATRIC_TYPE, matric_type)
        await self.select_from_lov(
            page, _C_ENDORSEMENT, mapping.get("endorsement", "CURRENTLY IN GR.12")
        )
        # the endorsement LOV re-render resets matric-type to the placeholder
        await self._select_label(page, _C_MATRIC_TYPE, matric_type)
        for subject in mapping.get("subjects") or []:
            await self.add_subject(page, subject["name"], subject["percentage"])

    async def add_subject(
        self, page: Page, subject_name: str, percentage: object
    ) -> None:
        """Add one row to the Page-C subjects table via the LOVs + Add Subject.
        Grade is always 'NSC' for an SA matric; the Gr11 percentage lives in the
        mislabelled 'symbol' field. Re-asserts matric-type first as a guard."""
        await self.select_subject_from_lov(page, subject_name)
        await self.select_from_lov(page, _C_GRADE, "NSC")
        await self.select_from_lov(
            page, _C_PERCENT, str(percentage), search_term=str(percentage)
        )
        await self._select_label(page, _C_MATRIC_TYPE, "SA Matric")
        await self._click(page, _C_ADD_SUBJECT)

    async def fill_previous_studies_page(
        self, page: Page, mapping: FieldMapping
    ) -> None:
        """Page D (Previous Studies): last school (LOV), present activity (LOV,
        'GRADE 12 PUPIL'), and whether they studied elsewhere before (No for a
        school leaver). Verified ids 2026-06-06."""
        school = mapping.get("school")
        await self.select_from_lov(page, _D_SCHOOL, school, search_term=school)
        await self.select_from_lov(
            page, _D_PRESENT_ACTIVITY, mapping.get("present_activity", "GRADE 12 PUPIL")
        )
        # the two LOVs re-render the page (resetDependant), briefly detaching this
        # select — let it settle, then use the JS-fallback selector.
        await page.wait_for_timeout(800)
        await self._select_label_or_js(
            page, _D_STUDIED_BEFORE, mapping.get("studied_before", "No")
        )

    async def fill_qualifications_page(
        self, page: Page, mapping: FieldMapping
    ) -> None:
        """Page E (Qualifications). Gating found live 2026-06-06:
        - the faculty LOV is **empty until** "Are you applying for" (`#oapECSLP`)
          is set to "Curricular Courses" (its server query filters on that);
        - the programme LOV (`#oapQualification`) is **code-keyed** — the row's
          link text is a code (e.g. `B6CS0Q`), the readable name + an
          `(ELIGIBLE TO APPLY-Y/N)` tag are in the description cell, so pick by
          row text (`select_from_lov_row`);
        - choosing the study period **auto-populates** offering type + block.

        **[VERIFY]** In a headless walk `#oapECSLP` rendered hidden and the Save
        button (`#oapNextBtn6`) stayed disabled until force-enabled; re-confirm a
        real (visible) selection fires ITS's enable routine in the live run.
        """
        await self._select_label_or_js(
            page, _E_ACADEMIC_YEAR, str(mapping.get("academic_year", "2027"))
        )
        await self._select_label_or_js(
            page, _E_APPLYING_FOR, mapping.get("applying_for", "Curricular Courses")
        )
        programme = mapping.get("programme")
        faculty = mapping.get("faculty") or resolve_faculty(programme or "")
        if not faculty:
            raise PortalChangedError(
                f"could not resolve a UJ faculty for programme {programme!r}",
                selector=_E_FACULTY,
            )
        await self.select_from_lov(
            page, _E_FACULTY, faculty, search_term=faculty_search_term(faculty)
        )
        if programme:
            await self.select_programme_from_lov(page, programme)
        year = mapping.get("year_of_study", "FIRST YEAR")
        await self.select_from_lov(page, _E_STUDY_PERIOD, year, search_term=year)
        # offering type + block auto-populate from the programme; only override
        # them if the mapping explicitly supplies a value.
        if mapping.get("mode_of_study"):
            await self.select_from_lov(
                page, _E_OFFERING, mapping["mode_of_study"],
                search_term=mapping["mode_of_study"],
            )

    async def select_from_lov_row(
        self,
        page: Page,
        code_selector: str,
        row_contains: str,
        *,
        search_term: str | None = "%",
    ) -> None:
        """Variant of `select_from_lov` for **code+description** LOVs (the UJ
        programme list): the clickable `<a>` carries an opaque code, so match on
        the *row* text instead and click the anchor inside it. Verified live for
        `#oapQualification` (picks an `(ELIGIBLE TO APPLY-Y)` programme)."""
        lov = await self._open_lov(page, code_selector)
        try:
            await lov.wait_for_load_state("domcontentloaded")
            if search_term:
                await lov.fill("input[name=x_thefilter]", search_term)
                await lov.get_by_role("button", name="Search").click()
            clicked = await lov.evaluate(
                """(c) => {
                  for (const tr of document.querySelectorAll('tr')) {
                    if ((tr.innerText || '').toUpperCase().includes(c.toUpperCase())) {
                      const a = tr.querySelector('a');
                      if (a) { a.click(); return true; }
                    }
                  }
                  return false;
                }""",
                row_contains,
            )
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                f"LOV row {row_contains!r} not selectable for {code_selector}",
                selector=code_selector,
            ) from exc
        if not clicked:
            raise PortalChangedError(
                f"no LOV row contains {row_contains!r}", selector=code_selector
            )

    async def select_programme_from_lov(
        self, page: Page, programme_text: str
    ) -> None:
        """Pick the programme (Page E) from the code-keyed LOV. Reads the live
        rows, scores the free-text request against the **eligible** descriptions
        (`app.automation.adapters.uj_programmes.best_programme_match`), and clicks
        the chosen row's anchor. Raises PortalChangedError if no eligible
        programme confidently matches — never submits an ineligible/guessed one."""
        lov = await self._open_lov(page, _E_PROGRAMME)
        try:
            await lov.wait_for_load_state("domcontentloaded")
            await lov.fill("input[name=x_thefilter]", "%")
            await lov.get_by_role("button", name="Search").click()
            rows = await lov.evaluate(
                "()=>[...document.querySelectorAll('tr')]"
                ".map(tr=>(tr.innerText||'').replace(/\\s+/g,' ').trim())"
                ".filter(t=>t.length>4 && t.length<160)"
            )
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                f"programme LOV failed for {programme_text!r}", selector=_E_PROGRAMME
            ) from exc
        chosen = best_programme_match(programme_text, rows or [])
        if not chosen:
            raise PortalChangedError(
                f"no eligible UJ programme matched {programme_text!r}",
                selector=_E_PROGRAMME,
            )
        try:
            clicked = await lov.evaluate(
                """(rowtext) => {
                  for (const tr of document.querySelectorAll('tr')) {
                    if ((tr.innerText || '').replace(/\\s+/g,' ').trim() === rowtext) {
                      const a = tr.querySelector('a');
                      if (a) { a.click(); return true; }
                    }
                  }
                  return false;
                }""",
                chosen,
            )
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                f"could not select programme {chosen!r}", selector=_E_PROGRAMME
            ) from exc
        if not clicked:
            raise PortalChangedError(
                f"programme row vanished: {chosen!r}", selector=_E_PROGRAMME
            )
        await page.wait_for_timeout(800)

    async def select_subject_from_lov(self, page: Page, subject_name: str) -> None:
        """Pick the school-leaving subject. The student's name is free-form and
        UJ's LOV is abbreviated/qualifier-tagged, so filter the popup by the
        name's first word, read the candidate rows, and click the best match
        (see `app.automation.subjects`). Raises PortalChangedError if no row is a
        confident match — better surfaced for review than guessing a subject."""
        lov = await self._open_lov(page, _C_SUBJECT)
        try:
            await lov.wait_for_load_state("domcontentloaded")
            term = subject_search_term(subject_name)
            if term:
                await lov.fill("input[name=x_thefilter]", term)
                await lov.get_by_role("button", name="Search").click()
            rows = await lov.evaluate(
                "()=>[...document.querySelectorAll('a')]"
                ".map(a=>(a.innerText||'').trim()).filter(t=>t && t.length<70)"
            )
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                f"subject LOV failed for {subject_name!r}", selector=_C_SUBJECT
            ) from exc
        target = best_subject_match(subject_name, rows or [])
        if not target:
            raise PortalChangedError(
                f"no LOV subject matched {subject_name!r}", selector=_C_SUBJECT
            )
        try:
            await lov.get_by_role("link", name=target, exact=True).first.click()
            await page.wait_for_timeout(400)
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                f"could not select subject {target!r}", selector=_C_SUBJECT
            ) from exc

    async def _is_visible(self, page: Page, selector: str) -> bool:
        try:
            return bool(await page.evaluate(
                "(s)=>{const e=document.querySelector(s); return !!(e && e.offsetParent);}",
                selector,
            ))
        except Exception:  # noqa: BLE001
            return False

    async def _select_label_or_js(
        self, page: Page, selector: str, label: str
    ) -> None:
        """Select an option by visible text, falling back to a direct JS value-set
        if the control is conditionally hidden (ITS sometimes renders `#oapECSLP`
        hidden under automation; the dependent LOV query reads the value, not the
        UI)."""
        try:
            await page.select_option(selector, label=label, timeout=5000)
            return
        except Exception:  # noqa: BLE001
            pass
        ok = await page.evaluate(
            """([sel, txt]) => {
              const s = document.querySelector(sel);
              if (!s) return false;
              const o = [...s.options].find(o => o.text.trim() === txt);
              if (!o) return false;
              s.value = o.value;
              s.dispatchEvent(new Event('change', {bubbles: true}));
              s.dispatchEvent(new Event('blur', {bubbles: true}));
              return true;
            }""",
            [selector, label],
        )
        if not ok:
            raise PortalChangedError(
                f"select {selector} has no option {label!r}", selector=selector
            )

    async def _save_and_continue(
        self, page: Page, selector: str, *, force: bool = False
    ) -> None:
        """Click a page's Save and Continue button and wait for the next page.
        `force=True` clears a `disabled` attribute first (Page E's Save stays
        disabled after automated fills; the server still validates on submit)."""
        if force:
            await page.evaluate(
                "(s)=>{const e=document.querySelector(s); if(e) e.disabled=false;}",
                selector,
            )
        await self._click(page, selector)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1800)

    async def _continue_summary(self, page: Page) -> None:
        """Page F (summary) advances via an id-less "Continue" button → Page G."""
        try:
            await page.get_by_role("button", name="Continue", exact=False).first.click()
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(1800)
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                "Page F 'Continue' button not found", selector="Continue"
            ) from exc

    async def _fire(self, page: Page, selector: str, *events: str) -> None:
        """Dispatch DOM events so ITS's inline `eventRun(...)` reveal handlers
        fire (e.g. matric year's onchange that reveals the UG block)."""
        try:
            await page.eval_on_selector(
                selector,
                "(el, evs) => evs.forEach("
                "n => el.dispatchEvent(new Event(n, {bubbles: true})))",
                list(events),
            )
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                f"could not fire {events} on {selector}", selector=selector
            ) from exc

    async def upload_documents(
        self, page: Page, documents: list[DocumentRef]
    ) -> None:
        """No-op — UJ requires no document upload for the initial application
        (confirmed). Any documents are submitted later/out of band."""
        return

    async def submit(self, page: Page) -> None:
        """Page G (Rules and Agreement): enter the 5-digit PIN, tick I Accept,
        click Submit Application. **Never** click Quit Application
        (`#oapExitBtn8` — it deletes all captured data). Ids inspected live
        2026-06-06 (the page itself was never submitted)."""
        pin = self._credentials.extra.get("pin") if self._credentials else None
        if not pin:
            raise AuthFailedError(
                "UJ submit needs a 5-digit PIN in credentials.extra['pin']"
            )
        await self._fill(page, _G_PIN, pin)
        await self._check(page, _G_ACCEPT)
        await self._click(page, _G_SUBMIT)

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
