"""University of Cape Town adapter (PeopleSoft Fluid).

Everything here encodes the live walkthrough of 2026-06-10 (account creation →
OTP → all 16 steps → stop on Step 16): see docs/phase-3/portal-research/uct.md
"Live spike findings" for the verified behaviours and field ids, and
`app.automation.fluid` for the shared Fluid driving patterns.

**Selector strategy — PeopleSoft ids via JS, label fallback.** Approach C
(accessibility tree) *does* work on Fluid, but ids are used as the primary
handle because Fluid re-renders the DOM after most server round-trips (stale
element handles) and a couple of fields (the account-creation email inputs)
carry no accessible name at all. All driving goes through `fluid.py`'s
re-querying JS helpers.

**Email challenges.** The account-creation OTP (and the post-submit applicant
number, when the imap source is active) arrive by email — the adapter blocks on
its `EmailChallengeSource` (wired by `set_challenge_source`) while the browser
waits in place on the portal's modal.
"""

import logging
import re
from pathlib import Path
from typing import Optional
from uuid import UUID

from playwright.async_api import Page

from app.automation import fluid
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

# The seeded `universities` ids are uuid4 (no fixed value to pin), so the
# wiring resolves UCT by website domain (`adapters.slug_for_website`). This
# placeholder satisfies the base-class contract and is never a real row id.
UCT_UNIVERSITY_ID = UUID("00000000-0000-0000-0000-0000000000c7")
UCT_SLUG = "uct"

# Entry points (verified live — the create-account page is publicly reachable).
CREATE_ACCOUNT_URL = (
    "https://publicaccess.uct.ac.za/psc/public/EMPLOYEE/SA/c/"
    "UCT_PUBLIC_MENU.UCT_ONL_HOME_FL.GBL"
)
LOGIN_URL = (
    "https://studentsonline.uct.ac.za/psc/students/EMPLOYEE/SA/c/"
    "NUI_FRAMEWORK.PT_LANDINGPAGE.GBL?LP=UCT_ONLINE_APP&cmd=login"
)

# Account-creation email inputs have NO accessible name — id is the only handle.
_ACC_EMAIL = "#SCC_NUR_WRK_EMAILID"
_ACC_EMAIL_REPEAT = "#SCC_NUR_WRK_EMAIL_ADDR\\$10\\$"

# Subject grids (step 5): row N opens the slot-N subject modal.
_GR11_ROW = "#UCT_SCHLCRSE_H1\\$0_row_{n}"
_GR12_ROW = "#UCT_SCHLCRSE_H11\\$0_row_{n}"
_SUBJECT_MODAL_CONFIRM = "#UCT_DERIVED_ONL_CONFIRM_PB"
_GR12_APRIL = "#UCT_OA_COURSES_CRSE_GRADE_INPUT1"

# Step 14 upload + step 16 submit controls.
_UPLOAD_BUTTON = "#SCC_ATCH_WRK_ATTACHADD\\$0"
_SUBMIT_BUTTON = "#SCC_TM_ADM_WRK_SCC_TM_ACCEPT"

_FIELDS_PATH = Path(__file__).with_name("uct.fields.json")


def load_field_schema() -> dict:
    import json

    return json.loads(_FIELDS_PATH.read_text(encoding="utf-8"))


def order_subjects_for_slots(subjects: list[dict]) -> list[dict]:
    """Order subjects to match UCT's slot-semantic grid: row 0 accepts only a
    Home Language, row 1 the second language (1st Additional/HL), row 2 the
    Maths variant, row 3 Life Orientation, rows 4+ the open elective list."""
    def slot(subject: dict) -> int:
        name = str(subject.get("name", "")).lower()
        if "home lang" in name:
            return 0
        if "additional" in name or "1st add" in name or "2nd add" in name:
            return 1
        if "math" in name:
            return 2
        if "orientation" in name:
            return 3
        return 4

    return sorted(subjects, key=slot)


def best_option_match(target: str, options: list[str]) -> Optional[str]:
    """Pick the dropdown option that best matches free text. Scored by how many
    of the *requested* tokens the option covers (so a short request like 'Civil
    Engineering' can still match a long degree title), abbreviation-tolerant
    (prefix match: 'Additional' ~ 'Add'), ties broken by the shorter option
    ('SOSHANGUVE' over 'SOSHANGUVE BLOCK AA'). Returns None below a confidence
    floor — better surfaced than guessed."""
    def tokens(text: str) -> list[str]:
        return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]

    want = tokens(target)
    if not want:
        return None
    best: Optional[str] = None
    best_key = (0.0, 0)
    for option in options:
        have = tokens(option)
        if not have:
            continue
        hits = sum(
            1 for w in want
            if any(h.startswith(w[:4]) or w.startswith(h[:4]) for h in have)
        )
        coverage = hits / len(want)
        key = (coverage, -len(have))
        if key > best_key:
            best, best_key = option, key
    return best if best_key[0] >= 0.6 else None


