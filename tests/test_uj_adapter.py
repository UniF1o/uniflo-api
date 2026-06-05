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

    def __init__(self, *, fail=None):
        self.calls = []
        self.fail = fail or set()
        self.goto_url = None
        self.inner_text_value = "Your student number is 220012345"

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
    assert page_a and all(
        (f["selector"] or "").startswith("#") for f in page_a
    )


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


async def test_fill_form_skips_fields_without_selector():
    a, page = UJAdapter(), FakePage()
    # nok_name is a page-B field with selector null
    await a.fill_form(page, FieldMapping(values={"nok_name": "John Doe"}))
    assert page.calls == []


async def test_fill_form_lov_not_wired_raises():
    a, page = UJAdapter(), FakePage()
    with pytest.raises(PortalChangedError):
        await a.fill_form(page, FieldMapping(values={"citizenship_code": "South Africa"}))


async def test_select_from_lov_not_wired_raises():
    a, page = UJAdapter(), FakePage()
    with pytest.raises(PortalChangedError):
        await a.select_from_lov(page, "#oapCitzCode", "South Africa")


async def test_fill_form_skips_conditional_field_when_not_actionable():
    a = UJAdapter()
    page = FakePage(fail={"#oapGender"})  # gender is flagged conditional in schema
    # gender is not actionable (raises) but conditional -> skipped, run continues
    await a.fill_form(page, FieldMapping(values={"gender": "F Female", "surname": "Doe"}))
    assert ("fill", "#oapSurname", "Doe") in page.calls
    assert not any(c[1] == "#oapGender" for c in page.calls)
