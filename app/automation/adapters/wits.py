"""University of the Witwatersrand adapter (PeopleSoft Activity Guide, VC_OA).

Everything here encodes the live walkthrough of 2026-06-11 (Create Application
ID → captcha → emailed Temporary ID login → password change → all 17 wizard
steps → stop ON Step 17, Submit never clicked): see
docs/phase-3/portal-research/wits.md "Live spike findings" for the verified
behaviours and element ids.

Wits shares the PeopleSoft AJAX model with UCT/UP, so the `fluid` helpers
drive it: stale handles after every round-trip, `ptModFrame_N` modal iframes,
`[role=alertdialog]` dialogs with stable message codes. Wits-specific
behaviours (all verified live):

- **Captcha decodes from the DOM** — six `<img>` filenames spell the answer
  (`VC_L_Y_1.JPG` → "y"), the same scheme as UP with a `VC_` prefix. The
  vision solver is the fallback.
- **Two-phase login**: Create Application ID makes Wits email a Temporary ID +
  temp password (fetched via the EmailChallengeSource); the confirm flow then
  forces a password change (→ the derived permanent password, never persisted).
- **One field per server round-trip** — a select's AJAX re-render silently
  discards sibling values set in the same pass, so every change settles before
  the next.
- **Validate Application gates steps 7+** (the Next button hides on step 6
  until it passes), and **eligibility is enforced at validation** ("You do not
  meet the subject requirements for …" in the Validation Messages modal),
  keyed off the Grade 12 subject list — not at programme selection like UP.
- **The indemnity (step 14) sits before Documents (16)** in wizard order, so
  `upload_documents` only proceeds past it when the student's agreement
  consent is recorded (`credentials.extra["agreement_consented"]`); without it
  the run parks at the indemnity instead of auto-accepting.
- **Submission is NOT payment-gated** — the R100 fee is paid after submit
  (FNB EFT / Campus Finances) with the issued person/student number as
  reference, so `submit()` proceeds (unlike UP).
"""

import calendar
import logging
import re
from pathlib import Path
from typing import Optional
from uuid import UUID

from playwright.async_api import Frame, Page

from app.automation import fluid
from app.automation.adapters.uct import best_option_match
from app.automation.adapters.up import decode_captcha_sources
from app.automation.base import (
    DocumentRef,
    FieldMapping,
    PortalCredentials,
    UniversityAdapter,
)
from app.automation.challenge import ChallengeRequest, EmailChallengeSource
from app.automation.exceptions import (
    AuthFailedError,
    HumanActionRequiredError,
    PortalChangedError,
    ValidationFailedError,
)
from app.automation.results import SubmissionConfirmation

logger = logging.getLogger(__name__)

# Placeholder (seeded `universities` ids are uuid4 — resolution goes through
# `adapters.slug_for_website`, like UCT/UP).
WITS_UNIVERSITY_ID = UUID("00000000-0000-0000-0000-000000000717")
WITS_SLUG = "wits"

# wits.ac.za/applications/ redirects here (verified live).
LOGIN_URL = (
    "https://self-service.wits.ac.za/psc/csprodonl/UW_SELF_SERVICE/SA/c/"
    "VC_OA_LOGIN_MENU.VC_OA_LOGIN_FL.GBL"
)

# Login / create / confirm pages (all VC_OA_LOGIN_WRK_*, verified live).
_LOGIN_TEMP_ID = "#VC_OA_LOGIN_WRK_OPRID"
_LOGIN_PASSWORD = "#VC_OA_LOGIN_WRK_PASSWORD"
_LOGIN_BTN = "#VC_OA_LOGIN_WRK_VC_LOGIN_PB"
_REGISTER_BTN = "#VC_OA_LOGIN_WRK_REGISTER"
_CONFIRM_PWD_BTN = "#VC_OA_LOGIN_WRK_VC_CONFIRM_PWD_PB"
_CONTINUE_BTN = "#VC_OA_LOGIN_WRK_CONTINUE_PB"  # doubles as the OK button
_CREATE = {
    "nationality": "#VC_OA_LOGIN_WRK_COUNTRY",
    "national_id": "#VC_OA_LOGIN_WRK_NATIONAL_ID",
    "title": "#VC_OA_LOGIN_WRK_NAME_PREFIX",
    "first_name": "#VC_OA_LOGIN_WRK_FIRST_NAME",
    "middle_names": "#VC_OA_LOGIN_WRK_MIDDLE_NAME",
    "last_name": "#VC_OA_LOGIN_WRK_LAST_NAME",
    "dob_day": "#VC_OA_LOGIN_WRK_CUB_BEGINDAY",
    "dob_month": "#VC_OA_LOGIN_WRK_MONTH_XLAT",
    "dob_year": "#VC_OA_LOGIN_WRK_VC_YEAR",
    "gender": "#VC_OA_LOGIN_WRK_SEX",
    "email": "#VC_OA_LOGIN_WRK_EMAIL_ADDR",
    "mobile": "#VC_OA_LOGIN_WRK_VC_PHONE_CELL_SS",  # the unlabelled number input
    "security_code": "#VC_OA_LOGIN_WRK_VC_SEC_CODE",
}

# Apply for Admission page.
_ACTION_SELECT = "#VC_OA_APPLY_WRK_VC_OA_APPL_ACTN"
_TYPE_SELECT = "#VC_OA_APPLY_WRK_VC_OA_APP_TYPE"
_YEAR_SELECT = "#VC_OA_APPLY_WRK_ADMIT_TERM"
_CALENDAR_SELECT = "#VC_OA_APPLY_WRK_WITS_ADMISSIONCALE"

