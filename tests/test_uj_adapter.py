import pytest

from app.automation.adapters.uj import (
    ENTRY_URL,
    UJ_SLUG,
    UJ_UNIVERSITY_ID,
    UJAdapter,
    load_field_schema,
)
from app.automation.base import FieldMapping, PortalCredentials
from app.automation.exceptions import AuthFailedError, PortalChangedError

_ALLOWED_TYPES = {"text", "date", "select", "checkbox", "lov", "file", "subject_loop"}


# --- LOV popup fakes -----------------------------------------------------------

class _Clickable:
    def __init__(self, popup, kind, name):
        self.popup, self.kind, self.name = popup, kind, name

    @property
    def first(self):
        return self

    async def click(self):
        if (self.kind, self.name) in self.popup.fail:
            raise RuntimeError(f"not selectable: {self.name}")
        self.popup.calls.append((self.kind, self.name))


# Real harvested UJ subject-LOV rows — the subject reader returns these so the
# resolver (app.automation.subjects) is exercised against true portal spelling.
_UJ_SUBJECT_ROWS = [
    "ENGLISH HOME LANG. (NSC/NCV)",
    "ENGLISH 1ST ADD LANG (NSC/NCV)",
    "AFRIKAANS 1ST AD LAN (NSC/NCV)",
    "AFRIKAANS HOME LANG.(NSC/NCV)",
    "MATHEMATICS (NSC/NCV/ISC)",
    "MATHEMATICAL LIT. (NSC/NCV)",
    "ABITUR MATHEMATICS (NSC)",
    "PHYSICAL SCIENCES(NSC/NCV/ISC)",
    "PHYSICAL EDUCATION (NSC/NCV)",
    "LIFE SCIENCES (NSC)",
    "GEOGRAPHY (NSC/NCV/ ISC)",
    "LIFE ORIENTATION (NSC/NCV/DR)",
]


class FakeLovPopup:
    def __init__(self, *, fail=None, rows=None):
        self.calls = []
        self.fail = fail or set()
        self.rows = rows if rows is not None else list(_UJ_SUBJECT_ROWS)

    async def wait_for_load_state(self, *a, **k):
        pass

    async def fill(self, selector, value):
        self.calls.append(("fill", selector, value))

    def get_by_role(self, role, name=None, exact=False):
        return _Clickable(self, role, name)

    async def evaluate(self, js, arg=None):
        # With an arg → select_from_lov_row's row-picker (clicks; returns bool).
        # Without → the subject reader, returns the candidate row texts.
        if arg is None:
            return list(self.rows)
        self.calls.append(("rowpick", arg))
        return True


class _PopupInfo:
    def __init__(self, popup):
        self._popup = popup

    @property
    def value(self):
        async def _coro():
            return self._popup

        return _coro()


class _PopupCtx:
    def __init__(self, page):
        self.page = page

    async def __aenter__(self):
        return _PopupInfo(self.page.next_popup)

    async def __aexit__(self, *a):
        return False


class FakeLocator:
    def __init__(self, page):
        self.page = page

    @property
    def first(self):
        return self

    async def inner_text(self):
        return self.page.inner_text_value


class FakePage:
    """Records Page-level calls; `fail` = selectors whose action raises."""

    def __init__(self, *, fail=None, next_popup=None):
        self.calls = []
        self.fail = fail or set()
        self.goto_url = None
        self.inner_text_value = "Your student number is 220012345"
        self.next_popup = next_popup

    async def goto(self, url, wait_until=None):
        self.goto_url = url

    def _maybe_fail(self, selector, method):
        if selector in self.fail:
            raise RuntimeError(f"forced fail: {method} {selector}")

    async def fill(self, selector, value):
        self._maybe_fail(selector, "fill")
        self.calls.append(("fill", selector, value))

    async def select_option(self, selector, label=None, value=None, **kwargs):
        self._maybe_fail(selector, "select")
        self.calls.append(
            ("select", selector, label if label is not None else f"val:{value}")
        )

    async def check(self, selector):
        self._maybe_fail(selector, "check")
        self.calls.append(("check", selector, None))

    async def click(self, selector):
        self._maybe_fail(selector, "click")
        self.calls.append(("click", selector, None))

    def get_by_text(self, text, exact=True):
        return FakeLocator(self)

    def expect_popup(self):
        return _PopupCtx(self)

    async def evaluate(self, js, arg=None):
        sel = arg[0] if isinstance(arg, (list, tuple)) and arg else arg
        if sel in self.fail:
            raise RuntimeError("evaluate failed")
        self.calls.append(("evaluate", arg))

    async def eval_on_selector(self, selector, js, arg=None):
        self._maybe_fail(selector, "eval_on_selector")
        self.calls.append(("fire", selector, arg))

    async def wait_for_load_state(self, *a, **k):
        pass

    async def wait_for_timeout(self, *a, **k):
        pass

    def get_by_role(self, role, name=None, exact=False):
        return _PageRoleClick(self, role, name)


