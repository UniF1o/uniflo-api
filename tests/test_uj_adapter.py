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

_ALLOWED_TYPES = {"text", "date", "select", "checkbox", "lov", "file"}


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


class FakeLovPopup:
    def __init__(self, *, fail=None):
        self.calls = []
        self.fail = fail or set()

    async def wait_for_load_state(self, *a, **k):
        pass

    async def fill(self, selector, value):
        self.calls.append(("fill", selector, value))

    def get_by_role(self, role, name=None, exact=False):
        return _Clickable(self, role, name)


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

    async def select_option(self, selector, label=None, value=None):
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
    assert ("check", "#oapAcceptAgreement", None) in page.calls
    assert ("click", "#oapSubmitBtn", None) in page.calls
    assert not any("quit" in str(c).lower() for c in page.calls)


async def test_upload_documents_is_noop():
    a, page = UJAdapter(), FakePage()
    await a.upload_documents(page, [])
    assert page.calls == []


# --- fill_form dispatch --------------------------------------------------------

async def test_fill_form_dispatches_verified_fields():
    a, page = UJAdapter(), FakePage()
    mapping = FieldMapping(
        values={
            "id_number": "0803124001089",  # text -> #oapIDnumber
            "sa_citizen": "Yes",  # select -> #oapCitizenType
            "has_disability": "No",  # checkbox No -> not ticked
        }
    )
    await a.fill_form(page, mapping)
    assert ("fill", "#oapIDnumber", "0803124001089") in page.calls
    assert ("select", "#oapCitizenType", "Yes") in page.calls
    assert not any(c[0] == "check" for c in page.calls)


async def test_fill_form_drives_lov_field():
    popup = FakeLovPopup()
    a, page = UJAdapter(), FakePage(next_popup=popup)
    await a.fill_form(page, FieldMapping(values={"citizenship_code": "South Africa"}))
    assert ("click", "a[href*=oapCitzCode]", None) in page.calls
    assert ("link", "South Africa") in popup.calls


async def test_fill_form_skips_fields_without_selector():
    a, page = UJAdapter(), FakePage()
    await a.fill_form(page, FieldMapping(values={"nok_name": "John Doe"}))
    assert page.calls == []


async def test_fill_form_skips_conditional_field_when_not_actionable():
    a = UJAdapter()
    page = FakePage(fail={"#oapGender"})  # gender is flagged conditional in schema
    await a.fill_form(page, FieldMapping(values={"gender": "F Female", "surname": "Doe"}))
    assert ("fill", "#oapSurname", "Doe") in page.calls
    assert not any(c[1] == "#oapGender" for c in page.calls)