# Wizard step controls (prefix VC_OA_STG_..., verified live). `$` ids go
# through attribute selectors so nothing needs escaping.
_ACTIVITY_SELECT = "#VC_OA_STG_GENL_VC_MAIN_ACTIVITY"
_SCHOOL_SEARCH_KEY = "#VC_OA_WRK_SEARCH_KEY"
_SCHOOL_SEARCH_BTN = "#VC_OA_WRK_SEARCH_BTN"
_AUTHORITY_SELECT = "#VC_OA_STG_SEDH_WITS_EXM_AUT_CD"
_EXAM_YEAR_INPUT = "#VC_OA_STG_SEDH_VC_FINAL_SCHL_YEAR"
_EXAM_MONTH_SELECT = "#VC_OA_STG_SEDH_UW_EXAM_MONTH"
_EXAM_NUMBER_INPUT = "#VC_OA_STG_SEDH_WITS_EXAMNUM"
_GR11_SUBJECT = 'select[id="VC_OA_STG_SEDG_SCHOOL_CRSE_NBR${n}"]'
_GR11_MARK = 'input[id="VC_OA_STG_SEDG_VC_GRADE${n}"]'
_COPY_GR11_BTN = "#VC_OA_WRK_VC_COPY_GR11_SUBJ"
_TERTIARY_FLAG = "#VC_OA_STG_GENL_VC_OA_TERT_FLG"
_PROG_SELECT = 'select[id="VC_OA_WRK_VC_ACAD_PROG{n}"]'
_PLAN_SELECT = 'select[id="VC_OA_WRK_VC_ACAD_PLAN{n}"]'
_ADDR1_LINE1 = "#VC_OA_STG_ADD1_ADDRESS1"
_ADDR1_LINE2 = "#VC_OA_STG_ADD1_ADDRESS2"
_ADDR1_SUBURB = "#VC_OA_STG_ADD1_ADDRESS3"
_ADDRESS_LOOKUP = "#VC_OA_WRK_ADDRESS_LOOKUP"
_ADDR2_SAME_AS = "#VC_OA_STG_ADD2_VC_USE_ADDRESS"
_ADDR3_SAME_AS = "#VC_OA_STG_ADD3_VC_USE_ADDRESS"
_CONTACT_MOBILE = "#VC_OA_STG_CNTC_VC_PHONE_CELL_SS"
_DEMO_MARITAL = "#VC_OA_STG_DEMO_MAR_STATUS"
_DEMO_POPULATION = "#VC_OA_STG_DEMO_ETHNIC_GRP_CD"
_DEMO_LANGUAGE = "#VC_OA_STG_DEMO_LANG_CD"
_DEMO_RELIGION = "#VC_OA_STG_DEMO_RELIGIOUS_PREF"
_DEMO_DISABLED = "#VC_OA_STG_DEMO_DISABLED"
_NOK_TITLE = "#VC_OA_STG_NKIN_NAME_PREFIX"
_NOK_INITIAL = "#VC_OA_STG_NKIN_FIRST_NAME"
_NOK_SURNAME = "#VC_OA_STG_NKIN_LAST_NAME"
_NOK_MOBILE = "#VC_OA_STG_NKIN_VC_PHONE_CELL_SS"
_NOK_EMAIL = "#VC_OA_STG_NKIN_EMAIL_ADDR"
_NOK_RELATION = "#VC_OA_STG_NKIN_PEOPLE_RELATION"
_NOK_SAME_AS = "#VC_OA_STG_NKIN_VC_USE_ADDRESS"
_EMERGENCY_SAME_AS = "#VC_OA_STG_GENL_VC_OA_EMERG_FLG"
_EMERGENCY_RELATION = "#VC_OA_STG_EMER_RELATIONSHIP"
_INDEMNITY_ACCEPT = "#SCC_TM_ADM_WRK_SCC_TM_ACCEPT"
_UPLOAD_ADD = 'a[id="VC_OA_WRK_FILE_CREATE1_LBL${n}"]'
# PeopleSoft File Attachment modal — My Device differs from UP's id.
_MODAL_MY_DEVICE = "#PT_ATTACH_BUTTON_DEF"
_MODAL_UPLOAD = '[id="#ICUpload"]'
_MODAL_DONE = '[id="#ICOK"]'
_SUBMIT_BTN = "#VC_OA_WRK_SUBMIT_PB"  # NEVER clicked outside the gated submit()

# Documents grid rows (verified for a Current-Grd-12 applicant):
# row 0 = Copy of ID Document/Passport, row 1 = Final GR11 Results.
_UPLOAD_ROWS = {
    "ID_COPY": 0,
    "GRADE11_RESULTS": 1,
    "MATRIC_RESULTS": 1,  # the results row takes either document
}

_FIELDS_PATH = Path(__file__).with_name("wits.fields.json")

_CAPTCHA_PREFIX = "VC"
_CAPTCHA_ATTEMPTS = 3


def load_field_schema() -> dict:
    import json

    return json.loads(_FIELDS_PATH.read_text(encoding="utf-8"))


def split_dob(value: str) -> tuple[str, str, str]:
    """dd/mm/yyyy (the credentials.extra format) → the Create Application ID
    DOB controls: zero-padded day ('12'), the month dropdown's '03 - March'
    text, and the year ('2008') — formats verified live."""
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", value.strip())
    if not match:
        raise ValueError(f"expected dd/mm/yyyy, got {value!r}")
    day, month, year = (int(g) for g in match.groups())
    return f"{day:02d}", f"{month:02d} - {calendar.month_name[month]}", str(year)


def local_mobile(phone: str) -> str:
    """The national digits for Wits' mobile inputs (the +27 country code is a
    separate prefilled control): '0825550142' / '+27 82 555 0142' → '825550142'."""
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("27") and len(digits) == 11:
        return digits[2:]
    return digits.lstrip("0")