class _PageRoleClick:
    def __init__(self, page, role, name):
        self.page, self.role, self.name = page, role, name

    @property
    def first(self):
        return self

    async def click(self, **k):
        self.page.calls.append(("click_role", self.role, self.name))


def _adapter_with_pin(pin="13579"):
    a = UJAdapter()
    a._credentials = PortalCredentials(username="", password="", extra={"pin": pin})
    return a


# --- identity + schema ---------------------------------------------------------

def test_adapter_is_concrete_and_identified():
    a = UJAdapter()
    assert a.slug == UJ_SLUG == "uj"
    assert a.university_id == UJ_UNIVERSITY_ID


def test_field_schema_is_well_formed_and_page_a_has_selectors():
    schema = load_field_schema()
    assert schema["slug"] == "uj"
    assert schema["university_id"] == str(UJ_UNIVERSITY_ID)
    fields = schema["fields"]
    assert len(fields) > 20
    for f in fields:
        assert {"field_id", "label", "type"} <= f.keys()
        assert f["type"] in _ALLOWED_TYPES
    page_a = [f for f in fields if f.get("page") == "A"]
    assert page_a and all((f["selector"] or "").startswith("#") for f in page_a)


# --- id-based helpers ----------------------------------------------------------

async def test_fill_targets_by_id():
    a, page = UJAdapter(), FakePage()
    await a._fill(page, "#oapSurname", "Doe")
    assert ("fill", "#oapSurname", "Doe") in page.calls


async def test_fill_raises_portal_changed_with_selector():
    a = UJAdapter()
    page = FakePage(fail={"#oapSurname"})
    with pytest.raises(PortalChangedError) as exc:
        await a._fill(page, "#oapSurname", "Doe")
    assert exc.value.selector == "#oapSurname"
    assert exc.value.code == "portal_changed"


async def test_select_label_and_value():
    a, page = UJAdapter(), FakePage()
    await a._select_label(page, "#oapTitle", "MR")
    await a._select_value(page, "#oapOldNew", "N")
    assert ("select", "#oapTitle", "MR") in page.calls
    assert ("select", "#oapOldNew", "val:N") in page.calls


async def test_check_and_click():
    a, page = UJAdapter(), FakePage()
    await a._check(page, "#oapApplyDisability")
    await a._click(page, "#oapNextBtn1")
    assert ("check", "#oapApplyDisability", None) in page.calls
    assert ("click", "#oapNextBtn1", None) in page.calls


# --- LOV (popup) ---------------------------------------------------------------

async def test_lov_clicks_row_directly_when_no_search():
    popup = FakeLovPopup()
    a, page = UJAdapter(), FakePage(next_popup=popup)
    await a.select_from_lov(page, "#oapCitzCode", "South Africa")
    # opened the popup via the trigger anchor, then clicked the row
    assert ("click", "a[href*=oapCitzCode]", None) in page.calls
    assert ("link", "South Africa") in popup.calls
    assert not any(c[0] == "fill" for c in popup.calls)  # no search


async def test_lov_searches_then_picks_row():
    popup = FakeLovPopup()
    a, page = UJAdapter(), FakePage(next_popup=popup)
    await a.select_from_lov(page, "#oapStreetAddrPCodeRq", "0152", search_term="0152")
    assert ("fill", "input[name=x_thefilter]", "0152") in popup.calls
    assert ("button", "Search") in popup.calls
    assert ("link", "0152") in popup.calls


async def test_lov_row_missing_raises():
    popup = FakeLovPopup(fail={("link", "South Africa")})
    a, page = UJAdapter(), FakePage(next_popup=popup)
    with pytest.raises(PortalChangedError):
        await a.select_from_lov(page, "#oapCitzCode", "South Africa")


