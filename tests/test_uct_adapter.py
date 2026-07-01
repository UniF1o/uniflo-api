"""Unit tests for the UCT adapter's pure/offline logic: field schema sanity,
slot-aware subject ordering, free-text option matching, the NBT precondition,
deterministic portal credentials, the UCT field mapping, and registry
resolution by website domain."""

import uuid
from datetime import date

import pytest

from app.api.automation.background import derive_portal_credentials
from app.automation.adapters import get_adapter, slug_for_website
from app.automation.adapters.uct import (
    UCT_SLUG,
    UCTAdapter,
    best_option_match,
    load_field_schema,
    order_subjects_for_slots,
)
from app.automation.base import FieldMapping, PortalCredentials
from app.automation.exceptions import AuthFailedError, ValidationFailedError
from app.automation.mapping import build_field_mapping

_ALLOWED_TYPES = {"text", "date", "select", "checkbox", "lov", "file", "subject_loop"}


# --- field schema ------------------------------------------------------------------


def test_schema_is_well_formed():
    schema = load_field_schema()
    assert schema["slug"] == "uct"
    ids = [f["field_id"] for f in schema["fields"]]
    assert len(ids) == len(set(ids)), "field_ids must be unique"
    for field in schema["fields"]:
        assert field["type"] in _ALLOWED_TYPES, field["field_id"]
        assert field["label"], field["field_id"]


def test_form_schema_injects_university_id():
    adapter = UCTAdapter()
    schema = adapter.form_schema()
    assert schema["university_id"] == str(adapter.university_id)


# --- slot ordering -----------------------------------------------------------------


def test_subjects_ordered_into_uct_slots():
    subjects = [
        {"name": "GEOGRAPHY", "percentage": 74},
        {"name": "MATHEMATICS", "percentage": 72},
        {"name": "AFRIKAANS FIRST ADDITIONAL LANGUAGE", "percentage": 65},
        {"name": "LIFE ORIENTATION", "percentage": 80},
        {"name": "ENGLISH HOME LANGUAGE", "percentage": 75},
        {"name": "PHYSICAL SCIENCES", "percentage": 70},
    ]
    ordered = [s["name"] for s in order_subjects_for_slots(subjects)]
    assert ordered[0] == "ENGLISH HOME LANGUAGE"          # slot 0: HL only
    assert ordered[1] == "AFRIKAANS FIRST ADDITIONAL LANGUAGE"  # slot 1: 2nd lang
    assert ordered[2] == "MATHEMATICS"                    # slot 2: maths
    assert ordered[3] == "LIFE ORIENTATION"               # slot 3: LO only
    assert set(ordered[4:]) == {"GEOGRAPHY", "PHYSICAL SCIENCES"}


# --- option matching (live UCT spellings) ---------------------------------------------


def test_match_abbreviated_subject_names():
    # real slot-2 options harvested live 2026-06-10
    options = [
        "Afrikaans 1st Additional Lang",
        "Afrikaans Home Language",
        "English 1st Additional Lang",
        "English Home Language",
        "IsiZulu 1st Additional Lang",
    ]
    assert best_option_match(
        "AFRIKAANS FIRST ADDITIONAL LANGUAGE", options
    ) == "Afrikaans 1st Additional Lang"
    assert best_option_match("ENGLISH HOME LANGUAGE", options) == "English Home Language"


def test_match_programme_against_qualifications():
    options = [
        "Bachelor of Architectural Studies",
        "Bachelor of Science in Engineering in Chemical Engineering",
        "Bachelor of Science in Engineering in Civil Engineering",
        "Bachelor of Science in Geomatics",
    ]
    assert best_option_match("Civil Engineering", options) == (
        "Bachelor of Science in Engineering in Civil Engineering"
    )


def test_match_school_rows():
    rows = [
        "Hlanganani High School (Soshanguve) SOSHANGUVE - G 971 G BLOCK 0152",
        "Soshanguve South Secondary School SOSHANGUVE 17705 Extension 8 0152",
        "Curro Academy Soshanguve SOSHANGUVE 6283 Palladium Street 0164",
    ]
    chosen = best_option_match("Soshanguve South Secondary School", rows)
    assert chosen is not None and chosen.startswith("Soshanguve South")


def test_match_returns_none_below_confidence():
    assert best_option_match("Astrophysics", ["Accounting", "Geography"]) is None
    assert best_option_match("", ["Accounting"]) is None