class UCTAdapter(UniversityAdapter):
    university_id = UCT_UNIVERSITY_ID
    slug = UCT_SLUG

    def __init__(self) -> None:
        self._credentials: Optional[PortalCredentials] = None
        self._challenge_source: Optional[EmailChallengeSource] = None
        self._application_id: Optional[UUID] = None
        self._applicant_email: Optional[str] = None

    def form_schema(self) -> dict:
        """Field catalog for the AI mapping layer, with the runtime-resolved
        university id injected (the JSON ships with null — seeded ids are
        uuid4, resolved by domain at wiring time)."""
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
        """Wire the email-challenge source (called by background.py). Without
        one, hitting the OTP raises HumanActionRequiredError instead."""
        self._challenge_source = source
        self._application_id = application_id
        self._applicant_email = applicant_email

    # --- pipeline -------------------------------------------------------------

    async def login(self, page: Page, credentials: PortalCredentials) -> None:
        """Sign in; on first contact, create the account (clearing the email
        OTP via the challenge source) — the portal auto-redirects back to the
        sign-in afterwards. Then enter the Undergraduate application (start a
        new one or resume the existing instance). Account fields (names, DOB,
        ID, email) travel in `credentials.extra` since the runtime hands
        `fill_form`'s mapping over only after login."""
        self._credentials = credentials
        await page.goto(LOGIN_URL, wait_until="domcontentloaded")
        await fluid.settle(page)
        if not await self._try_sign_in(page, credentials):
            await self._create_account(page, credentials)
            await fluid.settle(page)
            if not await self._try_sign_in(page, credentials):
                raise AuthFailedError("UCT sign-in failed after account creation")
        await self._enter_application(page, credentials)

    async def _try_sign_in(self, page: Page, credentials: PortalCredentials) -> bool:
        """Attempt the studentsonline sign-in. True once the Online Application
        homepage is reached; False if the credentials are unknown (no account
        yet). Raises AuthFailedError on an explicit rejection of a known user."""
        if not await fluid.is_visible(page, "input[id*='userid' i], #userid"):
            # not on the sign-in form — maybe already logged in
            return await self._on_homepage(page)
        try:
            await page.fill("input[id*='userid' i]", credentials.username)
            await page.fill("input[id*='pwd' i], input[type='password']",
                            credentials.password)
            await page.click("input[type='submit'], button[type='submit'], #login")
        except Exception:  # noqa: BLE001 — fall back to role-based targeting
            await page.get_by_role("textbox", name="User ID").fill(credentials.username)
            await page.get_by_role("textbox", name="Password").fill(credentials.password)
            await page.get_by_role("button", name=re.compile("Sign In")).click()
        await page.wait_for_load_state("domcontentloaded")
        await fluid.settle(page)
        return await self._on_homepage(page)

    async def _on_homepage(self, page: Page) -> bool:
        try:
            return bool(await page.evaluate(
                "() => document.body.innerText.includes('Online Application Homepage')"
            ))
        except Exception:  # noqa: BLE001
            return False

    async def _create_account(
        self, page: Page, credentials: PortalCredentials
    ) -> None:
        """Create the applicant account on publicaccess (verified live):
        fill → Create → OTP modal (iframe) → Verify → auto-redirect to login."""
        extra = credentials.extra
        required = ("first_name", "last_name", "date_of_birth", "email")
        missing = [k for k in required if not extra.get(k)]
        # The account "National ID / International Passport Number" field takes
        # either — international applicants have a passport, not an SA ID.
        national_id = extra.get("id_number") or extra.get("passport_number")
        if not national_id:
            missing.append("id_number/passport_number")
        if missing:
            raise AuthFailedError(
                f"UCT account creation needs credentials.extra keys: {missing}"
            )
        await page.goto(CREATE_ACCOUNT_URL, wait_until="domcontentloaded")
        await fluid.settle(page)
        await page.get_by_role(
            "textbox", name=re.compile(r"\*First Name")
        ).fill(extra["first_name"])
        await page.get_by_role(
            "textbox", name=re.compile(r"\*Last Name")
        ).fill(extra["last_name"])
        # dd/mm/yyyy typed directly works — no calendar needed (verified live)
        await page.get_by_role(
            "textbox", name=re.compile(r"\*Date of Birth")
        ).fill(extra["date_of_birth"])
        await page.get_by_role(
            "textbox", name=re.compile(r"National ID")
        ).fill(national_id)
        await fluid.js_fill(page, _ACC_EMAIL, extra["email"])
        await fluid.js_fill(page, _ACC_EMAIL_REPEAT, extra["email"])
        await page.get_by_role(
            "textbox", name=re.compile(r"\*Username")
        ).fill(credentials.username)
        await page.get_by_role(
            "textbox", name=re.compile(r"^\*Password$")
        ).fill(credentials.password)
        await page.get_by_role(
            "textbox", name=re.compile(r"\*Confirm Password")
        ).fill(credentials.password)
        await fluid.click_button(page, "Create")
        await self._clear_otp(page)
        await page.wait_for_load_state("domcontentloaded")

    async def _clear_otp(self, page: Page) -> None:
        """The 'Confirm Email Address' modal (iframe): fetch the emailed OTP via
        the challenge source while the browser waits in place, type, Verify."""
        frame = await fluid.wait_modal_frame(page, timeout_s=20)
        if self._challenge_source is None or self._application_id is None:
            raise HumanActionRequiredError(
                "UCT emailed an OTP but no EmailChallengeSource is wired"
            )
        request = ChallengeRequest(
            slug=self.slug,
            application_id=self._application_id,
            applicant_email=self._applicant_email or "",
            expected_fields=("otp",),
            value_patterns={"otp": r"\b(\d{4,8})\b"},
            sender_hint="uct.ac.za",
            subject_hint=None,
        )
        values = await self._challenge_source.get_values(request)
        await frame.get_by_role("textbox", name=re.compile("OTP")).fill(values["otp"])
        await frame.get_by_role("button", name="Verify OTP").click()

    async def _enter_application(
        self, page: Page, credentials: PortalCredentials
    ) -> None:
        """Homepage → Undergraduate tile → start page → pick the intake year →
        Start Application (+ Yes confirm) or resume the in-progress one."""
        try:
            await page.get_by_label("Undergraduate").get_by_role("button").click()
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                "Undergraduate tile not found on the application homepage",
                selector="Undergraduate",
            ) from exc
        await page.wait_for_load_state("domcontentloaded")
        await fluid.settle(page)
        year = credentials.extra.get("application_year")
        if year:
            try:
                await fluid.js_select_text(
                    page, "select", year, contains=True
                )
                await fluid.settle(page)
            except PortalChangedError:
                logger.info("UCT: year selector not adjustable — using default")
        if await fluid.button_visible(page, "Start Application"):
            await fluid.click_button(page, "Start Application")
            await fluid.settle(page, 1000)
            await fluid.answer_alert(page, "Yes")
        else:
            # an application already exists for the year — resume it
            for label in ("Continue Application", "Continue", "View Application"):
                if await fluid.button_visible(page, label):
                    await fluid.click_button(page, label)
                    break
            else:
                raise PortalChangedError(
                    "neither Start Application nor a resume button found",
                    selector="Start Application",
                )
        await page.wait_for_load_state("domcontentloaded")
        await fluid.settle(page)
        heading = await fluid.current_step_heading(page)
        logger.info("UCT: entered the application wizard at %r", heading)

    # --- fill_form: steps 2-13 -------------------------------------------------

    async def fill_form(self, page: Page, mapping: FieldMapping) -> None:
        self._require_nbt(mapping)
        # Step 1 (Introduction) is info-only — advance off it if we're there.
        if await fluid.button_visible(page, "Next"):
            await fluid.next_step(page)
        await self._step2_personal(page, mapping)
        await self._step3_contact(page, mapping)
        await self._step4_guardian(page, mapping)
        await self._step5_school(page, mapping)
        await self._step6_tertiary(page, mapping)
        await self._step7_post_school(page)
        await self._step8_choices(page, mapping)
        await self._step9_referees(page)
        await self._step10_nbt(page, mapping)
        await self._step11_funding(page, mapping)
        await self._step12_housing(page, mapping)
        await self._step13_redress(page, mapping)
        logger.info("UCT fill_form: steps 2-13 complete — at Document Uploads")

    def _require_nbt(self, mapping: FieldMapping) -> None:
        """Hard precondition (decided in research): the student must have an NBT
        registration before a UCT run — fail fast with a clear field error
        rather than mid-form. The portal enforces the '931' prefix (msg 2835)."""
        number = str(mapping.get("nbt_registration_number") or "").strip()
        if not number:
            raise ValidationFailedError(
                "UCT requires an NBT registration number before applying — "
                "capture it on the student profile first",
                field="nbt_registration_number",
            )
        if not number.startswith("931"):
            raise ValidationFailedError(
                f"NBT registration number must start with '931' (got {number!r})",
                field="nbt_registration_number",
            )

    async def _step2_personal(self, page: Page, mapping: FieldMapping) -> None:
        """Names/DOB prefill from account creation. Citizenship reveals the SA
        ID field, and its re-render can revert sibling selects — fill one at a
        time and re-assert Race afterwards (both verified live)."""
        if title := mapping.get("title"):
            await self._select_by_label_text(page, "Title", title)
        if sex := mapping.get("sex"):
            await self._select_by_label_text(page, "*Sex", sex)
        if lang := mapping.get("home_language"):
            await self._select_by_label_text(page, "*Home Language", lang)
        citizenship = mapping.get("citizenship_type", "SA Citizen")
        await self._select_by_label_text(
            page, "*Indicate Type of Citizenship or Residency in SA", citizenship
        )
        await fluid.settle(page)  # reveals SA ID (or the passport table) + may revert Race
        if race := mapping.get("race"):
            await self._select_by_label_text(page, "*Race", race)
        if sa_id := mapping.get("sa_id"):
            await self._fill_by_label_text(page, "*SA ID Number", sa_id)
        elif mapping.get("passport_number"):
            # International (Non-SA Citizen): the citizenship select hid the SA-ID
            # block and revealed the Passport Information add-row table instead.
            await self._add_passport_information(page, mapping)
        await fluid.save_step(page, step="2 Personal Information")
        await fluid.next_step(page)

    async def _add_passport_information(
        self, page: Page, mapping: FieldMapping
    ) -> None:
        """International branch: fill the Step-2 Passport Information add-row
        table. 'Add Passport Information' (+) opens a modal (iframe) with
        *Country / *Citizenship Status / *Passport Number (Country first — the
        Citizenship Status list only populates after it). Modelled from
        docs/phase-3/portal-research/uct.md; **[VERIFY]** the modal control ids
        and the Citizenship-Status option set on the first live non-SA run."""
        country = str(mapping.get("passport_country") or "")
        number = str(mapping.get("passport_number") or "")
        status = str(mapping.get("passport_citizenship_status") or "")
        try:
            await fluid.click_button(page, "Add Passport Information")
        except PortalChangedError as exc:
            raise PortalChangedError(
                "UCT 'Add Passport Information' button not found on the "
                "international branch",
                selector="Add Passport Information",
            ) from exc
        frame = await fluid.wait_modal_frame(page)
        await fluid.settle(page, 800)
        frame = await fluid.wait_modal_frame(page)
        if country:
            await self._select_in_frame_by_label(frame, "Country", country)
            await fluid.settle(page, 600)  # populates the Citizenship Status list
        frame = await fluid.wait_modal_frame(page)
        # Modal Citizenship Status options (Citizen / Permanent Resident /
        # Temporary Resident / Unknown) differ from the profile's residency
        # taxonomy — fuzzy-match, defaulting an International applicant to Citizen
        # (a citizen of their passport country).
        await self._select_in_frame_by_label(
            frame, "Citizenship Status", status or "Citizen", fallback="Citizen"
        )
        if number:
            await self._fill_in_frame_by_label(frame, "Passport Number", number)
        await fluid.click_button(frame, "Save")
        await fluid.wait_modal_closed(page)
        await fluid.settle(page, 600)

    async def _step3_contact(self, page: Page, mapping: FieldMapping) -> None:
        """Postal code typed directly populates the Suburb dropdown — no lookup
        modal needed. Phone goes through the '+' add-row iframe modal."""
        postal = str(mapping.get("postal_code") or "")
        if postal:
            await self._fill_by_label_text(page, "*Postal Code", postal)
            await page.keyboard.press("Tab")
            await fluid.settle(page)
        if suburb := mapping.get("suburb"):
            options = await fluid.select_option_texts(
                page, "#UCT_OA_CONTACT_UCT_SA_CITY4"
            )
            chosen = best_option_match(str(suburb), options) or (
                options[0] if options else None
            )
            if not chosen:
                raise ValidationFailedError(
                    f"no UCT suburb option for postal code {postal!r}",
                    field="suburb",
                )
            await fluid.js_select_text(page, "#UCT_OA_CONTACT_UCT_SA_CITY4", chosen)
        if line1 := mapping.get("address_line_1"):
            await fluid.js_fill(page, "#UCT_OA_CONTACT_ADDRESS1", str(line1))
        if phone := mapping.get("phone"):
            await self._add_phone(page, str(phone))
        await fluid.save_step(page, step="3 Contact Details")
        await fluid.next_step(page)

    async def _add_phone(self, page: Page, number: str) -> None:
        try:
            await page.get_by_role("button", name="Add Contact Number").click()
        except Exception as exc:  # noqa: BLE001
            raise PortalChangedError(
                "Add Contact Number button not found", selector="Add Contact Number"
            ) from exc
        frame = await fluid.wait_modal_frame(page)
        await frame.get_by_label("Phone Type").select_option("SA Cellular")
        await fluid.settle(page, 800)  # modal re-renders; country code auto-sets 027
        frame = await fluid.wait_modal_frame(page)
        await frame.get_by_role("textbox", name="Telephone").fill(number)
        await frame.get_by_role("button", name="Save").click()
        await fluid.wait_modal_closed(page)

    async def _step4_guardian(self, page: Page, mapping: FieldMapping) -> None:
        """P/G + fee payer. The P/G SA ID is required once any detail is
        entered (msg 2756); 'guardian is fee payer' hides the payer dropdown."""
        fields = {
            "#UCT_OA_PARENT_UCT_FIRST_NAME_GUA": mapping.get("guardian_first_name"),
            "#UCT_OA_PARENT_UCT_LAST_NAME_GUAR": mapping.get("guardian_last_name"),
            "#UCT_OA_PARENT_UCT_NATIONAL_ID_GU": mapping.get("guardian_id_number"),
            "#UCT_OA_PARENT_EMAIL_ADDR": mapping.get("guardian_email"),
            "#UCT_OA_PARENT_PHONE_DAY": mapping.get("guardian_phone"),
        }
        if title := mapping.get("guardian_title"):
            await fluid.js_select_text(
                page, "#UCT_OA_PARENT_UCT_TITLE_GUARDIAN", str(title)
            )
        for selector, value in fields.items():
            if value:
                await fluid.js_fill(page, selector, str(value))
        if relation := mapping.get("guardian_relationship"):
            options = await fluid.select_option_texts(
                page, "#UCT_OA_PARENT_PEOPLE_RELATION"
            )
            chosen = best_option_match(str(relation), options) or "Guardian"
            await fluid.js_select_text(page, "#UCT_OA_PARENT_PEOPLE_RELATION", chosen)
        if mapping.get("guardian_is_fee_payer", True):
            await fluid.set_switch(page, "#UCT_OA_PARENT_UCT_GUARDIAN_PAYER", True)
            await fluid.settle(page)
        await fluid.save_step(page, step="4 Parent/Guardian and Fee Payer")
        await fluid.next_step(page)

    async def _step5_school(self, page: Page, mapping: FieldMapping) -> None:
        """Year first (the qualification options are year-dependent), school via
        the search modal (which RESETS the qualification — re-assert after),
        then the slot-semantic subject grids for Gr11 + Gr12 April marks."""
        if year := mapping.get("matric_year"):
            await fluid.js_select_text(
                page, "#UCT_OA_SCHOOL_UCT_YEAR_CODE", str(year)
            )
            await fluid.settle(page)
        terms = mapping.get("school_terms", "4 Terms")
        await fluid.js_select_text(page, "#UCT_OA_SCHOOL_TRNSCRPT_STATUS", terms)
        qualification = mapping.get("school_qualification", "NSC(DBE, IEB or SACAI)")
        await fluid.js_select_text(
            page, "#UCT_OA_SCHOOL_UCT_SCHOOL_AUTH", qualification, contains=True
        )
        if school := mapping.get("school"):
            await self._find_school(
                page, str(school), str(mapping.get("school_province") or "")
            )
            await fluid.settle(page)
            # the school-selection re-render clears the qualification select
            await fluid.js_select_text(
                page, "#UCT_OA_SCHOOL_UCT_SCHOOL_AUTH", qualification, contains=True
            )
            await fluid.settle(page)
        subjects = order_subjects_for_slots(list(mapping.get("subjects") or []))
        if subjects:
            await self._fill_grade11(page, subjects)
            await self._fill_grade12_april(page, subjects)
        await fluid.save_step(page, step="5 Secondary School Information")
        await fluid.next_step(page)

    async def _find_school(self, page: Page, school: str, province: str) -> None:
        await fluid.js_click(page, "#PTS_SRCH_BTN")
        frame = await fluid.wait_modal_frame(page)
        if province:
            await frame.get_by_label("Province").select_option(province)
        # >=4 consecutive letters; the distinctive first word works best
        term = next((w for w in school.split() if len(w) >= 4), school[:10])
        await frame.get_by_role("textbox", name="Search Name").fill(term)
        await frame.get_by_role("button", name="Search").click()
        await fluid.settle(page, 1200)
        frame = await fluid.wait_modal_frame(page)
        rows = await frame.evaluate(
            """() => [...document.querySelectorAll('tr')]
              .map(tr => (tr.innerText || '').replace(/\\s+/g, ' ').trim())
              .filter(t => t && !t.startsWith('Description'))"""
        )
        chosen = best_option_match(school, rows or [])
        if not chosen:
            raise ValidationFailedError(
                f"no UCT school result matched {school!r} (province {province!r})",
                field="school",
            )
        clicked = await frame.evaluate(
            """(rowtext) => {
              for (const tr of document.querySelectorAll('tr')) {
                if ((tr.innerText || '').replace(/\\s+/g, ' ').trim() === rowtext) {
                  tr.click();
                  return true;
                }
              }
              return false;
            }""",
            chosen,
        )
        if not clicked:
            raise PortalChangedError(
                f"school row vanished: {chosen!r}", selector="#PTS_SRCH_BTN"
            )
        await fluid.wait_modal_closed(page)

    async def _fill_grade11(self, page: Page, subjects: list[dict]) -> None:
        for index, subject in enumerate(subjects):
            await fluid.js_click(page, _GR11_ROW.format(n=index))
            frame = await fluid.wait_modal_frame(page)
            await fluid.settle(page, 800)
            frame = await fluid.wait_modal_frame(page)
            options = await frame.evaluate(
                """() => {
                  const sel = [...document.querySelectorAll('select')]
                    .find(s => s.labels && s.labels[0]
                          && s.labels[0].textContent.includes('Subject'));
                  return sel ? [...sel.options].map(o => o.text.trim()).filter(Boolean) : [];
                }"""
            )
            name = str(subject.get("name", ""))
            chosen = best_option_match(name, options)
            if not chosen:
                raise ValidationFailedError(
                    f"no UCT subject option matched {name!r} in slot {index} "
                    f"(slot options: {options[:8]})",
                    field="subjects",
                )
            await frame.evaluate(
                """(txt) => {
                  const sel = [...document.querySelectorAll('select')]
                    .find(s => s.labels && s.labels[0]
                          && s.labels[0].textContent.includes('Subject'));
                  const opt = [...sel.options].find(o => o.text.trim() === txt);
                  sel.value = opt.value;
                  sel.dispatchEvent(new Event('change', {bubbles: true}));
                }""",
                chosen,
            )
            await fluid.settle(page, 800)
            frame = await fluid.wait_modal_frame(page)
            await frame.evaluate(
                """(pct) => {
                  const inp = [...document.querySelectorAll('input')]
                    .find(i => i.labels && i.labels[0]
                          && i.labels[0].textContent.includes('%'));
                  inp.value = pct;
                  inp.dispatchEvent(new Event('change', {bubbles: true}));
                }""",
                str(subject.get("percentage", "")),
            )
            await fluid.js_click(frame, _SUBJECT_MODAL_CONFIRM)
            await fluid.wait_modal_closed(page)
            await fluid.settle(page, 600)

    async def _fill_grade12_april(self, page: Page, subjects: list[dict]) -> None:
        """The Grade 12 grid auto-copies the Gr11 subjects; each row's modal
        wants the April % (required) and takes an optional June % — filled
        when a grade_12_june record was captured (mid-year applicants).
        Switch the grade radio first (JS click — radios sit under the
        ps_indicator overlay too)."""
        await fluid.js_click(page, "#UCT_DERIVED_ONL_UCT_SCHOOL_GRADE\\$105\\$")
        await fluid.settle(page)
        for index, subject in enumerate(subjects):
            april = subject.get("april", subject.get("percentage", ""))
            await fluid.js_click(page, _GR12_ROW.format(n=index))
            frame = await fluid.wait_modal_frame(page)
            await fluid.settle(page, 800)
            frame = await fluid.wait_modal_frame(page)
            await fluid.js_fill(frame, _GR12_APRIL, str(april))
            june = subject.get("june")
            if june is not None:
                await self._fill_june_mark(page, str(june), subject)
            await fluid.js_click(frame, _SUBJECT_MODAL_CONFIRM)
            await fluid.wait_modal_closed(page)
            await fluid.settle(page, 600)

    async def _fill_june_mark(self, page: Page, june: str, subject: dict) -> None:
        """The June % input in the Gr12 subject modal, found by its label (the
        id wasn't pinned at the spike — only April's was). Logged and skipped
        when absent, since the portal treats June as optional."""
        frame = await fluid.wait_modal_frame(page)
        filled = await frame.evaluate(
            """(val) => {
              const inp = [...document.querySelectorAll('input')]
                .find(i => !i.disabled && i.labels && i.labels[0]
                      && /june/i.test(i.labels[0].textContent));
              if (!inp) return false;
              inp.value = val;
              inp.dispatchEvent(new Event('change', {bubbles: true}));
              return true;
            }""",
            june,
        )
        if not filled:
            logger.info(
                "UCT June %% input not found for %r — April only",
                subject.get("name"),
            )

    async def _step6_tertiary(self, page: Page, mapping: FieldMapping) -> None:
        applied = str(mapping.get("applied_before", "No")).lower() in ("yes", "true", "1")
        await fluid.set_switch(page, "#UCT_OA_TERTIARY_UCT_TERTIARY_INDIC", applied)
        await fluid.save_step(page, step="6 Tertiary Information")
        await fluid.next_step(page)

    async def _step7_post_school(self, page: Page) -> None:
        await fluid.save_step(page, step="7 Post School Activity")
        await fluid.next_step(page)

    async def _step8_choices(self, page: Page, mapping: FieldMapping) -> None:
        """Cascade: Level → Faculty → Academic Qualification → Specialisation.
        The free-text programme is resolved against the live cascade (scanning
        every faculty when none is mapped); UCT applies no eligibility gate at
        selection. The optional second choice mirrors the cascade on the
        `_INC`-suffixed selects (ids recorded at the live spike) — best-effort,
        a failed second choice never sinks the run."""
        programme = str(mapping.get("programme") or "")
        if not programme:
            raise ValidationFailedError("no programme to apply for", field="programme")
        await self._fill_choice_cascade(
            page, "", mapping.get("choice_level", "Undergraduate"),
            mapping.get("faculty"), programme,
        )
        if second := mapping.get("programme_second"):
            try:
                await self._fill_choice_cascade(
                    page, "_INC", mapping.get("choice_level", "Undergraduate"),
                    None, str(second),
                )
            except (PortalChangedError, ValidationFailedError) as exc:
                logger.warning("UCT second choice skipped: %s", exc)
        await fluid.save_step(page, step="8 Programme Choices")
        await fluid.next_step(page)

    async def _fill_choice_cascade(
        self, page: Page, suffix: str, level: str,
        faculty_hint, programme: str,
    ) -> None:
        """One Level → Faculty → Qualification → Specialisation cascade; the
        second choice uses the same ids with an `_INC` suffix."""
        career = f"#UCT_OA_CHOICE_ACAD_CAREER{suffix}"
        group = f"#UCT_OA_CHOICE_ACAD_GROUP{suffix}"
        prog = f"#UCT_OA_CHOICE_ACAD_PROG{suffix}"
        plan_sel = f"#UCT_OA_CHOICE_ACAD_PLAN{suffix}"
        await fluid.js_select_text(page, career, level)
        await fluid.settle(page)
        faculties = await fluid.select_option_texts(page, group)
        if faculty_hint:
            match = best_option_match(str(faculty_hint), faculties)
            faculties = [match] if match else faculties
        chosen_faculty, chosen_prog = None, None
        for faculty in faculties:
            await fluid.js_select_text(page, group, faculty)
            await fluid.settle(page)
            programmes = await fluid.select_option_texts(page, prog)
            match = best_option_match(programme, programmes)
            if match:
                chosen_faculty, chosen_prog = faculty, match
                break
        if not chosen_prog:
            raise ValidationFailedError(
                f"no UCT qualification matched {programme!r} in any faculty",
                field="programme",
            )
        await fluid.js_select_text(page, prog, chosen_prog)
        await fluid.settle(page)
        plans = await fluid.select_option_texts(page, plan_sel)
        plan = best_option_match(programme, plans) or (plans[0] if plans else None)
        if plan:
            await fluid.js_select_text(page, plan_sel, plan)
        logger.info(
            "UCT choice%s: %s / %s / %s",
            " 2" if suffix else " 1", chosen_faculty, chosen_prog, plan,
        )

    async def _step9_referees(self, page: Page) -> None:
        await fluid.save_step(page, step="9 Referees & Supervisors")
        await fluid.next_step(page)

    async def _step10_nbt(self, page: Page, mapping: FieldMapping) -> None:
        number = str(mapping.get("nbt_registration_number"))
        await fluid.js_fill(page, "#UCT_ONL_APP_NBT_UCT_NBT_REG_NUMBER", number)
        if year := mapping.get("nbt_year"):
            await fluid.js_select_text(
                page, "#UCT_ONL_APP_NBT_UCT_NBT_REG_YEAR", str(year)
            )
            await fluid.settle(page)  # reveals the exam-date dropdown
        date_options = await fluid.select_option_texts(
            page, "#UCT_ONL_APP_NBT_UCT_NBT_DATE"
        )
        wanted = str(mapping.get("nbt_date") or "")
        chosen = wanted if wanted in date_options else None
        if not chosen and date_options:
            chosen = date_options[-1]  # latest listed sitting as the fallback
            logger.info(
                "UCT NBT date %r not in the portal list — using %r", wanted, chosen
            )
        if chosen:
            await fluid.js_select_text(page, "#UCT_ONL_APP_NBT_UCT_NBT_DATE", chosen)
        await fluid.save_step(page, step="10 NBT Information")
        await fluid.next_step(page)

    async def _step11_funding(self, page: Page, mapping: FieldMapping) -> None:
        nsfas = str(mapping.get("nsfas_other_institution", "No")).lower() in (
            "yes", "true", "1",
        )
        needs = str(mapping.get("needs_financial_assistance", "No")).lower() in (
            "yes", "true", "1",
        )
        await fluid.set_switch(page, "#UCT_ONL_APP_FND_UCT_OA_FUND_OTHER", nsfas)
        await fluid.set_switch(page, "#UCT_ONL_APP_FND_UCT_OA_FUND_AID", needs)
        await fluid.save_step(page, step="11 Funding Information")
        await fluid.next_step(page)

    async def _step12_housing(self, page: Page, mapping: FieldMapping) -> None:
        wants = str(mapping.get("wants_housing", "No")).lower() in ("yes", "true", "1")
        await fluid.set_switch(page, "#UCT_ONL_APP_HSE_UCT_SF_HOUSING", wants)
        await fluid.save_step(page, step="12 Housing Information")
        await fluid.next_step(page)

    _REDRESS_SELECTORS = {
        "redress_mother_race": "#UCT_OA_REDRESS_UCT_ETHNIC_MOTHER",
        "redress_father_race": "#UCT_OA_REDRESS_UCT_ETHNIC_FATHER",
        "redress_mother_language": "#UCT_OA_REDRESS_UCT_PRM_GUARD_LANG",
        "redress_mother_education": "#UCT_OA_REDRESS_UCT_MOM_UNIV_DGREE",
        "redress_father_education": "#UCT_OA_REDRESS_UCT_DAD_UNIV_DGREE",
        "redress_grandparent_education": "#UCT_OA_REDRESS_UCT_GRAN_UNIV_DGRE",
        "redress_child_support_grant": "#UCT_OA_REDRESS_UCT_CHILD_SUPPORT",
        "redress_social_pension": "#UCT_OA_REDRESS_UCT_SUPPT_PENSION",
    }

    async def _step13_redress(self, page: Page, mapping: FieldMapping) -> None:
        """All 8 dropdowns are required. Unanswered ones fall back to the
        portal's own 'I choose not to answer' / 'I do not know' options."""
        for field_id, selector in self._REDRESS_SELECTORS.items():
            value = mapping.get(field_id)
            options = await fluid.select_option_texts(page, selector)
            chosen = best_option_match(str(value), options) if value else None
            if not chosen:
                chosen = next(
                    (o for o in options
                     if o in ("I choose not to answer", "I do not know")),
                    None,
                )
            if not chosen:
                raise ValidationFailedError(
                    f"no usable option for {field_id}", field=field_id
                )
            await fluid.js_select_text(page, selector, chosen)
        await fluid.save_step(page, step="13 Redress and Disadvantage Factors")
        await fluid.next_step(page)

    # --- documents / submit / verify ------------------------------------------------

    async def upload_documents(
        self, page: Page, documents: list[DocumentRef]
    ) -> None:
        """Step 14: the SA Identity Document row is required (Choice = All).
        Upload → File Attachment iframe → My Device (native chooser) → Upload →
        'Upload Complete' → Done (verified live)."""
        sa_id = next(
            (d for d in documents if "id" in d.doc_type.lower()), None
        )
        if sa_id is None:
            raise ValidationFailedError(
                "UCT requires the SA Identity Document upload — none provided",
                field="sa_id_document",
            )
        await fluid.js_click(page, _UPLOAD_BUTTON)
        frame = await fluid.wait_modal_frame(page)
        async with page.expect_file_chooser() as chooser_info:
            await frame.get_by_role("button", name="My Device").click()
        chooser = await chooser_info.value
        await chooser.set_files(sa_id.local_path)
        await fluid.settle(page, 1000)
        frame = await fluid.wait_modal_frame(page)
        await frame.get_by_role("button", name="Upload").click()
        try:
            await frame.get_by_text("Upload Complete").wait_for(timeout=30_000)
        except Exception as exc:  # noqa: BLE001
            raise ValidationFailedError(
                f"UCT upload of {sa_id.filename!r} did not complete",
                field="sa_id_document",
            ) from exc
        await frame.get_by_role("button", name="Done").click()
        await fluid.wait_modal_closed(page)
        await fluid.save_step(page, step="14 Document Uploads")
        await fluid.next_step(page)

    async def submit(self, page: Page) -> None:
        """Step 15 (Review): Save → 'reviewed and is correct?' confirm (msg
        3279) → Yes → Next → Step 16: click **Submit** (the student's agreement
        consent is already recorded upstream — the consent gate in background.py
        won't run this step without it)."""
        await fluid.click_button(page, "Save")
        await fluid.settle(page, 1500)
        if not await fluid.answer_alert(page, "Yes"):
            alert = await fluid.read_alert(page)
            raise ValidationFailedError(
                f"UCT review confirmation dialog not shown (alert: {alert})",
                field="review",
            )
        await fluid.settle(page)
        await fluid.next_step(page)
        heading = await fluid.current_step_heading(page)
        if heading and "16" not in heading:
            raise PortalChangedError(
                f"expected Step 16 after review, got {heading!r}",
                selector=_SUBMIT_BUTTON,
            )
        await fluid.js_click(page, _SUBMIT_BUTTON)
        await page.wait_for_load_state("domcontentloaded")
        await fluid.settle(page)

    async def verify_submission(self, page: Page) -> SubmissionConfirmation:
        """**[VERIFY LIVE]** — the post-submit page was deliberately never
        captured (no fake submissions). Best-effort: read an applicant/reference
        number off the page; UCT also emails the applicant number (readable by
        the imap challenge source). Pin the real marker at the supervised first
        live submit."""
        marker = None
        reference = None
        try:
            body = await page.evaluate("() => document.body.innerText.slice(0, 4000)")
            marker = next(
                (line.strip() for line in (body or "").splitlines()
                 if "applicant number" in line.lower() or "submitted" in line.lower()),
                None,
            )
            match = re.search(r"applicant number[:\s]*([A-Z0-9-]{5,})",
                              body or "", re.IGNORECASE)
            reference = match.group(1) if match else None
        except Exception:  # noqa: BLE001
            logger.warning("UCT verify_submission: marker not pinned yet")
        return SubmissionConfirmation(reference=reference, marker=marker)

    # --- small label-based helpers (step 2's controls move between renders) ------

    async def _select_by_label_text(
        self, page: Page, label: str, option_text: str
    ) -> None:
        """Select by the field's accessible label (approach C — works on Fluid),
        re-querying via JS so re-renders don't stale the handle."""
        result = await page.evaluate(
            """([label, txt]) => {
              const sel = [...document.querySelectorAll('select')]
                .find(s => s.offsetParent !== null && s.labels && s.labels[0]
                      && s.labels[0].textContent.trim() === label);
              if (!sel) return {error: 'missing'};
              const opt = [...sel.options].find(o => o.text.trim() === txt)
                || [...sel.options].find(o =>
                     o.text.trim().toLowerCase() === txt.toLowerCase());
              if (!opt) return {error: 'no-option',
                                options: [...sel.options].map(o => o.text.trim())};
              sel.value = opt.value;
              sel.dispatchEvent(new Event('change', {bubbles: true}));
              return {ok: true};
            }""",
            [label, str(option_text)],
        )
        if result.get("error") == "missing":
            raise PortalChangedError(f"select labelled {label!r} not found",
                                     selector=label)
        if result.get("error") == "no-option":
            raise PortalChangedError(
                f"select {label!r} has no option {option_text!r} "
                f"(live: {result.get('options')})",
                selector=label,
            )

    async def _select_in_frame_by_label(
        self, frame, label: str, wanted: str, *, fallback: Optional[str] = None
    ) -> None:
        """Select an option in a modal iframe by a label *substring* (tolerates
        the '*Country' required-marker prefix), fuzzy-matched against the live
        options with an optional fallback when nothing matches."""
        options = await frame.evaluate(
            """(label) => {
              const sel = [...document.querySelectorAll('select')]
                .find(s => s.offsetParent !== null && s.labels && s.labels[0]
                      && s.labels[0].textContent.includes(label));
              return sel
                ? [...sel.options].map(o => o.text.trim()).filter(Boolean)
                : null;
            }""",
            label,
        )
        if options is None:
            raise PortalChangedError(
                f"passport modal select labelled {label!r} not found", selector=label
            )
        chosen = wanted if wanted in options else best_option_match(wanted, options)
        if not chosen and fallback:
            chosen = (
                fallback if fallback in options else best_option_match(fallback, options)
            )
        if not chosen:
            raise ValidationFailedError(
                f"no passport-modal option for {label!r} matched {wanted!r} "
                f"(live: {options[:10]})",
                field=label,
            )
        await frame.evaluate(
            """([label, txt]) => {
              const sel = [...document.querySelectorAll('select')]
                .find(s => s.offsetParent !== null && s.labels && s.labels[0]
                      && s.labels[0].textContent.includes(label));
              const opt = [...sel.options].find(o => o.text.trim() === txt);
              sel.value = opt.value;
              sel.dispatchEvent(new Event('change', {bubbles: true}));
            }""",
            [label, chosen],
        )

    async def _fill_in_frame_by_label(self, frame, label: str, value: str) -> None:
        """Fill a text input in a modal iframe by a label substring."""
        ok = await frame.evaluate(
            """([label, val]) => {
              const inp = [...document.querySelectorAll('input')]
                .find(i => i.offsetParent !== null && i.labels && i.labels[0]
                      && i.labels[0].textContent.includes(label));
              if (!inp) return false;
              inp.value = val;
              inp.dispatchEvent(new Event('change', {bubbles: true}));
              return true;
            }""",
            [label, str(value)],
        )
        if not ok:
            raise PortalChangedError(
                f"passport modal input labelled {label!r} not found", selector=label
            )

    async def _fill_by_label_text(self, page: Page, label: str, value: str) -> None:
        ok = await page.evaluate(
            """([label, val]) => {
              const inp = [...document.querySelectorAll('input')]
                .find(i => i.offsetParent !== null && i.labels && i.labels[0]
                      && i.labels[0].textContent.trim() === label);
              if (!inp) return false;
              inp.value = val;
              inp.dispatchEvent(new Event('change', {bubbles: true}));
              return true;
            }""",
            [label, str(value)],
        )
        if not ok:
            raise PortalChangedError(f"input labelled {label!r} not found",
                                     selector=label)