async def test_lov_popup_fails_to_open_raises():
    a = UJAdapter()
    page = FakePage(fail={"a[href*=oapCitzCode]"})  # trigger click fails
    with pytest.raises(PortalChangedError):
        await a.select_from_lov(page, "#oapCitzCode", "South Africa")


# --- login / submit / upload ---------------------------------------------------

async def test_login_passes_gate_with_ids():
    a, page = UJAdapter(), FakePage()
    await a.login(page, PortalCredentials(username="", password=""))
    assert page.goto_url == ENTRY_URL
    assert ("select", "#oapOldNew", "val:N") in page.calls
    assert ("select", "#oapReturnYesNo", "val:N") in page.calls
    assert ("select", "#oapTokenYesNo", "val:N") in page.calls
    assert ("check", "#oapAcceptPopi", None) in page.calls
    assert ("click", "#oapNextBtn1", None) in page.calls


async def test_submit_requires_pin():
    a, page = UJAdapter(), FakePage()
    with pytest.raises(AuthFailedError):
        await a.submit(page)


async def test_submit_enters_pin_and_never_quits():
    a, page = _adapter_with_pin("13579"), FakePage()
    await a.submit(page)
    assert ("fill", "#oapLoginPin", "13579") in page.calls
    assert ("check", "#oapAcceptApplRAR", None) in page.calls  # "I Accept"
    assert ("click", "#oapNextBtn8", None) in page.calls  # "Submit Application"
    # never touch Quit Application (#oapExitBtn8 deletes all data)
    assert not any("oapExitBtn8" in str(c) for c in page.calls)
    assert not any("quit" in str(c).lower() for c in page.calls)


async def test_upload_documents_is_noop():
    a, page = UJAdapter(), FakePage()
    await a.upload_documents(page, [])
    assert page.calls == []


# --- field dispatch via _fill_simple (fill_form now drives the full A→G walk) ---

async def test_fill_simple_dispatches_verified_fields():
    a, page = UJAdapter(), FakePage()
    mapping = FieldMapping(
        values={
            "id_number": "0803124001089",  # text -> #oapIDnumber
            "sa_citizen": "Yes",  # select -> #oapCitizenType
            "has_disability": "No",  # checkbox No -> not ticked
        }
    )
    await a._fill_simple(page, mapping)
    assert ("fill", "#oapIDnumber", "0803124001089") in page.calls
    assert ("select", "#oapCitizenType", "Yes") in page.calls
    assert not any(c[0] == "check" for c in page.calls)


async def test_set_date_uses_evaluate():
    a, page = UJAdapter(), FakePage()
    await a._set_date(page, "#oapBirthdate", "12-MAR-2008")
    assert ("evaluate", ["#oapBirthdate", "12-MAR-2008"]) in page.calls


async def test_set_date_failure_raises_portal_changed():
    a = UJAdapter()
    page = FakePage(fail={"#oapBirthdate"})
    with pytest.raises(PortalChangedError):
        await a._set_date(page, "#oapBirthdate", "12-MAR-2008")


async def test_fill_simple_dispatches_date_via_set_date():
    a, page = UJAdapter(), FakePage()
    await a._fill_simple(page, FieldMapping(values={"date_of_birth": "12-MAR-2008"}))
    assert ("evaluate", ["#oapBirthdate", "12-MAR-2008"]) in page.calls


async def test_fill_simple_drives_lov_field():
    popup = FakeLovPopup()
    a, page = UJAdapter(), FakePage(next_popup=popup)
    await a._fill_simple(page, FieldMapping(values={"citizenship_code": "South Africa"}))
    assert ("click", "a[href*=oapCitzCode]", None) in page.calls
    assert ("link", "South Africa") in popup.calls


async def test_fill_simple_skips_page_e_manual_field():
    a, page = UJAdapter(), FakePage()
    # academic_year (page E) has a selector but is flagged manual -> not filled here
    await a._fill_simple(page, FieldMapping(values={"academic_year": "2027"}))
    assert page.calls == []


async def test_fill_simple_skips_manual_fields():
    a, page = UJAdapter(), FakePage()
    # matric_year (page C) has a selector but is flagged manual — driven by
    # fill_matric_page, not the generic _fill_simple loop.
    await a._fill_simple(page, FieldMapping(values={"matric_year": "2026"}))
    assert page.calls == []