# --- NBT precondition ----------------------------------------------------------------


def test_nbt_precondition_missing():
    adapter = UCTAdapter()
    with pytest.raises(ValidationFailedError) as exc:
        adapter._require_nbt(FieldMapping(values={}))
    assert exc.value.field == "nbt_registration_number"


def test_nbt_precondition_wrong_prefix():
    adapter = UCTAdapter()
    with pytest.raises(ValidationFailedError):
        adapter._require_nbt(
            FieldMapping(values={"nbt_registration_number": "12345678901234"})
        )


def test_nbt_precondition_valid():
    adapter = UCTAdapter()
    adapter._require_nbt(
        FieldMapping(values={"nbt_registration_number": "93100012345678"})
    )  # no raise


# --- deterministic credentials ---------------------------------------------------------


def test_derive_portal_credentials_rules_and_determinism():
    student = uuid.uuid4()
    username, password = derive_portal_credentials(student, UCT_SLUG)
    again = derive_portal_credentials(student, UCT_SLUG)
    assert (username, password) == again  # deterministic — retries reuse the account
    # UCT username rules: >=10 chars, [letters digits . - _], not an email
    assert len(username) >= 10 and "@" not in username
    assert all(c.isalnum() or c in ".-_" for c in username)
    # UCT password rules: >=16 with upper, lower, digit, special
    assert len(password) >= 16
    assert any(c.isupper() for c in password)
    assert any(c.islower() for c in password)
    assert any(c.isdigit() for c in password)
    assert any(not c.isalnum() for c in password)


def test_derive_portal_credentials_vary_by_student_and_slug():
    a, b = uuid.uuid4(), uuid.uuid4()
    assert derive_portal_credentials(a, "uct") != derive_portal_credentials(b, "uct")
    assert derive_portal_credentials(a, "uct") != derive_portal_credentials(a, "wits")


# --- registry resolution ----------------------------------------------------------------


def test_slug_for_website_domains():
    assert slug_for_website("https://uct.ac.za") == "uct"
    assert slug_for_website("https://www.uj.ac.za") == "uj"
    assert slug_for_website("https://self-service.wits.ac.za/x") == "wits"
    assert slug_for_website("https://unknown.example.com") is None
    assert slug_for_website(None) is None


def test_get_adapter_by_slug():
    adapter = get_adapter("uct")
    assert isinstance(adapter, UCTAdapter)


# --- field mapping -----------------------------------------------------------------------


class _Profile:
    title = "miss"
    first_name = "Jane"
    middle_names = None
    last_name = "Doe"
    id_number = "0803124001089"
    date_of_birth = date(2008, 3, 12)
    phone = "0825550142"
    street_address = "24 Acacia Road"
    suburb = "Soshanguve"
    city = "Pretoria"
    province = "gauteng"
    postal_code = "0152"
    is_sa_citizen = True
    gender = "female"
    home_language = "ENGLISH"
    ethnicity = "AFRICAN"
    wants_residence = False
    applying_nsfas = True
    nbt_reference = "93100012345678"
    nbt_year = 2026
    nbt_date = date(2026, 7, 25)
    redress_factors = {
        "mother_race": "Black",
        "redress_social_pension": "No",
    }


class _Guardian:
    contact_type = "next_of_kin"  # falls back when no explicit guardian exists
    title = "mr"
    first_name = "John"
    last_name = "Doe"
    relationship = "father"
    id_number = "7506155123085"
    email = "john.doe.test26@gmail.com"
    phone = "0825550188"


class _Record:
    year = 2026
    institution = "Soshanguve South Secondary School"
    subjects = [
        {"name": "English Home Language", "mark": 75},
        {"name": "Mathematics", "mark": 72},
    ]


class _Application:
    programme = "Civil Engineering"
    application_year = 2027