class WitsAdapter(UniversityAdapter):
    university_id = WITS_UNIVERSITY_ID
    slug = WITS_SLUG

    def __init__(self) -> None:
        self._credentials: Optional[PortalCredentials] = None
        self._challenge_source: Optional[EmailChallengeSource] = None
        self._application_id: Optional[UUID] = None
        self._applicant_email: Optional[str] = None
        self._temp_id: Optional[str] = None

    def form_schema(self) -> dict:
        schema = load_field_schema()
        schema["university_id"] = str(self.university_id)
        return schema

    def set_challenge_source(
        self,
        source: EmailChallengeSource,
        *,
        application_id: UUID,
        applicant_email: str,
    ) -> None:
        """Wire the email-challenge source (called by background.py) — Wits
        emails the Temporary ID + temp password after Create Application ID."""
        self._challenge_source = source
        self._application_id = application_id
        self._applicant_email = applicant_email

    # --- login -----------------------------------------------------------------

    async def login(self, page: Page, credentials: PortalCredentials) -> None:
        """Create the Application ID (captcha decoded from the DOM), fetch the
        emailed Temporary ID + temp password via the challenge source, confirm
        the email + clear the forced password change (→ the derived permanent
        password), sign in, and begin/resume the Undergraduate application.

        Retries land here too: a duplicate-ID rejection of the create form
        still proceeds to the challenge (the inbox/student re-supplies the
        original Temporary ID), and when the confirm step reports the email as
        already verified the sign-in falls back to the derived password."""
        self._credentials = credentials
        await page.goto(LOGIN_URL, wait_until="domcontentloaded")
        await fluid.settle(page)
        await self._create_application_id(page, credentials)
        values = await self._fetch_login_values(page)
        temp_id = values["temporary_id"].strip()
        emailed = values["password"].strip()
        self._temp_id = temp_id
        email = (credentials.extra or {}).get("email", "")
        await self._confirm_temporary_password(page, email, temp_id, emailed)
        for password in (credentials.password, emailed):
            if await self._sign_in(page, temp_id, password):
                logger.info("Wits: logged in with temporary ID %s", temp_id)
                await self._begin_application(page, credentials)
                return
        raise AuthFailedError(
            f"Wits login failed for temporary ID {temp_id!r} with both the "
            "derived and the emailed password"
        )

    async def _create_application_id(
        self, page: Page, credentials: PortalCredentials
    ) -> None:
        """The Create Application ID form → captcha → the Confirm Application
        Details review page → 'Confirmation of Email' → OK (email sent)."""
        extra = credentials.extra
        required = ("first_name", "last_name", "date_of_birth", "id_number", "email")
        missing = [k for k in required if not extra.get(k)]
        if missing:
            raise AuthFailedError(
                f"Wits Create Application ID needs credentials.extra keys: {missing}"
            )
        await fluid.js_click(page, _REGISTER_BTN)
        await fluid.settle(page)
        # Nationality defaults to South Africa; selecting re-renders, so only
        # touch it for a non-default value. Every set settles (one-field rule).
        if (nationality := extra.get("nationality")) and nationality != "South Africa":
            await self._select_best(page, _CREATE["nationality"], nationality)
            await fluid.settle(page)
        await fluid.js_fill(page, _CREATE["national_id"], extra["id_number"])
        if title := extra.get("title"):
            await self._select_best(page, _CREATE["title"], str(title))
            await fluid.settle(page, 600)
        await fluid.js_fill(page, _CREATE["first_name"], extra["first_name"])
        if middles := extra.get("middle_names"):
            await fluid.js_fill(page, _CREATE["middle_names"], middles)
        await fluid.js_fill(page, _CREATE["last_name"], extra["last_name"])
        day, month, year = split_dob(extra["date_of_birth"])
        await fluid.js_select_text(page, _CREATE["dob_day"], day)
        await fluid.settle(page, 600)
        await fluid.js_select_text(page, _CREATE["dob_month"], month)
        await fluid.settle(page, 600)
        await fluid.js_fill(page, _CREATE["dob_year"], year)
        if gender := extra.get("gender"):
            # live set: Female / Gender Neutral / Male
            await self._select_best(page, _CREATE["gender"], str(gender))
            await fluid.settle(page, 600)
        await fluid.js_fill(page, _CREATE["email"], extra["email"])
        if phone := extra.get("phone"):
            await fluid.js_fill(page, _CREATE["mobile"], local_mobile(phone))
        await self._pass_security_check(page)

    async def _pass_security_check(self, page: Page) -> None:
        """Solve the six-image security code and walk Continue → the Confirm
        Application Details review → the Confirmation of Email OK. A rejected
        code re-renders fresh images, so the loop re-reads them. A duplicate-ID
        rejection is logged, not raised — the originally emailed login is
        still valid and the challenge source re-supplies it."""
        for attempt in range(_CAPTCHA_ATTEMPTS):
            code = await self._solve_captcha(page)
            await fluid.js_fill(page, _CREATE["security_code"], code)
            await fluid.js_click(page, _CONTINUE_BTN)
            await fluid.settle(page)
            alert = await fluid.read_alert(page) or ""
            if alert and re.search(r"security|code", alert, re.IGNORECASE):
                await fluid.answer_alert(page, "OK")
                logger.info(
                    "Wits security code rejected (attempt %d): %s", attempt + 1, alert
                )
                continue
            if alert:
                await fluid.answer_alert(page, "OK")
                logger.warning("Wits Create Application ID rejected: %s", alert)
                return
            # Confirm Application Details review page → second Continue.
            if await self._body_has(page, "Confirm Application Details"):
                await fluid.click_button(page, "Continue")
                await fluid.settle(page)
            # 'Confirmation of Email' — note the Temporary ID notice → OK.
            if await self._body_has(page, "Confirmation of Email"):
                await fluid.click_button(page, "OK")
                await fluid.settle(page)
            return
        raise ValidationFailedError(
            f"Wits rejected the security code {_CAPTCHA_ATTEMPTS} times",
            field="security_code",
        )

    async def _solve_captcha(self, page: Page) -> str:
        """Decode the six `VC_*` image filenames; fall back to the vision
        solver on an unknown scheme."""
        sources = await page.evaluate(
            """() => [...document.querySelectorAll('img')]
              .filter(i => /^Image\\d$/.test(i.alt))
              .sort((a, b) => a.alt.localeCompare(b.alt))
              .map(i => i.src)"""
        )
        code = decode_captcha_sources(sources or [], prefix=_CAPTCHA_PREFIX)
        if code:
            logger.info(
                "Wits captcha decoded from image filenames (%d chars)", len(code)
            )
            return code
        from app.automation.captcha import capture_element_image, get_captcha_solver

        solver = get_captcha_solver()
        if solver is None:
            raise HumanActionRequiredError(
                "Wits captcha could not be decoded and no vision solver is "
                "configured"
            )
        image = await capture_element_image(page, 'img[alt="Image1"] >> xpath=..')
        return await solver.solve(image, length=len(sources or []) or 6)

    async def _fetch_login_values(self, page: Page) -> dict[str, str]:
        if self._challenge_source is None or self._application_id is None:
            raise HumanActionRequiredError(
                "Wits emailed the Temporary ID + password but no "
                "EmailChallengeSource is wired"
            )
        request = ChallengeRequest(
            slug=self.slug,
            application_id=self._application_id,
            applicant_email=self._applicant_email or "",
            expected_fields=("temporary_id", "password"),
            # Verified body markers: literal 'TEMPORARY ACCESS ID:' /
            # 'PASSWORD:' lines (values 'T1867394' / '080312' on the spike).
            value_patterns={
                "temporary_id": r"TEMPORARY\s+ACCESS\s+ID\W{0,5}(T\d{6,9})",
                "password": r"PASSWORD\W{0,5}([A-Za-z0-9!@#$%^&*]{4,24})",
            },
            sender_hint="wits.ac.za",
            subject_hint=None,
        )
        return await self._challenge_source.get_values(request)

    async def _confirm_temporary_password(
        self, page: Page, email: str, temp_id: str, temp_password: str
    ) -> bool:
        """'Confirm Temporary Password' → User Details (email + Temporary ID +
        temp password) → forced password change → the derived permanent
        password. False when the portal rejects the step (e.g. the email was
        already confirmed on an earlier run — the permanent password then
        already works)."""
        assert self._credentials is not None
        await fluid.js_click(page, _CONFIRM_PWD_BTN)
        await fluid.settle(page)
        await fluid.js_fill(page, "#VC_OA_LOGIN_WRK_EMAIL_ADDR", email)
        await fluid.js_fill(page, _LOGIN_TEMP_ID, temp_id)
        await fluid.js_fill(page, _LOGIN_PASSWORD, temp_password)
        await fluid.js_click(page, _CONTINUE_BTN)
        await fluid.settle(page)
        alert = await fluid.read_alert(page)
        if alert:
            await fluid.answer_alert(page, "OK")
            logger.info("Wits email confirmation rejected: %s", alert)
            return False
        # 'Enter a new password' — labels verified; ids vary, so label-driven.
        new_password = self._credentials.password
        await self._fill_by_label(page, "Password", new_password)
        await self._fill_by_label(page, "Confirm Password", new_password)
        await fluid.click_button(page, "OK")
        await fluid.settle(page)
        # 'Your password has been successfully changed.' → OK → login page.
        if await fluid.button_visible(page, "OK"):
            await fluid.click_button(page, "OK")
            await fluid.settle(page)
        return True

    async def _sign_in(self, page: Page, temp_id: str, password: str) -> bool:
        await fluid.js_fill(page, _LOGIN_TEMP_ID, temp_id)
        await fluid.js_fill(page, _LOGIN_PASSWORD, password)
        await fluid.js_click(page, _LOGIN_BTN)
        await page.wait_for_load_state("domcontentloaded")
        await fluid.settle(page)
        alert = await fluid.read_alert(page)
        if alert:
            await fluid.answer_alert(page, "OK")
            logger.info("Wits sign-in rejected: %s", alert)
            return False
        return await self._body_has(page, "Apply for Admission")

    async def _begin_application(
        self, page: Page, credentials: PortalCredentials
    ) -> None:
        """Apply for Admission cascade (each select settles before the next):
        Begin New Application (resume on a retry) → Undergraduate Full-Time →
        the intake year → January → Continue → the Activity Guide wizard."""
        actions = await fluid.select_option_texts(page, _ACTION_SELECT)
        begin = next((a for a in actions if "begin" in a.lower()), None)
        resume = next((a for a in actions if "continue" in a.lower()), None)
        for action in (a for a in (begin, resume) if a):
            await fluid.js_select_text(page, _ACTION_SELECT, action)
            await fluid.settle(page)
            await self._select_best(page, _TYPE_SELECT, "Undergraduate Full-Time")
            await fluid.settle(page)
            wanted = (credentials.extra or {}).get("application_year")
            years = await fluid.select_option_texts(page, _YEAR_SELECT)
            year = next(
                (y for y in years if wanted and wanted in y),
                years[-1] if years else None,
            )
            if not year:
                raise PortalChangedError(
                    "Wits Academic Year offered no options", selector=_YEAR_SELECT
                )
            await fluid.js_select_text(page, _YEAR_SELECT, year)
            await fluid.settle(page)
            calendars = await fluid.select_option_texts(page, _CALENDAR_SELECT)
            await fluid.js_select_text(
                page, _CALENDAR_SELECT,
                "January" if "January" in calendars else calendars[-1],
            )
            await fluid.settle(page, 600)
            await fluid.click_button(page, "Continue")
            await page.wait_for_load_state("domcontentloaded")
            await fluid.settle(page, 3000)
            alert = await fluid.read_alert(page)
            if alert:
                await fluid.answer_alert(page, "OK")
                logger.info(
                    "Wits %r rejected: %s — trying the next action", action, alert
                )
                continue
            logger.info("Wits: entered the application wizard (%s)", action)
            return
        raise PortalChangedError(
            "Wits Apply for Admission accepted neither Begin New Application "
            "nor Continue Existing Application",
            selector=_ACTION_SELECT,
        )

    # --- fill_form: steps 2-13 ----------------------------------------------------

    async def fill_form(self, page: Page, mapping: FieldMapping) -> None:
        self._require_next_of_kin(mapping)
        # Step 1 Welcome is info-only (auto-saves) — advance off it.
        if await self._body_has(page, "Welcome to Wits University"):
            await self._next(page)
        await self._step_personal(page, mapping)
        await self._step_activities(page, mapping)
        await self._step_secondary(page, mapping)
        await self._step_tertiary(page, mapping)
        await self._step_choices(page, mapping)  # ends with Validate + Next
        await self._step_domicilium(page, mapping)
        await self._step_same_as_address(page, _ADDR2_SAME_AS, "8 Residential Address")
        await self._step_same_as_address(page, _ADDR3_SAME_AS, "9 Postal Address")
        await self._step_contact(page, mapping)
        await self._step_demographics(page, mapping)
        await self._step_next_of_kin(page, mapping)
        await self._step_emergency(page, mapping)
        logger.info("Wits fill_form: steps 2-13 complete")

    def _require_next_of_kin(self, mapping: FieldMapping) -> None:
        """Hard preconditions, checked up front for clear errors: Wits requires
        a next of kin whose mobile differs from the applicant's (the portal
        enforces both mobile and email; an identical email is simply dropped
        at fill time since the field is optional)."""
        if not mapping.get("nok_surname"):
            raise ValidationFailedError(
                "Wits requires a next of kin — capture a next_of_kin contact "
                "on the student profile first",
                field="nok_surname",
            )
        applicant = local_mobile(str(mapping.get("phone") or ""))
        nok = local_mobile(str(mapping.get("nok_phone") or ""))
        if not nok or nok == applicant:
            raise ValidationFailedError(
                "Wits requires a next-of-kin mobile number different from the "
                "applicant's",
                field="nok_phone",
            )

    async def _save(self, page: Page, step: str) -> None:
        """Header Save; an alert dialog means the portal rejected the step
        (surfaced verbatim, message code included)."""
        await fluid.click_button(page, "Save")
        await fluid.settle(page)
        alert = await fluid.read_alert(page)
        if alert:
            await fluid.answer_alert(page, "OK")
            raise ValidationFailedError(
                f"Wits rejected step {step}: {alert}", field=step
            )

    async def _next(self, page: Page, *, step: str = "") -> None:
        await fluid.click_button(page, "Next")
        await fluid.settle(page, 2500)
        alert = await fluid.read_alert(page)
        if alert:
            await fluid.answer_alert(page, "OK")
            raise ValidationFailedError(
                f"Wits blocked leaving step {step or '?'}: {alert}",
                field=step or None,
            )

    async def _save_and_next(self, page: Page, step: str) -> None:
        await self._save(page, step)
        await self._next(page, step=step)

    async def _step_personal(self, page: Page, mapping: FieldMapping) -> None:
        """Step 2: names/DOB/ID are read-only prefills from Create Application
        ID — only the Title and Gender selects are editable (label-driven; the
        page exposes no captured ids for them)."""
        if title := mapping.get("title"):
            await self._select_by_label_best(page, "Title", str(title))
            await fluid.settle(page, 600)
        if gender := mapping.get("gender"):
            await self._select_by_label_best(page, "Gender", str(gender))
            await fluid.settle(page, 600)
        await self._save_and_next(page, "2 Personal Details")

    async def _step_activities(self, page: Page, mapping: FieldMapping) -> None:
        await self._select_best(
            page, _ACTIVITY_SELECT, str(mapping.get("current_activity", "School"))
        )
        await fluid.settle(page, 600)
        await self._save_and_next(page, "3 Current Activities")

    async def _step_secondary(self, page: Page, mapping: FieldMapping) -> None:
        """Step 4. The South African / Current Grd 12 radios default correctly
        for matriculants and are left alone. Order: school modal → authority →
        exam year → month → number → the Gr11 grid → Copy Grade 11 Subjects
        (the Gr12 list, min 5 subjects, IS required — verified). Every control
        settles individually: a select's re-render discards sibling values set
        in the same pass (verified the hard way)."""
        if school := mapping.get("school"):
            await self._find_school(page, str(school))
        if authority := mapping.get("examining_authority"):
            await self._select_best(page, _AUTHORITY_SELECT, str(authority))
            await fluid.settle(page)
        if year := mapping.get("examination_year"):
            await fluid.js_fill(page, _EXAM_YEAR_INPUT, str(year))
            await fluid.settle(page, 800)
        await self._select_best(
            page, _EXAM_MONTH_SELECT, str(mapping.get("examination_month", "November"))
        )
        await fluid.settle(page, 800)
        if exam_number := mapping.get("exam_number"):
            await fluid.js_fill(page, _EXAM_NUMBER_INPUT, str(exam_number))
            await fluid.settle(page, 600)
        subjects = list(mapping.get("subjects") or [])
        if len(subjects) < 5:
            raise ValidationFailedError(
                "Wits requires at least 5 subjects on the Grade 11/12 grids — "
                f"the academic record carries {len(subjects)}",
                field="subjects",
            )
        await self._fill_grade11(page, subjects)
        await fluid.js_click(page, _COPY_GR11_BTN)
        await fluid.settle(page, 1500)
        await self._save_and_next(page, "4 Secondary Education")

    async def _find_school(self, page: Page, school: str) -> None:
        """Select School modal: search key → Search → pick the best row."""
        await fluid.click_button(page, "Select School")
        frame = await fluid.wait_modal_frame(page)
        await fluid.settle(page, 800)
        frame = await fluid.wait_modal_frame(page)
        # >=4 consecutive letters; the distinctive first word works best (UCT/UP)
        term = next((w for w in school.split() if len(w) >= 4), school[:10])
        await fluid.js_fill(frame, _SCHOOL_SEARCH_KEY, term)
        await fluid.js_click(frame, _SCHOOL_SEARCH_BTN)
        await fluid.settle(page, 1500)
        frame = fluid.modal_frame(page)
        if frame is None:
            raise PortalChangedError(
                "Wits school modal closed before results", selector="Select School"
            )
        rows = await self._select_rows(frame)
        texts = [r["text"] for r in rows]
        chosen = best_option_match(school, texts)
        if not chosen:
            raise ValidationFailedError(
                f"no Wits school result matched {school!r} (rows: {texts[:6]})",
                field="school",
            )
        index = next(r["index"] for r in rows if r["text"] == chosen)
        await fluid.js_click(frame, f'[id="VC_OA_WRK_SELECT${index}"]')
        await fluid.wait_modal_closed(page)
        await fluid.settle(page)

    async def _fill_grade11(self, page: Page, subjects: list[dict]) -> None:
        """The Final Grade 11 Results grid: 10 pre-rendered rows of subject
        dropdown + mark input, filled top-down to preserve school-report
        order. Option texts truncate at ~30 chars ('Afrikaans First Additional
        Lan') — the fuzzy match absorbs that."""
        for index, subject in enumerate(subjects):
            name = str(subject.get("name", ""))
            mark = subject.get("percentage")
            if mark is None:
                raise ValidationFailedError(
                    f"subject {name!r} has no mark", field="subjects"
                )
            subject_sel = _GR11_SUBJECT.format(n=index)
            options = await fluid.select_option_texts(page, subject_sel)
            chosen = best_option_match(name, options)
            if not chosen:
                raise ValidationFailedError(
                    f"no Wits subject option matched {name!r}", field="subjects"
                )
            await fluid.js_select_text(page, subject_sel, chosen)
            await fluid.settle(page, 800)
            await fluid.js_fill(page, _GR11_MARK.format(n=index), str(mark))
            await fluid.settle(page, 500)

    async def _step_tertiary(self, page: Page, mapping: FieldMapping) -> None:
        applied = str(mapping.get("tertiary_studies", "No")).lower() in (
            "yes", "true", "1",
        )
        await fluid.set_switch(page, _TERTIARY_FLAG, applied)
        await fluid.settle(page, 600)
        await self._save_and_next(page, "5 Tertiary Education")

    async def _step_choices(self, page: Page, mapping: FieldMapping) -> None:
        """Step 6: up to 3 programmes. Render quirk (verified): only the last
        programme select is visible on first render — all three appear after
        the first server round-trip — so a throwaway selection may be needed
        before Programme 1 can be targeted, and stray slots are cleared after.
        Ends with Validate Application: the Next button stays hidden until it
        passes, and eligibility ('subject requirements') is enforced here."""
        programme = str(mapping.get("programme") or "")
        if not programme:
            raise ValidationFailedError("no programme to apply for", field="programme")
        await self._ensure_choice_blocks(page)
        await self._pick_programme(page, 1, programme, required=True)
        for slot, key in ((2, "programme_second"), (3, "programme_third")):
            if wanted := mapping.get(key):
                await self._pick_programme(page, slot, str(wanted), required=False)
        await self._clear_stray_choices(
            page,
            keep={1}
            | {2 for _ in [1] if mapping.get("programme_second")}
            | {3 for _ in [1] if mapping.get("programme_third")},
        )
        await self._save(page, "6 Study Choices")
        await self._validate_application(page)
        await self._next(page, step="6 Study Choices")

    async def _ensure_choice_blocks(self, page: Page) -> None:
        """Make all three programme blocks render: when Programme 1's select
        isn't visible yet, make a throwaway selection in whichever block is
        (the spike landed it in Programme 3) — it's cleared afterwards."""
        if await fluid.is_visible(page, _PROG_SELECT.format(n=1)):
            return
        kicked = await page.evaluate(
            """() => {
              const sel = [...document.querySelectorAll(
                  'select[id^="VC_OA_WRK_VC_ACAD_PROG"]')]
                .find(s => s.offsetParent !== null);
              if (!sel) return false;
              const opt = [...sel.options].find(o => o.text.trim());
              if (!opt) return false;
              sel.value = opt.value;
              sel.dispatchEvent(new Event('change', {bubbles: true}));
              return true;
            }"""
        )
        if not kicked:
            raise PortalChangedError(
                "no Wits Academic Program dropdown found", selector="ACAD_PROG"
            )
        await fluid.settle(page, 2000)

    async def _pick_programme(
        self, page: Page, slot: int, programme: str, *, required: bool
    ) -> None:
        prog_sel = _PROG_SELECT.format(n=slot)
        options = await fluid.select_option_texts(page, prog_sel)
        chosen = best_option_match(programme, options)
        if not chosen:
            if required:
                raise ValidationFailedError(
                    f"no open Wits programme matched {programme!r}",
                    field="programme",
                )
            logger.info("Wits choice %d skipped — no match for %r", slot, programme)
            return
        await fluid.js_select_text(page, prog_sel, chosen)
        await fluid.settle(page, 1500)
        # The Academic Plan cascade offers a single non-blank option — it must
        # still be explicitly selected (verified live).
        plan_sel = _PLAN_SELECT.format(n=slot)
        plans = await fluid.select_option_texts(page, plan_sel)
        plan = best_option_match(programme, plans) or (plans[-1] if plans else None)
        if plan:
            await fluid.js_select_text(page, plan_sel, plan)
            await fluid.settle(page, 800)
        logger.info("Wits choice %d: %s / %s", slot, chosen, plan)

    async def _clear_stray_choices(self, page: Page, *, keep: set[int]) -> None:
        """Reset programme slots the mapping didn't ask for (the render-quirk
        workaround can leave a throwaway value in one — repeating a code is a
        portal error)."""
        for slot in (2, 3):
            if slot in keep:
                continue
            cleared = await page.evaluate(
                """(sel) => {
                  const el = document.querySelector(sel);
                  if (!el || !el.value) return false;
                  el.value = '';
                  el.dispatchEvent(new Event('change', {bubbles: true}));
                  return true;
                }""",
                _PROG_SELECT.format(n=slot),
            )
            if cleared:
                await fluid.settle(page, 1200)

    async def _validate_application(self, page: Page) -> None:
        """Validate Application gates steps 7+. Failure → alert (32030, 346)
        'Errors found on multiple pages' → the Validation Messages modal,
        whose rows (page | message, including 'You do not meet the subject
        requirements for …' eligibility failures) are surfaced verbatim."""
        await fluid.click_button(page, "Validate Application")
        await fluid.settle(page, 3500)
        alert = await fluid.read_alert(page)
        if not alert:
            return
        await fluid.answer_alert(page, "OK")
        await fluid.settle(page, 1500)
        frame = fluid.modal_frame(page)
        messages = None
        if frame is not None:
            try:
                messages = await frame.evaluate(
                    "() => document.body.innerText.replace(/\\s+/g, ' ')"
                    ".trim().slice(0, 600)"
                )
            except Exception:  # noqa: BLE001
                pass
        raise ValidationFailedError(
            f"Wits validation failed: {messages or alert}", field="validate"
        )

    async def _step_domicilium(self, page: Page, mapping: FieldMapping) -> None:
        """Step 7: Country defaults to South Africa; Suburb + the Address
        Search link resolve the read-only City/Postal Code/Province."""
        if line1 := mapping.get("address_line_1"):
            await fluid.js_fill(page, _ADDR1_LINE1, str(line1))
            await fluid.settle(page, 800)
        if line2 := mapping.get("address_line_2"):
            await fluid.js_fill(page, _ADDR1_LINE2, str(line2))
            await fluid.settle(page, 800)
        suburb = str(mapping.get("suburb") or "")
        if not suburb:
            raise ValidationFailedError(
                "no suburb to resolve Wits' Address Search", field="suburb"
            )
        await fluid.js_fill(page, _ADDR1_SUBURB, suburb)
        await fluid.settle(page, 800)
        await self._resolve_address_search(
            page, suburb, str(mapping.get("postal_code") or "")
        )
        await self._save_and_next(page, "7 Domicilium Address")

    async def _resolve_address_search(
        self, page: Page, suburb: str, postal: str
    ) -> None:
        """The Address Search link opens a modal of Suburb|City|Postal|Province
        rows resolved from the typed suburb; rows carrying the profile's postal
        code are preferred."""
        await fluid.js_click(page, _ADDRESS_LOOKUP)
        frame = await fluid.wait_modal_frame(page)
        await fluid.settle(page, 1200)
        frame = await fluid.wait_modal_frame(page)
        rows = await self._select_rows(frame)
        if not rows:
            raise ValidationFailedError(
                f"Wits Address Search returned no rows for suburb {suburb!r}",
                field="suburb",
            )
        candidates = [r for r in rows if postal and postal in r["text"]] or rows
        texts = [r["text"] for r in candidates]
        chosen = best_option_match(suburb, texts) or texts[0]
        index = next(r["index"] for r in candidates if r["text"] == chosen)
        await fluid.js_click(frame, f'[id="VC_OA_WRK_SELECT${index}"]')
        await fluid.wait_modal_closed(page)
        await fluid.settle(page, 800)

    async def _step_same_as_address(
        self, page: Page, selector: str, step: str
    ) -> None:
        """Steps 8/9: the 'Same as Other Address' select offers Domicilium
        only (verified) — engaged instead of re-entering the address."""
        await fluid.js_select_text(page, selector, "Domicilium")
        await fluid.settle(page, 1200)
        await self._save_and_next(page, step)

    async def _step_contact(self, page: Page, mapping: FieldMapping) -> None:
        """Step 10: email + mobile prefill from registration; re-asserted from
        the mapping when present."""
        if phone := mapping.get("phone"):
            await fluid.js_fill(page, _CONTACT_MOBILE, local_mobile(str(phone)))
            await fluid.settle(page, 600)
        await self._save_and_next(page, "10 Contact Details")

    async def _step_demographics(self, page: Page, mapping: FieldMapping) -> None:
        """Step 11. Live option sets: Population Group is Asian/Black/Coloured/
        Indian/White ('Black', not 'African'); 'Nil Declared' is the religious
        non-answer. The detailed disability toggle list is a doc'd capture gap
        — the Yes/No answer passes through."""
        for selector, key, fallback in (
            (_DEMO_MARITAL, "marital_status", "Single"),
            (_DEMO_POPULATION, "population_group", None),
            (_DEMO_LANGUAGE, "home_language", None),
            (_DEMO_RELIGION, "religious_affiliation", "Nil Declared"),
            (_DEMO_DISABLED, "has_disability", "No"),
        ):
            value = mapping.get(key) or fallback
            if value is None:
                continue
            await self._select_best(page, selector, str(value))
            await fluid.settle(page, 800)
        if str(mapping.get("has_disability", "No")).lower() == "yes":
            logger.warning(
                "Wits disability detail capture is a doc'd gap — answered Yes "
                "without specifics"
            )
        await self._save_and_next(page, "11 Demographic Details")

    async def _step_next_of_kin(self, page: Page, mapping: FieldMapping) -> None:
        """Step 12. Portal-enforced: the NOK email + mobile must differ from
        the applicant's — the mobile is preconditioned in fill_form; an
        identical email is dropped (the field is optional)."""
        if title := mapping.get("nok_title"):
            await self._select_best(page, _NOK_TITLE, str(title))
            await fluid.settle(page, 800)
        if initial := mapping.get("nok_initial"):
            await fluid.js_fill(page, _NOK_INITIAL, str(initial))
            await fluid.settle(page, 500)
        await fluid.js_fill(page, _NOK_SURNAME, str(mapping.get("nok_surname")))
        await fluid.settle(page, 500)
        await fluid.js_fill(
            page, _NOK_MOBILE, local_mobile(str(mapping.get("nok_phone")))
        )
        await fluid.settle(page, 500)
        if relationship := mapping.get("nok_relationship"):
            await self._select_best(page, _NOK_RELATION, str(relationship))
            await fluid.settle(page, 800)
        nok_email = str(mapping.get("nok_email") or "")
        applicant = str(mapping.get("email") or "")
        if nok_email and nok_email.lower() != applicant.lower():
            await fluid.js_fill(page, _NOK_EMAIL, nok_email)
            await fluid.settle(page, 500)
        elif nok_email:
            logger.info("Wits NOK email equals the applicant's — left blank")
        await fluid.js_select_text(page, _NOK_SAME_AS, "Domicilium")
        await fluid.settle(page, 1200)
        await self._save_and_next(page, "12 Next of Kin")

    async def _step_emergency(self, page: Page, mapping: FieldMapping) -> None:
        """Step 13: ticking 'Use same details as Next of Kin' hides the
        name/phone inputs (copied server-side); the relationship still needs a
        value. fill_form ends here — saved, not advanced (upload_documents
        owns the step-14 indemnity boundary)."""
        await fluid.set_switch(page, _EMERGENCY_SAME_AS, True)
        await fluid.settle(page, 1500)
        relationship = str(mapping.get("nok_relationship") or "")
        if relationship and await fluid.is_visible(page, _EMERGENCY_RELATION):
            await self._select_best(page, _EMERGENCY_RELATION, relationship)
            await fluid.settle(page, 800)
        await self._save(page, "13 Emergency Contact")

    # --- documents ------------------------------------------------------------------

    async def upload_documents(
        self, page: Page, documents: list[DocumentRef]
    ) -> None:
        """Step 16 (rows verified for Current Grd 12: 0 = ID copy, 1 = Final
        GR11 Results). The step-14 indemnity sits on the way: it is accepted
        ONLY when the student's agreement consent is recorded
        (credentials.extra['agreement_consented'], set by background.py from
        `applications.agreement_consent_at`) — otherwise the run parks before
        it and the uploads wait with the submit, per the consent decision."""
        by_type = {d.doc_type.upper(): d for d in documents}
        id_doc = by_type.get("ID_COPY")
        results = by_type.get("GRADE11_RESULTS") or by_type.get("MATRIC_RESULTS")
        if id_doc is None:
            raise ValidationFailedError(
                "Wits requires the certified ID copy — none provided",
                field="documents",
            )
        if results is None:
            raise ValidationFailedError(
                "Wits requires the Grade 11 results (or matric certificate) — "
                "none provided",
                field="documents",
            )
        await self._next(page, step="13 Emergency Contact")  # → 14 Indemnity
        if await self._body_has(page, "Indemnity & Undertaking"):
            accepted = await self._body_has(
                page, "Indemnity and Undertaking Complete"
            )
            if not accepted:
                consented = (
                    (self._credentials.extra or {}).get("agreement_consented")
                    == "true"
                    if self._credentials
                    else False
                )
                if not consented:
                    logger.info(
                        "Wits: agreement consent not recorded — parked before "
                        "the indemnity; documents wait with the submit"
                    )
                    return
                await fluid.js_click(page, _INDEMNITY_ACCEPT)
                await fluid.settle(page, 2000)
            await self._next(page, step="14 Indemnity")  # → 15 Payment (info)
            await self._next(page, step="15 Payment")  # → 16 Documents
        for doc in (id_doc, results):
            row = _UPLOAD_ROWS[doc.doc_type.upper()]
            await self._upload_row(page, row, doc)
        await self._save(page, "16 Documents")

    async def _upload_row(self, page: Page, row: int, doc: DocumentRef) -> None:
        """One Add → PeopleSoft File Attachment modal → My Device (native
        chooser) → Upload → 'Upload Complete' → Done (all verified live)."""
        await fluid.js_click(page, _UPLOAD_ADD.format(n=row))
        frame = await fluid.wait_modal_frame(page)
        await fluid.settle(page, 800)
        frame = await fluid.wait_modal_frame(page)
        async with page.expect_file_chooser() as chooser_info:
            await fluid.js_click(frame, _MODAL_MY_DEVICE)
        chooser = await chooser_info.value
        await chooser.set_files(doc.local_path)
        await fluid.settle(page, 800)
        frame = await fluid.wait_modal_frame(page)
        await fluid.js_click(frame, _MODAL_UPLOAD)
        try:
            await frame.get_by_text("Upload Complete").wait_for(timeout=30_000)
        except Exception as exc:  # noqa: BLE001
            raise ValidationFailedError(
                f"Wits upload of {doc.filename!r} did not complete",
                field="documents",
            ) from exc
        await fluid.js_click(frame, _MODAL_DONE)
        await fluid.wait_modal_closed(page)
        await fluid.settle(page, 600)

    # --- submit / verify ----------------------------------------------------------

    async def submit(self, page: Page) -> None:
        """Step 17: 'Submit Application to the University'. Only reachable
        with the agreement consent recorded (the gate in background.py), which
        also means upload_documents accepted the indemnity and left the run on
        step 16. Payment (R100) is deliberately NOT a gate — it happens after
        submission with the issued person/student number as reference."""
        await self._next(page, step="16 Documents")  # → 17 Submit
        if not await fluid.is_visible(page, _SUBMIT_BTN):
            raise PortalChangedError(
                "Wits Submit button not visible on step 17", selector=_SUBMIT_BTN
            )
        await fluid.js_click(page, _SUBMIT_BTN)
        await fluid.settle(page, 1500)
        # a confirm dialog may interpose — accept it [VERIFY at first live submit]
        await fluid.answer_alert(page, "Yes")
        await page.wait_for_load_state("domcontentloaded")
        await fluid.settle(page, 3000)
        alert = await fluid.read_alert(page)
        if alert:
            await fluid.answer_alert(page, "OK")
            if re.search(r"error|unable", alert, re.IGNORECASE):
                raise ValidationFailedError(
                    f"Wits rejected the submission: {alert}", field="submit"
                )

    async def verify_submission(self, page: Page) -> SubmissionConfirmation:
        """Success marker: submission issues a **person/student number** (also
        the payment reference) and locks further edits. **[VERIFY LIVE]** at
        the first supervised submit — the post-submit page was deliberately
        never captured (the spike parked on the Step 17 screen)."""
        body = ""
        try:
            body = await page.evaluate(
                "() => document.body.innerText.slice(0, 4000)"
            ) or ""
        except Exception:  # noqa: BLE001
            logger.warning("Wits verify_submission: page unreadable")
        ref_match = re.search(
            r"(?:person|student)\s+number\W{0,5}([A-Z0-9]{5,12})",
            body, re.IGNORECASE,
        )
        marker = next(
            (line.strip() for line in body.splitlines()
             if "submitted" in line.lower()),
            None,
        )
        return SubmissionConfirmation(
            reference=ref_match.group(1) if ref_match else None, marker=marker
        )

    # --- shared helpers ---------------------------------------------------------------

    async def _select_best(self, page: Page, selector: str, wanted: str) -> str:
        """Select the live option best matching free text (exact first)."""
        options = await fluid.select_option_texts(page, selector)
        chosen = wanted if wanted in options else best_option_match(wanted, options)
        if not chosen:
            raise ValidationFailedError(
                f"no Wits option in {selector} matched {wanted!r} "
                f"(live: {options[:10]})",
                field=selector,
            )
        await fluid.js_select_text(page, selector, chosen)
        return chosen

    async def _select_by_label_best(
        self, page: Page, label: str, wanted: str
    ) -> None:
        """Label-driven select for the few controls without captured ids
        (step 2's Title/Gender), fuzzy-matched against the live options."""
        options = await page.evaluate(
            """(label) => {
              const sel = [...document.querySelectorAll('select')]
                .find(s => s.offsetParent !== null && s.labels && s.labels[0]
                      && s.labels[0].textContent.trim() === label);
              return sel
                ? [...sel.options].map(o => o.text.trim()).filter(Boolean)
                : null;
            }""",
            label,
        )
        if options is None:
            raise PortalChangedError(
                f"select labelled {label!r} not found", selector=label
            )
        chosen = wanted if wanted in options else best_option_match(wanted, options)
        if not chosen:
            raise ValidationFailedError(
                f"no Wits option for {label!r} matched {wanted!r} "
                f"(live: {options[:10]})",
                field=label,
            )
        await page.evaluate(
            """([label, txt]) => {
              const sel = [...document.querySelectorAll('select')]
                .find(s => s.offsetParent !== null && s.labels && s.labels[0]
                      && s.labels[0].textContent.trim() === label);
              const opt = [...sel.options].find(o => o.text.trim() === txt);
              sel.value = opt.value;
              sel.dispatchEvent(new Event('change', {bubbles: true}));
            }""",
            [label, chosen],
        )

    async def _fill_by_label(self, page: Page, label: str, value: str) -> None:
        ok = await page.evaluate(
            """([label, val]) => {
              const inp = [...document.querySelectorAll('input')]
                .find(i => i.offsetParent !== null && !i.disabled
                      && i.labels && i.labels[0]
                      && i.labels[0].textContent.trim() === label);
              if (!inp) return false;
              inp.value = val;
              inp.dispatchEvent(new Event('change', {bubbles: true}));
              return true;
            }""",
            [label, str(value)],
        )
        if not ok:
            raise PortalChangedError(
                f"input labelled {label!r} not found", selector=label
            )

    async def _body_has(self, page: Page, text: str) -> bool:
        try:
            return bool(await page.evaluate(
                """(t) => document.body.innerText.replace(/\\s+/g, ' ')
                       .includes(t)""",
                text,
            ))
        except Exception:  # noqa: BLE001
            return False

    @staticmethod
    async def _select_rows(frame: Frame) -> list[dict]:
        """Result rows of a VC_OA modal grid: [{index, text}] keyed off the
        per-row VC_OA_WRK_SELECT$n button."""
        rows = await frame.evaluate(
            """() => [...document.querySelectorAll('[id^="VC_OA_WRK_SELECT$"]')]
              .map(btn => {
                const tr = btn.closest('tr');
                return {
                  index: parseInt(btn.id.split('$')[1], 10),
                  text: ((tr && tr.innerText) || '').replace(/\\s+/g, ' ')
                          .replace(/^\\d*\\s*Select /, '').trim(),
                };
              })"""
        )
        return rows or []