# --- Page C / D dedicated flows ------------------------------------------------

async def test_fill_matric_page_reveals_and_loops_subjects():
    popup = FakeLovPopup()
    a, page = UJAdapter(), FakePage(next_popup=popup)
    mapping = FieldMapping(
        values={
            "matric_year": "2026",
            "ug_or_pg": "Undergraduate",
            "upgrading": "No",
            "matric_type": "SA Matric",
            "endorsement": "CURRENTLY IN GR.12",
            "subjects": [
                {"name": "MATHEMATICS (NSC/NCV/ISC)", "percentage": 72},
                {"name": "ENGLISH HOME LANG. (NSC/NCV)", "percentage": 75},
            ],
        }
    )
    await a.fill_matric_page(page, mapping)
    # matric year first, then fire its onchange to reveal the UG block
    assert ("fill", "#oapMatYear", "2026") in page.calls
    assert ("fire", "#oapMatYear", ["change", "blur"]) in page.calls
    assert ("select", "#oapUGPGUGOnly", "Undergraduate") in page.calls
    assert ("select", "#oapStudUpgrade", "No") in page.calls
    # matric-type re-asserted at least twice (once after endorsement, once/subject)
    assert sum(c == ("select", "#oapTypeMatric", "SA Matric") for c in page.calls) >= 2
    # endorsement + both subjects driven through the LOV
    assert ("link", "CURRENTLY IN GR.12") in popup.calls
    assert ("link", "MATHEMATICS (NSC/NCV/ISC)") in popup.calls
    assert ("link", "ENGLISH HOME LANG. (NSC/NCV)") in popup.calls
    assert ("link", "NSC") in popup.calls
    assert ("link", "72") in popup.calls and ("link", "75") in popup.calls
    # one Add Subject click per subject
    assert sum(c == ("click", "#oapAddMatric", None) for c in page.calls) == 2


async def test_select_subject_resolves_freeform_name():
    # free-form "Mathematics" must resolve to the NSC row, not ABITUR/3rd-paper
    popup = FakeLovPopup()
    a, page = UJAdapter(), FakePage(next_popup=popup)
    await a.select_subject_from_lov(page, "Mathematics")
    assert ("click", "a[href*=oapMSubj]", None) in page.calls
    assert ("fill", "input[name=x_thefilter]", "MATHEMATICS") in popup.calls
    assert ("link", "MATHEMATICS (NSC/NCV/ISC)") in popup.calls


async def test_select_subject_no_match_raises():
    popup = FakeLovPopup(rows=["ACCOUNTING (NSC/NCV)", "BIOLOGY (NSC)"])
    a, page = UJAdapter(), FakePage(next_popup=popup)
    with pytest.raises(PortalChangedError):
        await a.select_subject_from_lov(page, "Mathematics")


async def test_add_subject_drives_lovs_and_clicks_add():
    popup = FakeLovPopup()
    a, page = UJAdapter(), FakePage(next_popup=popup)
    await a.add_subject(page, "LIFE ORIENTATION (NSC/NCV/DR)", 80)
    assert ("click", "a[href*=oapMSubj]", None) in page.calls
    assert ("link", "LIFE ORIENTATION (NSC/NCV/DR)") in popup.calls
    assert ("link", "NSC") in popup.calls
    assert ("link", "80") in popup.calls
    assert ("select", "#oapTypeMatric", "SA Matric") in page.calls  # reset guard
    assert ("click", "#oapAddMatric", None) in page.calls


async def test_fill_previous_studies_page():
    popup = FakeLovPopup()
    a, page = UJAdapter(), FakePage(next_popup=popup)
    mapping = FieldMapping(
        values={
            "school": "SOSHANGUVE SECONDARY SCHOOL",
            "present_activity": "GRADE 12 PUPIL",
            "studied_before": "No",
        }
    )
    await a.fill_previous_studies_page(page, mapping)
    assert ("click", "a[href*=oapSchool]", None) in page.calls
    assert ("link", "SOSHANGUVE SECONDARY SCHOOL") in popup.calls
    assert ("click", "a[href*=oapPact]", None) in page.calls
    assert ("link", "GRADE 12 PUPIL") in popup.calls
    assert ("select", "#oapPrevQualInd", "No") in page.calls