def test_uct_mapping_builds_expected_values():
    mapping = build_field_mapping(
        "uct",
        profile=_Profile(),
        application=_Application(),
        academic_record=_Record(),
        contacts=[_Guardian()],
        email="jane.doe.test26@gmail.com",
    )
    assert mapping.get("date_of_birth") == "12/03/2008"  # dd/mm/yyyy typed format
    assert mapping.get("sex") == "Female"
    assert mapping.get("race") == "African"
    assert mapping.get("home_language") == "English"
    assert mapping.get("citizenship_type") == "SA Citizen"
    assert mapping.get("suburb") == "SOSHANGUVE"  # portal options are UPPERCASE
    assert mapping.get("guardian_first_name") == "John"  # NOK fallback
    assert mapping.get("guardian_relationship") == "Father"
    assert mapping.get("matric_year") == "2026"
    assert mapping.get("school_qualification") == "NSC(DBE, IEB or SACAI)"
    assert mapping.get("subjects")[0]["name"] == "ENGLISH HOME LANGUAGE"
    assert mapping.get("nbt_registration_number") == "93100012345678"
    assert mapping.get("nbt_date") == "25/07/26"  # matches the portal's dd/mm/yy list
    assert mapping.get("needs_financial_assistance") == "Yes"
    assert mapping.get("wants_housing") == "No"
    # redress keys normalised onto the redress_ prefix
    assert mapping.get("redress_mother_race") == "Black"
    assert mapping.get("redress_social_pension") == "No"
    assert mapping.get("programme") == "Civil Engineering"


# --- international branch: passport table + account creation ------------------------


class _FakeModalFrame:
    """Records the label/value writes the passport-modal helpers make; returns
    the canned option list for a Country/Citizenship-Status read (str arg) and
    True for a write ([label, value] arg)."""

    def __init__(self, options_by_label):
        self.options_by_label = options_by_label
        self.writes = []

    async def evaluate(self, js, arg=None):
        if isinstance(arg, str):
            for label, opts in self.options_by_label.items():
                if label in arg or arg in label:
                    return opts
            return None
        self.writes.append(tuple(arg))
        return True


def test_schema_has_passport_fields():
    by_id = {f["field_id"]: f for f in load_field_schema()["fields"]}
    for field_id in (
        "passport_country", "passport_citizenship_status", "passport_number"
    ):
        assert field_id in by_id, field_id
        assert by_id[field_id]["page"] == "2"
        assert by_id[field_id].get("conditional") is True


async def test_select_in_frame_by_label_fuzzy_and_fallback():
    adapter = UCTAdapter()
    frame = _FakeModalFrame({
        "Country": ["Zambia", "Zimbabwe", "South Africa"],
        "Citizenship Status": [
            "Citizen", "Permanent Resident", "Temporary Resident", "Unknown"
        ],
    })
    await adapter._select_in_frame_by_label(frame, "Country", "Zimbabwe")
    assert ("Country", "Zimbabwe") in frame.writes
    # 'International' has no exact modal option → falls back to 'Citizen'.
    await adapter._select_in_frame_by_label(
        frame, "Citizenship Status", "International", fallback="Citizen"
    )
    assert ("Citizenship Status", "Citizen") in frame.writes


async def test_fill_in_frame_by_label_writes_value():
    adapter = UCTAdapter()
    frame = _FakeModalFrame({})
    await adapter._fill_in_frame_by_label(frame, "Passport Number", "ZW1234567")
    assert ("Passport Number", "ZW1234567") in frame.writes


async def test_account_creation_requires_id_or_passport():
    adapter = UCTAdapter()
    creds = PortalCredentials(
        username="u", password="p",
        extra={"first_name": "T", "last_name": "M",
               "date_of_birth": "01/06/2007", "email": "t@x.z"},
    )
    with pytest.raises(AuthFailedError, match="id_number/passport_number"):
        await adapter._create_account(None, creds)


def test_uct_international_mapping_swaps_sa_id_for_passport():
    class _Intl(_Profile):
        is_sa_citizen = False
        citizenship_status = "International"
        nationality = "Zimbabwe"
        passport_number = "ZW1234567"
        id_number = None

    mapping = build_field_mapping(
        "uct", profile=_Intl(), application=_Application(),
        academic_record=_Record(), contacts=[_Guardian()], email=None,
    )
    assert mapping.get("citizenship_type") == "International (Non-SA Citizen)"
    assert mapping.get("passport_country") == "Zimbabwe"
    assert mapping.get("passport_number") == "ZW1234567"
    assert mapping.get("sa_id") is None  # SA-ID field dropped on this branch


def test_uct_mapping_drops_unknowns():
    class _Empty:
        pass

    mapping = build_field_mapping(
        "uct",
        profile=_Empty(),
        application=_Empty(),
        academic_record=None,
        contacts=[],
        email=None,
    )
    assert mapping.get("sa_id") is None
    assert mapping.get("nbt_registration_number") is None
    # defaults that always apply
    assert mapping.get("choice_level") == "Undergraduate"
    assert mapping.get("guardian_is_fee_payer") is True
