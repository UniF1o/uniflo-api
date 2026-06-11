"""University of Pretoria adapter (PeopleSoft Online Application Portal, OAP).

Everything here encodes the live walkthrough of 2026-06-11 (new-application
form → captcha → emailed Application-ID login → password change → all sections
→ Verify "No errors" → stop at Payment): see docs/phase-3/portal-research/up.md
"Live spike findings" for the verified behaviours and element ids.

UP shares the PeopleSoft AJAX model with Fluid (UCT), so the `fluid` helpers
drive it: stale handles after every server round-trip, `ptModFrame_N` modal
iframes, `[role=alertdialog]` dialogs in the PARENT document with stable
message codes, overlay-intercepted clicks needing JS. UP-specific behaviours:

- **Captcha decodes from the DOM** — six `<img>` tags whose filenames spell the
  answer (`UP_L_R_1.JPG` → lowercase "r"). The vision solver is the fallback.
- **Two-phase login**: the new-application form makes UP email an Application
  ID + password (fetched via the EmailChallengeSource); first login forces a
  password change (set to the derived permanent password, nothing persisted).
- **Eligibility gate at choice selection** (msg 31100, 501): rejected rows are
  skipped and the next-best matching open programme is tried.
- **Subjects want NSC level + percent**, and the percent dropdown only offers
  the chosen level's band — the level is derived from the percent first.
- **Payment (R300) sits before Apply** and Uniflo never pays: `submit()` stops
  with HumanActionRequiredError unless the portal shows the fee as paid.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from playwright.async_api import Frame, Page

from app.automation import fluid
from app.automation.adapters.uct import best_option_match
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
# `adapters.slug_for_website`, like UCT).
UP_UNIVERSITY_ID = UUID("00000000-0000-0000-0000-000000000a11")
UP_SLUG = "up"

PORTAL_URL = (
    "https://upnet.up.ac.za/psc/upapply/EMPLOYEE/SA/c/"
    "UP_OAP_MENU.UP_OAP_LOGIN_FL.GBL"
)

# Toolbar (every wizard page) — img-only buttons, so ids are the only handle.
_SAVE_BTN = "#UP_FAE_WRK_SAVE_PB"
_NEXT_BTN = "#UP_FAE_WRK_NEXT_PB"

# Section controls (all verified live 2026-06-11).
_DOB_INPUT = "#UP_OAP_WRK_BIRTHDATE"  # native <input type=date> — ISO fill
_POSTCODE_SEARCH_KEY = "#UP_POSTSRCH_WRK_SEARCH_KEY"
_POSTCODE_SEARCH_BTN = "UP_POSTSRCH_WRK_SEARCH_BTN"
_SCHOOL_OPENER = "#UP_FAE_WRK_CHANGE_CODE"  # same id opens choice 1 on Study Choice
_SCHOOL_SEARCH_KEY = "#UP_FAE_WRK_SEARCH_KEY"
_SCHOOL_SEARCH_BTN = "UP_FAE_WRK_SEARCH_BTN"
_CHOICE1_OPENER = "#UP_FAE_WRK_CHANGE_CODE"
_CHOICE2_OPENER = "#UP_FAE_WRK_CHANGE_CODE_ATP"
_CHOICE_SEARCH_BTN = "UP_OAP_WRK_SEARCH_BTN"  # differs from the school modal's!
_CHOICE1_VALUE = "#UP_FAE_WRK_UP_CHOICE1"
_CHOICE2_VALUE = "#UP_FAE_WRK_UP_CHOICE2"
_RESIDENCE_SELECT = "#UP_FAE_STG_GENL_UP_HOUSING_OPT"
_NSFAS_CHECKBOX = "#UP_FAE_STG_GENL_UP_NSFAS"
_FUNDING_CHECKBOX = "#UP_FAE_STG_GENL_UP_FIN_AID"
_DECLARATION_SWITCH = "#UP_FAE_STG_GENL_CONFIRMED"
_VERIFY_BTN = "#UP_FAE_WRK_VERIFY"
_APPLY_BTN = "#UP_FAE_WRK_APPLY"  # NEVER clicked outside the gated submit()
# File Attachment modal ids literally start with '#' — attribute selectors.
_MODAL_MY_DEVICE = "#PT_ATTACH_MYDEVICE"
_MODAL_UPLOAD = '[id="#ICUpload"]'
_MODAL_DONE = '[id="#ICOK"]'

# Documentation upload rows are fixed indices (add button per row).
_UPLOAD_ROWS = {
    "ID_COPY": 0,
    "GRADE11_RESULTS": 2,
    "MATRIC_RESULTS": 3,
    "TRANSCRIPT": 9,
}

_FIELDS_PATH = Path(__file__).with_name("up.fields.json")

def load_field_schema() -> dict:
    import json

    return json.loads(_FIELDS_PATH.read_text(encoding="utf-8"))


def decode_captcha_sources(sources: list[str], *, prefix: str = "UP") -> Optional[str]:
    """The captcha answer spelled by the six image URLs, or None when any
    filename doesn't match the known scheme (→ fall back to the vision solver).

    Filenames are `{prefix}_{case}_{char}_{seq}.JPG` ('L' = lowercase, verified
    live; 'U' presumed uppercase; digits carry their own glyph). The same
    scheme ships on Wits with prefix "VC" — hence the parameter."""
    pattern = re.compile(
        rf"{re.escape(prefix)}_([A-Z])_([A-Za-z0-9])_\d+\.JPG", re.IGNORECASE
    )
    chars: list[str] = []
    for src in sources:
        match = pattern.search(src or "")
        if not match:
            return None
        marker, char = match.group(1).upper(), match.group(2)
        if marker == "L":
            chars.append(char.lower())
        elif marker == "U":
            chars.append(char.upper())
        else:  # digits / unknown markers carry the glyph verbatim
            chars.append(char)
    return "".join(chars) or None


def nsc_level(percent: int) -> int:
    """NSC achievement level for a percentage (10-point bands, 7 = 80%+). The
    portal's Percent dropdown only offers the selected level's band, so the
    level must be derived from the stored percentage — not entered separately."""
    if percent >= 80:
        return 7
    if percent < 30:
        return 1
    return percent // 10 - 1


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def rank_choice_rows(programme: str, rows: list[str]) -> list[str]:
    """Open study-choice rows ranked by how well they match the requested
    programme (same prefix-tolerant token coverage as `best_option_match`).
    Rows without 'Open' are excluded — their closing date has passed. Ranked
    (not single-best) because the eligibility gate may reject the top row and
    the next candidate (e.g. the extended 5-year variant) should be tried."""
    want = _tokens(programme)
    if not want:
        return []
    scored: list[tuple[float, int, str]] = []
    for row in rows:
        if " open" not in f" {row.lower()} ":
            continue
        have = _tokens(row)
        hits = sum(
            1 for w in want
            if any(h.startswith(w[:4]) or w.startswith(h[:4]) for h in have)
        )
        coverage = hits / len(want)
        if coverage >= 0.6:
            scored.append((coverage, -len(have), row))
    scored.sort(reverse=True)
    return [row for _, _, row in scored]


class UPAdapter(UniversityAdapter):
    university_id = UP_UNIVERSITY_ID
    slug = UP_SLUG

    def __init__(self) -> None:
        self._credentials: Optional[PortalCredentials] = None
        self._challenge_source: Optional[EmailChallengeSource] = None
        self._application_id: Optional[UUID] = None
        self._applicant_email: Optional[str] = None

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
        """Wire the email-challenge source (called by background.py) — UP emails
        the Application ID + initial password after the new-application form."""
        self._challenge_source = source
        self._application_id = application_id
        self._applicant_email = applicant_email

    # --- login -----------------------------------------------------------------

    async def login(self, page: Page, credentials: PortalCredentials) -> None:
        """Submit the new-application form (captcha decoded from the DOM), fetch
        the emailed Application ID + password via the challenge source, sign in,
        and clear the forced password change (→ the derived permanent password).

        Retries land here too: if UP rejects the new-application form (e.g. the
        ID number already has an application), the run still proceeds to the
        challenge — the student/inbox re-supplies the original login, and the
        derived password is tried first in case the change already happened."""
        self._credentials = credentials
        await page.goto(PORTAL_URL, wait_until="domcontentloaded")
        await fluid.settle(page)
        await self._start_new_application(page, credentials)
        values = await self._fetch_login_values(page)
        app_id = values["application_id"].strip()
        emailed = values["password"].strip()
        for password in (emailed, credentials.password):
            if await self._try_login(page, app_id, password):
                logger.info("UP: logged in to application %s", app_id)
                return
        raise AuthFailedError(
            f"UP login failed for application {app_id!r} with both the emailed "
            "and the derived password"
        )

    async def _start_new_application(
        self, page: Page, credentials: PortalCredentials
    ) -> None:
        extra = credentials.extra
        required = ("first_name", "last_name", "date_of_birth", "id_number", "email")
        missing = [k for k in required if not extra.get(k)]
        if missing:
            raise AuthFailedError(
                f"UP new application needs credentials.extra keys: {missing}"
            )
        await self._select_by_label(page, "I want to", "start new application")
        await fluid.settle(page)
        await self._dismiss_privacy_notice(page)
        await self._select_by_label(page, "Career of Study", "Undergraduate")
        await fluid.settle(page)
        await self._pick_first_year(page, extra.get("application_year"))
        await self._fill_by_label(page, "Last Name", extra["last_name"])
        await self._fill_by_label(page, "First Name", extra["first_name"])
        await self._fill_by_label(page, "Email Address", extra["email"])
        await self._fill_by_label(page, "Confirm Email Address", extra["email"])
        await fluid.js_fill(page, _DOB_INPUT, _iso_date(extra["date_of_birth"]))
        await self._select_by_label(page, "Identify me by", "SA ID Number")
        await fluid.settle(page)
        await self._fill_by_label(
            page, "South African National ID", extra["id_number"]
        )
        code = await self._solve_captcha(page)
        await self._fill_by_label(page, "*Security Code (case sensitive)", code)
        await fluid.click_button(page, "Go")
        await fluid.settle(page)
        alert = await fluid.read_alert(page)
        if alert and "details sent to your email" in alert:
            await fluid.answer_alert(page, "OK")
            await fluid.settle(page, 800)
            return
        if alert:
            # Don't sink the run — a duplicate-application rejection still
            # leaves the original emailed login valid (relay re-supplies it).
            await fluid.answer_alert(page, "OK")
            logger.warning("UP new-application form rejected: %s", alert)

    async def _pick_first_year(self, page: Page, wanted: Optional[str]) -> None:
        """First Year of Study cascades from Career; the open intake year is
        normally the single non-blank option."""
        options = await self._options_by_label(page, "First Year of Study")
        choice = wanted if wanted in options else (options[-1] if options else None)
        if not choice:
            raise PortalChangedError(
                "UP First Year of Study offered no options",
                selector="First Year of Study",
            )
        await self._select_by_label(page, "First Year of Study", choice)
        await fluid.settle(page, 800)

    async def _dismiss_privacy_notice(self, page: Page) -> None:
        """The 'Data privacy notice' modal precedes the form (ptModFrame, OK)."""
        frame = fluid.modal_frame(page)
        if frame is None:
            return
        try:
            text = await frame.evaluate("() => document.body.innerText.slice(0, 300)")
        except Exception:  # noqa: BLE001
            return
        if "privacy" in (text or "").lower():
            await fluid.click_button(frame, "OK")
            await fluid.wait_modal_closed(page)

    async def _solve_captcha(self, page: Page) -> str:
        """Decode the six captcha images from their filenames; fall back to the
        vision solver on an unknown scheme; raise for the human-in-the-loop path
        when neither is available."""
        sources = await page.evaluate(
            """() => [...document.querySelectorAll('img')]
              .filter(i => /^Image\\d$/.test(i.alt))
              .sort((a, b) => a.alt.localeCompare(b.alt))
              .map(i => i.src)"""
        )
        code = decode_captcha_sources(sources or [])
        if code:
            logger.info("UP captcha decoded from image filenames (%d chars)", len(code))
            return code
        from app.automation.captcha import capture_element_image, get_captcha_solver

        solver = get_captcha_solver()
        if solver is None:
            raise HumanActionRequiredError(
                "UP captcha could not be decoded and no vision solver is configured"
            )
        image = await capture_element_image(page, 'img[alt="Image1"] >> xpath=..')
        return await solver.solve(image, length=len(sources or []) or 6)

    async def _fetch_login_values(self, page: Page) -> dict[str, str]:
        if self._challenge_source is None or self._application_id is None:
            raise HumanActionRequiredError(
                "UP emailed the Application ID + password but no "
                "EmailChallengeSource is wired"
            )
        request = ChallengeRequest(
            slug=self.slug,
            application_id=self._application_id,
            applicant_email=self._applicant_email or "",
            expected_fields=("application_id", "password"),
            value_patterns={
                "application_id": r"\b(T\d{6,9})\b",
                "password": r"[Pp]assword\W{0,3}([A-Za-z0-9!@#$%^&*]{6,24})",
            },
            sender_hint="up.ac.za",
            subject_hint=None,
        )
        return await self._challenge_source.get_values(request)

    async def _try_login(self, page: Page, app_id: str, password: str) -> bool:
        """One sign-in attempt. Clears the forced first-login password change
        (→ the derived permanent password). True once the wizard is reached."""
        await self._select_by_label(
            page, "I want to", "login to continue / view study application"
        )
        await fluid.settle(page)
        await self._fill_by_label(page, "Application ID", app_id)
        await self._fill_by_label(page, "Password", password)
        await fluid.click_button(page, "Go")
        await fluid.settle(page)
        alert = await fluid.read_alert(page)
        if alert:
            await fluid.answer_alert(page, "OK")
            logger.info("UP login attempt rejected: %s", alert)
            return False
        frame = fluid.modal_frame(page)
        if frame is not None:
            await self._change_password(page, frame)
        return await self._in_wizard(page)

    async def _change_password(self, page: Page, frame: Frame) -> None:
        """'Confirm email and change password' modal: old password is prefilled;
        set the permanent (derived) password."""
        assert self._credentials is not None
        new_password = self._credentials.password
        try:
            await frame.get_by_role(
                "textbox", name="New Password", exact=True
            ).fill(new_password)
            await frame.get_by_role(
                "textbox", name="Confirm New Password"
            ).fill(new_password)
            await frame.get_by_role("button", name="OK").click()
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                "UP change-password modal did not accept input",
                selector="Confirm email and change password",
            ) from exc
        await page.wait_for_load_state("domcontentloaded")
        await fluid.settle(page)

    async def _in_wizard(self, page: Page) -> bool:
        try:
            return bool(await page.evaluate(
                "() => document.body.innerText.includes('Overall Application Status')"
            ))
        except Exception:  # noqa: BLE001
            return False

    # --- fill_form: Personal Information → General Details ------------------------

    async def fill_form(self, page: Page, mapping: FieldMapping) -> None:
        await self._section_personal(page, mapping)
        await self._section_contact(page, mapping)
        await self._section_demographics(page, mapping)
        await self._section_tertiary(page, mapping)
        await self._section_secondary(page, mapping)
        await self._section_study_choice(page, mapping)
        await self._section_general(page, mapping)
        logger.info("UP fill_form: sections complete through General Details")

    async def _goto_section(self, page: Page, name: str) -> None:
        ok = await page.evaluate(
            """(name) => {
              const items = [...document.querySelectorAll('li')];
              const hit = items.find(li => (li.textContent || '').trim().startsWith(name));
              if (!hit) return false;
              hit.click();
              return true;
            }""",
            name,
        )
        if not ok:
            raise PortalChangedError(
                f"left-nav section {name!r} not found", selector=name
            )
        await fluid.settle(page)

    async def _save_section(self, page: Page, section: str) -> None:
        """Toolbar Save; an alert dialog means the portal rejected the section
        (alerts carry stable message codes, surfaced verbatim)."""
        await fluid.js_click(page, _SAVE_BTN)
        await fluid.settle(page)
        alert = await fluid.read_alert(page)
        if alert:
            await fluid.answer_alert(page, "OK")
            raise ValidationFailedError(
                f"UP rejected {section}: {alert}", field=section
            )

    async def _section_personal(self, page: Page, mapping: FieldMapping) -> None:
        await self._goto_section(page, "Personal Information")
        if title := mapping.get("title"):
            await self._select_label_best(page, "Title", str(title))
        if preferred := mapping.get("preferred_name"):
            await self._fill_by_label(page, "Preferred First Name", str(preferred))
        await self._save_section(page, "Personal Information")

    async def _section_contact(self, page: Page, mapping: FieldMapping) -> None:
        await self._goto_section(page, "Contact Details")
        if line1 := mapping.get("address_line_1"):
            await self._fill_by_label(page, "Address Line 1", str(line1))
        if phone := mapping.get("phone"):
            await self._fill_by_label(page, "Mobile Number", str(phone))
        await self._set_city(page, mapping)
        await self._save_section(page, "Contact Details")

    async def _set_city(self, page: Page, mapping: FieldMapping) -> None:
        """The City/Postal/Province inputs are disabled — the postcode modal is
        mandatory. Broad terms pop '>300 matches — refine' (msg 31200, 8), so
        queries go suburb → postal code. Street-Code rows are preferred (it's a
        street address) and matched on the postal code when present."""
        suburb = str(mapping.get("suburb") or "").strip()
        city = str(mapping.get("city") or "").strip()
        postal = str(mapping.get("postal_code") or "").strip()
        queries = [q for q in (suburb, postal, city) if q]
        if not queries:
            raise ValidationFailedError(
                "no suburb/postal code to resolve UP's city lookup",
                field="postal_code",
            )
        for query in queries:
            rows = await self._postcode_rows(page, query)
            if rows is None:  # >300 matches — refine with the next query
                continue
            chosen = self._pick_postcode_row(rows, suburb or city, postal)
            if chosen is None:
                continue
            frame = fluid.modal_frame(page)
            if frame is None:
                raise PortalChangedError(
                    "postcode modal closed before a row was selected",
                    selector=_POSTCODE_SEARCH_KEY,
                )
            await fluid.js_click(frame, f"#SELECT_BTN\\${chosen['index']}")
            await fluid.wait_modal_closed(page)
            await fluid.settle(page, 800)
            return
        raise ValidationFailedError(
            f"no UP postcode row matched suburb={suburb!r} postal={postal!r}",
            field="postal_code",
        )

    async def _postcode_rows(
        self, page: Page, query: str
    ) -> Optional[list[dict]]:
        """Open the modal, search, and return the result rows — or None when
        the portal asks for a refined query (>300 matches)."""
        await self._click_labeled(page, "Select City / Postcode")
        frame = await fluid.wait_modal_frame(page)
        await fluid.settle(page, 800)
        frame = await fluid.wait_modal_frame(page)
        await fluid.js_fill(frame, _POSTCODE_SEARCH_KEY, query)
        await self._modal_submit(frame, _POSTCODE_SEARCH_BTN)
        await fluid.settle(page)
        alert = await fluid.read_alert(page)
        if alert and "refine your search" in alert:
            await fluid.answer_alert(page, "OK")
            await fluid.settle(page, 800)
            return None
        frame = fluid.modal_frame(page)
        if frame is None:
            return []
        return await self._select_rows(frame)

    @staticmethod
    def _pick_postcode_row(
        rows: list[dict], place: str, postal: str
    ) -> Optional[dict]:
        street_rows = [r for r in rows if "street code" in r["text"].lower()]
        candidates = street_rows or rows
        if postal:
            candidates = [r for r in candidates if postal in r["text"]] or candidates
        if not candidates:
            return None
        if place:
            texts = [r["text"] for r in candidates]
            match = best_option_match(place, texts)
            if match:
                return next(r for r in candidates if r["text"] == match)
        return candidates[0]

    async def _section_demographics(self, page: Page, mapping: FieldMapping) -> None:
        await self._goto_section(page, "Demographic Details")
        for label, key in (
            ("Gender", "gender"),
            ("Home Language", "home_language"),
            ("Population Group", "population_group"),
            ("Tell us more", "tell_us_more"),
        ):
            if value := mapping.get(key):
                await self._select_label_best(page, label, str(value))
                await fluid.settle(page, 600)
        # Disability stays off for MVP (the Disability Detail modal needs data
        # the profile doesn't carry yet — surfaced as a doc'd gap).
        await self._save_section(page, "Demographic Details")

    async def _section_tertiary(self, page: Page, mapping: FieldMapping) -> None:
        await self._goto_section(page, "Tertiary Education")
        await self._select_label_best(
            page,
            "Were you prev enrolled at a University, a Univ of Technology or a "
            "Post School Technical College?",
            str(mapping.get("prev_enrolled", "No")),
        )
        await self._save_section(page, "Tertiary Education")

    async def _section_secondary(self, page: Page, mapping: FieldMapping) -> None:
        """Cascade order matters: Final School Year → Examining Authority →
        School Grades Type / Highest grade → Exemption Type; the school search
        modal; then the subjects grid (level before percent — the percent
        dropdown only offers the level's band)."""
        await self._goto_section(page, "Secondary Education")
        if year := mapping.get("final_school_year"):
            await self._select_label_best(page, "Final School Year", str(year))
            await fluid.settle(page)
        if authority := mapping.get("examining_authority"):
            await self._select_label_best(page, "Examining Authority", str(authority))
            await fluid.settle(page)
        if school := mapping.get("school"):
            await self._find_school(page, str(school))
        if grades_type := mapping.get("school_grades_type"):
            await self._select_label_best(page, "School Grades Type", str(grades_type))
            await fluid.settle(page, 800)
        if highest := mapping.get("highest_grade"):
            await self._select_label_best(page, "Highest grade completed", str(highest))
            await fluid.settle(page, 800)
        if exam_number := mapping.get("exam_number"):
            await self._fill_by_label(page, "Examination Number", str(exam_number))
        if exemption := mapping.get("exemption_type"):
            await self._select_label_best(page, "Exemption Type", str(exemption))
            await fluid.settle(page, 800)
        subjects = list(mapping.get("subjects") or [])
        if not subjects:
            raise ValidationFailedError(
                "UP requires the subject grid — no subjects on the academic record",
                field="subjects",
            )
        await self._fill_subjects(page, subjects)
        await self._save_section(page, "Secondary Education")

    async def _find_school(self, page: Page, school: str) -> None:
        await fluid.js_click(page, _SCHOOL_OPENER)
        frame = await fluid.wait_modal_frame(page)
        await fluid.settle(page, 800)
        frame = await fluid.wait_modal_frame(page)
        term = next((w for w in school.split() if len(w) >= 4), school[:10])
        await fluid.js_fill(frame, _SCHOOL_SEARCH_KEY, term)
        await self._modal_submit(frame, _SCHOOL_SEARCH_BTN)
        await fluid.settle(page)
        frame = fluid.modal_frame(page)
        if frame is None:
            raise PortalChangedError(
                "school modal closed before results", selector=_SCHOOL_OPENER
            )
        rows = await self._select_rows(frame)
        texts = [r["text"] for r in rows]
        match = best_option_match(school, texts)
        if not match:
            raise ValidationFailedError(
                f"no UP school result matched {school!r} (rows: {texts[:6]})",
                field="school",
            )
        chosen = next(r for r in rows if r["text"] == match)
        await fluid.js_click(frame, f"#SELECT_BTN\\${chosen['index']}")
        await fluid.wait_modal_closed(page)
        await fluid.settle(page)

    async def _fill_subjects(self, page: Page, subjects: list[dict]) -> None:
        """Rows are pre-rendered (`SCHOOL_CRSE_NBR$n` / `CRSE_GRADE_INPUT$n` /
        `CRSE_GRADE_OFF$n`), entered top-down to preserve school-report order.
        The captured NSC level is used when the record carries one; otherwise
        it derives from the percentage band."""
        for index, subject in enumerate(subjects):
            name = str(subject.get("name", ""))
            try:
                percent = int(subject.get("percentage"))
            except (TypeError, ValueError):
                raise ValidationFailedError(
                    f"subject {name!r} has no numeric percentage", field="subjects"
                ) from None
            subject_sel = f"#SCHOOL_CRSE_NBR\\${index}"
            options = await fluid.select_option_texts(page, subject_sel)
            chosen = best_option_match(name, options)
            if not chosen:
                raise ValidationFailedError(
                    f"no UP subject option matched {name!r}", field="subjects"
                )
            await fluid.js_select_text(page, subject_sel, chosen)
            await fluid.settle(page, 800)
            level = subject.get("nsc_level") or nsc_level(percent)
            await fluid.js_select_text(
                page, f"#CRSE_GRADE_INPUT\\${index}", str(level)
            )
            await self._wait_visible(page, f"#CRSE_GRADE_OFF\\${index}")
            await fluid.js_select_text(
                page, f"#CRSE_GRADE_OFF\\${index}", str(percent)
            )
            await fluid.settle(page, 600)

    async def _section_study_choice(self, page: Page, mapping: FieldMapping) -> None:
        """First (+ optional second) choice via the search modal. The portal
        runs a live minimum-admissions check on selection (msg 31100, 501) —
        rejected rows are skipped and the next-ranked open row is tried, so an
        extended-programme variant can absorb a too-low APS."""
        await self._goto_section(page, "Study Choice")
        programme = str(mapping.get("programme") or "")
        if not programme:
            raise ValidationFailedError("no programme to apply for", field="programme")
        accepted = await self._pick_choice(
            page, _CHOICE1_OPENER, _CHOICE1_VALUE, programme
        )
        logger.info("UP first choice accepted: %s", accepted)
        if second := mapping.get("programme_second"):
            try:
                accepted2 = await self._pick_choice(
                    page, _CHOICE2_OPENER, _CHOICE2_VALUE, str(second)
                )
                logger.info("UP second choice accepted: %s", accepted2)
            except ValidationFailedError as exc:
                logger.warning("UP second choice skipped: %s", exc.message)
        await self._save_section(page, "Study Choice")

    async def _pick_choice(
        self, page: Page, opener: str, value_input: str, programme: str
    ) -> str:
        """Try ranked matching rows until the eligibility gate accepts one."""
        term = max(_tokens(programme), key=len, default=programme)
        tried: set[str] = set()
        for _ in range(4):  # eligibility rejections close the modal — reopen
            await fluid.js_click(page, opener)
            frame = await fluid.wait_modal_frame(page)
            await fluid.settle(page, 800)
            frame = await fluid.wait_modal_frame(page)
            await fluid.js_fill(frame, _SCHOOL_SEARCH_KEY, term)
            await self._modal_submit(frame, _CHOICE_SEARCH_BTN)
            await fluid.settle(page)
            frame = fluid.modal_frame(page)
            if frame is None:
                raise PortalChangedError(
                    "study-choice modal closed before results", selector=opener
                )
            rows = await self._select_rows(frame)
            ranked_texts = [
                t for t in rank_choice_rows(programme, [r["text"] for r in rows])
                if t not in tried
            ]
            if not ranked_texts:
                raise ValidationFailedError(
                    f"no open UP programme matched {programme!r} "
                    f"(or every match was rejected by the eligibility check)",
                    field="programme",
                )
            candidate = next(r for r in rows if r["text"] == ranked_texts[0])
            tried.add(candidate["text"])
            await fluid.js_click(frame, f"#SELECT_BTN\\${candidate['index']}")
            await fluid.settle(page)
            alert = await fluid.read_alert(page)
            if alert and "Minimum admissions" in alert:
                await fluid.answer_alert(page, "OK")
                await fluid.settle(page, 800)
                continue  # gate rejected — reopen and try the next candidate
            if alert:
                await fluid.answer_alert(page, "OK")
                raise ValidationFailedError(
                    f"UP rejected the study choice: {alert}", field="programme"
                )
            if fluid.modal_frame(page) is not None:
                await fluid.wait_modal_closed(page)
            value = await page.evaluate(
                "(sel) => { const el = document.querySelector(sel);"
                " return el ? el.value : null; }",
                value_input,
            )
            if value:
                return candidate["text"]
        raise ValidationFailedError(
            f"every matching UP programme for {programme!r} was rejected by the "
            "minimum-admissions check",
            field="programme",
        )

    async def _section_general(self, page: Page, mapping: FieldMapping) -> None:
        await self._goto_section(page, "General Details")
        residence = str(mapping.get("wants_residence", "No"))
        await fluid.js_select_text(page, _RESIDENCE_SELECT, residence)
        await fluid.settle(page, 600)
        nsfas = str(mapping.get("applying_nsfas", "No")).lower() in ("yes", "true", "1")
        funding = str(mapping.get("up_funding", "No")).lower() in ("yes", "true", "1")
        await fluid.set_switch(page, _NSFAS_CHECKBOX, nsfas)
        await fluid.set_switch(page, _FUNDING_CHECKBOX, funding)
        await self._save_section(page, "General Details")

    # --- documents -----------------------------------------------------------------

    async def upload_documents(
        self, page: Page, documents: list[DocumentRef]
    ) -> None:
        """Documentation section: SA ID is mandatory; school results take the
        Grade 11 final results OR the Grade 12 certificate (matriculants → Gr11).
        Upload rows are fixed indices; each runs the File Attachment modal."""
        by_type = {d.doc_type.upper(): d for d in documents}
        sa_id = by_type.get("ID_COPY")
        results = by_type.get("GRADE11_RESULTS") or by_type.get("MATRIC_RESULTS")
        if sa_id is None:
            raise ValidationFailedError(
                "UP requires the SA ID upload — none provided", field="documents"
            )
        if results is None:
            raise ValidationFailedError(
                "UP requires Grade 11 results or the Grade 12 certificate — "
                "none provided",
                field="documents",
            )
        await self._goto_section(page, "Documentation")
        for doc in (sa_id, results):
            row = _UPLOAD_ROWS[doc.doc_type.upper()]
            await self._upload_row(page, row, doc)
        await self._save_section(page, "Documentation")

    async def _upload_row(self, page: Page, row: int, doc: DocumentRef) -> None:
        await fluid.js_click(page, f"#UP_FAE_WRK_FILE_CREATE1_LBL\\${row}")
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
                f"UP upload of {doc.filename!r} did not complete",
                field="documents",
            ) from exc
        await fluid.js_click(frame, _MODAL_DONE)
        await fluid.wait_modal_closed(page)
        await fluid.settle(page, 600)

    # --- submit / verify --------------------------------------------------------------

    async def submit(self, page: Page) -> None:
        """Declaration (consent already recorded upstream — the gate in
        background.py won't reach this without it) → Verify (must pass with
        'No errors', msg 31100, 388) → Payment check → Apply.

        ⚠️ The Apply button is ENABLED even while the R300 fee is unpaid
        (verified live) — Uniflo never pays, so an unpaid application stops
        here with HumanActionRequiredError instead of applying."""
        await self._goto_section(page, "Declaration")
        await fluid.set_switch(page, _DECLARATION_SWITCH, True)
        await self._save_section(page, "Declaration")
        await self._goto_section(page, "Verify")
        await fluid.js_click(page, _VERIFY_BTN)
        await fluid.settle(page, 3000)
        alert = await fluid.read_alert(page) or ""
        await fluid.answer_alert(page, "OK")
        if "No errors" not in alert:
            errors = await self._verify_errors(page)
            raise ValidationFailedError(
                f"UP verification failed: {errors or alert or 'no alert shown'}",
                field="verify",
            )
        await self._goto_section(page, "Payment")
        status = await page.evaluate(
            """() => {
              const m = document.body.innerText.match(
                /Payment Status\\s*\\n?\\s*(Not Paid|Paid)/i);
              return m ? m[1] : null;
            }"""
        )
        if (status or "").lower() != "paid":
            raise HumanActionRequiredError(
                "UP's R300 application fee is unpaid — the student must pay "
                "(card or EFT + proof upload) before the application can be "
                f"submitted (portal payment status: {status!r})"
            )
        await self._goto_section(page, "Apply")
        await fluid.js_click(page, _APPLY_BTN)
        await page.wait_for_load_state("domcontentloaded")
        await fluid.settle(page, 3000)
        alert = await fluid.read_alert(page)
        if alert:
            await fluid.answer_alert(page, "OK")

    async def _verify_errors(self, page: Page) -> Optional[str]:
        try:
            return await page.evaluate(
                """() => {
                  const i = document.body.innerText.indexOf('Error Message');
                  return i > -1
                    ? document.body.innerText.slice(i, i + 600).trim()
                    : null;
                }"""
            )
        except Exception:  # noqa: BLE001
            return None

    async def verify_submission(self, page: Page) -> SubmissionConfirmation:
        """Success marker: the header's Overall Application Status flips away
        from 'Must still verify & apply'. The Application ID (T-number) in the
        header is the portal reference. **[VERIFY LIVE]** at the first real
        supervised submit — the post-Apply page was never captured (no fake
        submissions)."""
        body = ""
        try:
            body = await page.evaluate(
                "() => document.body.innerText.slice(0, 4000)"
            ) or ""
        except Exception:  # noqa: BLE001
            logger.warning("UP verify_submission: page unreadable")
        status_match = re.search(r"Overall Application Status:\s*([^\n]+)", body)
        status = (status_match.group(1).strip() if status_match else None)
        ref_match = re.search(r"\((T\d{6,9})\)", body)
        reference = ref_match.group(1) if ref_match else None
        if status and "must still verify" in status.lower():
            raise PortalChangedError(
                f"UP application status did not flip after Apply (still {status!r})",
                selector="Overall Application Status",
            )
        return SubmissionConfirmation(reference=reference, marker=status)

    # --- shared label/modal helpers --------------------------------------------------

    async def _options_by_label(self, page: Page, label: str) -> list[str]:
        options = await page.evaluate(
            """(label) => {
              const sel = [...document.querySelectorAll('select')]
                .find(s => s.labels && s.labels[0]
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
        return options

    async def _select_by_label(self, page: Page, label: str, text: str) -> None:
        result = await page.evaluate(
            """([label, txt]) => {
              const sel = [...document.querySelectorAll('select')]
                .find(s => s.labels && s.labels[0]
                      && s.labels[0].textContent.trim() === label);
              if (!sel) return {error: 'missing'};
              const opt = [...sel.options].find(o => o.text.trim() === txt);
              if (!opt) return {error: 'no-option',
                                options: [...sel.options].map(o => o.text.trim())};
              sel.value = opt.value;
              sel.dispatchEvent(new Event('change', {bubbles: true}));
              return {ok: true};
            }""",
            [label, str(text)],
        )
        if result.get("error") == "missing":
            raise PortalChangedError(
                f"select labelled {label!r} not found", selector=label
            )
        if result.get("error") == "no-option":
            raise PortalChangedError(
                f"select {label!r} has no option {text!r} "
                f"(live: {result.get('options')})",
                selector=label,
            )

    async def _select_label_best(self, page: Page, label: str, wanted: str) -> str:
        """Select the live option best matching free text (exact first)."""
        options = await self._options_by_label(page, label)
        if wanted in options:
            chosen = wanted
        else:
            chosen = best_option_match(wanted, options)
        if not chosen:
            raise ValidationFailedError(
                f"no UP option for {label!r} matched {wanted!r} (live: {options[:10]})",
                field=label,
            )
        await self._select_by_label(page, label, chosen)
        return chosen

    async def _fill_by_label(self, page: Page, label: str, value: str) -> None:
        ok = await page.evaluate(
            """([label, val]) => {
              const inp = [...document.querySelectorAll('input')]
                .find(i => !i.disabled && i.labels && i.labels[0]
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

    async def _click_labeled(self, page: Page, label: str) -> None:
        """Click a toolbar/icon control by aria-label or title (the inner <a>
        when the label sits on a wrapper) — pointer clicks get intercepted by
        the modal mask, so this is a JS click."""
        ok = await page.evaluate(
            """(label) => {
              const nodes = [...document.querySelectorAll('*')].filter(n =>
                n.getAttribute &&
                (n.getAttribute('aria-label') === label || n.title === label));
              for (const node of nodes) {
                const btn = node.matches('a,button,input')
                  ? node : node.querySelector('a,button,input');
                if (btn) { btn.click(); return true; }
              }
              return false;
            }""",
            label,
        )
        if not ok:
            raise PortalChangedError(
                f"control labelled {label!r} not found", selector=label
            )

    @staticmethod
    async def _modal_submit(frame: Frame, action_id: str) -> None:
        """Run a PeopleSoft action inside the modal's own window —
        `submitAction_win0` survives the overlay mask that eats pointer clicks."""
        await frame.evaluate(
            "(id) => submitAction_win0(document.win0, id)", action_id
        )

    @staticmethod
    async def _select_rows(frame: Frame) -> list[dict]:
        """Result-grid rows with their SELECT_BTN index: [{index, text}]."""
        rows = await frame.evaluate(
            """() => [...document.querySelectorAll('tr')]
              .map(tr => {
                const btn = tr.querySelector('[id^="SELECT_BTN$"]');
                if (!btn) return null;
                return {
                  index: parseInt(btn.id.split('$')[1], 10),
                  text: (tr.innerText || '').replace(/\\s+/g, ' ')
                          .replace(/^Select /, '').trim(),
                };
              })
              .filter(Boolean)"""
        )
        return rows or []

    @staticmethod
    async def _wait_visible(page: Page, selector: str, timeout_s: float = 8.0) -> None:
        import asyncio

        deadline = asyncio.get_event_loop().time() + timeout_s
        while not await fluid.is_visible(page, selector):
            if asyncio.get_event_loop().time() >= deadline:
                raise PortalChangedError(
                    f"{selector} did not appear", selector=selector
                )
            await page.wait_for_timeout(300)


def _iso_date(value: str) -> str:
    """credentials.extra carries dd/mm/yyyy (the UCT account format); UP's
    native date input wants ISO."""
    value = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    return datetime.strptime(value, "%d/%m/%Y").strftime("%Y-%m-%d")