async def test_select_from_lov_row_picks_by_row_text():
    popup = FakeLovPopup()
    a, page = UJAdapter(), FakePage(next_popup=popup)
    await a.select_from_lov_row(
        page, "#oapQualification", "B ENG IN CIVIL ENGINEERING", search_term="%"
    )
    assert ("click", "a[href*=oapQualification]", None) in page.calls
    assert ("fill", "input[name=x_thefilter]", "%") in popup.calls
    assert ("button", "Search") in popup.calls
    # the row substring is handed to the popup's evaluate (clicks the row's <a>)
    assert ("rowpick", "B ENG IN CIVIL ENGINEERING") in popup.calls


async def test_run_application_walks_to_page_g_without_submitting():
    popup = FakeLovPopup()
    a, page = _adapter_with_pin(), FakePage(next_popup=popup)
    mapping = FieldMapping(
        values={
            "id_number": "0803124001089",
            "sa_citizen": "Yes",
            "nok_name": "John Doe",
            "matric_year": "2026",
            "subjects": [{"name": "MATHEMATICS (NSC/NCV/ISC)", "percentage": 72}],
            "school": "SOSHANGUVE SECONDARY SCHOOL",
            "faculty": "ENGINEERING&BUILT ENVIRONMENT",
            "programme": "B ENG IN CIVIL ENGINEERING",
        }
    )
    await a.run_application(page, mapping, do_submit=False)
    # Saved through every page A→E
    for sel in ["#oapNextBtn2", "#oapNextBtn2_1", "#oapNextBtn3",
                "#oapNextBtn4", "#oapNextBtn6"]:
        assert ("click", sel, None) in page.calls
    # Page F summary advanced via the id-less Continue
    assert ("click_role", "button", "Continue") in page.calls
    # NEVER submitted: no PIN entry, no Submit/Quit click
    assert not any(c[:2] == ("fill", "#oapLoginPin") for c in page.calls)
    assert ("click", "#oapNextBtn8", None) not in page.calls
    assert not any("oapExitBtn8" in str(c) for c in page.calls)


async def test_run_application_submits_when_requested():
    popup = FakeLovPopup()
    a, page = _adapter_with_pin("13579"), FakePage(next_popup=popup)
    await a.run_application(page, FieldMapping(values={"subjects": []}), do_submit=True)
    # do_submit=True runs the Page-G submit with the real ids
    assert ("fill", "#oapLoginPin", "13579") in page.calls
    assert ("check", "#oapAcceptApplRAR", None) in page.calls
    assert ("click", "#oapNextBtn8", None) in page.calls


async def test_fill_qualifications_page():
    popup = FakeLovPopup()
    a, page = UJAdapter(), FakePage(next_popup=popup)
    mapping = FieldMapping(
        values={
            "academic_year": "2027",
            "applying_for": "Curricular Courses",
            "faculty": "ENGINEERING&BUILT ENVIRONMENT",
            "programme": "B ENG IN CIVIL ENGINEERING",
            "year_of_study": "FIRST YEAR",
        }
    )
    await a.fill_qualifications_page(page, mapping)
    assert ("select", "#oapAcademicYear", "2027") in page.calls
    # the gate that populates the faculty LOV
    assert ("select", "#oapECSLP", "Curricular Courses") in page.calls
    assert ("click", "a[href*=oapFaculty]", None) in page.calls
    assert ("link", "ENGINEERING&BUILT ENVIRONMENT") in popup.calls
    # programme is code-keyed -> picked by row text
    assert ("click", "a[href*=oapQualification]", None) in page.calls
    assert ("rowpick", "B ENG IN CIVIL ENGINEERING") in popup.calls
    assert ("click", "a[href*=oapStudyPeriod]", None) in page.calls
    assert ("link", "FIRST YEAR") in popup.calls


async def test_fill_simple_skips_conditional_field_when_not_actionable():
    a = UJAdapter()
    page = FakePage(fail={"#oapGender"})  # gender is flagged conditional in schema
    await a._fill_simple(page, FieldMapping(values={"gender": "F Female", "surname": "Doe"}))
    assert ("fill", "#oapSurname", "Doe") in page.calls
    assert not any(c[1] == "#oapGender" for c in page.calls)
