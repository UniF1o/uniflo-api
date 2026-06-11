"""Unit tests for the Wits adapter's pure/offline logic: field schema sanity,
the VC_*-prefix captcha decode, DOB/mobile helpers, the upload-row map, the
next-of-kin preconditions, the Wits field mapping, and registry resolution."""

from datetime import date

import pytest

from app.automation.adapters import get_adapter, slug_for_website
from app.automation.adapters.up import decode_captcha_sources
from app.automation.adapters.wits import (
    _UPLOAD_ROWS,
    WitsAdapter,
    load_field_schema,
    local_mobile,
    split_dob,
)
from app.automation.base import FieldMapping
from app.automation.exceptions import ValidationFailedError
from app.automation.mapping import build_field_mapping

_ALLOWED_TYPES = {"text", "date", "select", "checkbox", "file", "subject_loop"}


# --- field schema ------------------------------------------------------------------


def test_schema_is_well_formed():
    schema = load_field_schema()
    assert schema["slug"] == "wits"
    ids = [f["field_id"] for f in schema["fields"]]
    assert len(ids) == len(set(ids)), "field_ids must be unique"
    for field in schema["fields"]:
        assert field["type"] in _ALLOWED_TYPES, field["field_id"]
        assert field["label"], field["field_id"]


def test_form_schema_injects_university_id():
    adapter = WitsAdapter()
    schema = adapter.form_schema()
    assert schema["university_id"] == str(adapter.university_id)


# --- captcha decoding (VC_ prefix — live finding 2026-06-11) -------------------------


def test_decode_captcha_wits_prefix():
    sources = [
        "https://self-service.wits.ac.za/cs/csprodonl/cache/VC_L_Y_1.JPG",
        "https://self-service.wits.ac.za/cs/csprodonl/cache/VC_L_D_1.JPG",
        "https://self-service.wits.ac.za/cs/csprodonl/cache/VC_N_7_1.JPG",
        "https://self-service.wits.ac.za/cs/csprodonl/cache/VC_L_M_1.JPG",
        "https://self-service.wits.ac.za/cs/csprodonl/cache/VC_L_R_1.JPG",
        "https://self-service.wits.ac.za/cs/csprodonl/cache/VC_L_U_1.JPG",
    ]
    assert decode_captcha_sources(sources, prefix="VC") == "yd7mru"  # verified live


def test_decode_captcha_wrong_prefix_returns_none():
    assert decode_captcha_sources(["/cache/VC_L_Y_1.JPG"]) is None  # default UP
    assert decode_captcha_sources(["/cache/UP_L_R_1.JPG"], prefix="VC") is None


def test_decode_captcha_up_default_still_works():
    assert decode_captcha_sources(["/cache/UP_L_R_1.JPG"]) == "r"


# --- DOB / mobile helpers -------------------------------------------------------------


def test_split_dob_matches_live_control_formats():
    # Day zero-padded, month as '03 - March' (both verified live)
    assert split_dob("12/03/2008") == ("12", "03 - March", "2008")
    assert split_dob("5/11/2007") == ("05", "11 - November", "2007")


def test_split_dob_rejects_other_formats():
    with pytest.raises(ValueError):
        split_dob("2008-03-12")


def test_local_mobile_strips_prefixes():
    assert local_mobile("0825550142") == "825550142"
    assert local_mobile("+27 82 555 0142") == "825550142"
    assert local_mobile("27825550142") == "825550142"
    assert local_mobile("825550142") == "825550142"


# --- documents upload rows --------------------------------------------------------------


def test_upload_row_indices_match_live_grid():
    # verified live: row 0 = ID copy, row 1 = Final GR11 Results (either
    # results document lands on the same row)
    assert _UPLOAD_ROWS["ID_COPY"] == 0
    assert _UPLOAD_ROWS["GRADE11_RESULTS"] == 1
    assert _UPLOAD_ROWS["MATRIC_RESULTS"] == 1


# --- next-of-kin preconditions (portal-enforced: NOK mobile != applicant's) -------------


def test_require_next_of_kin_passes_with_distinct_mobile():
    WitsAdapter()._require_next_of_kin(FieldMapping(values={
        "nok_surname": "Doe", "nok_phone": "0825550188", "phone": "0825550142",
    }))


def test_require_next_of_kin_rejects_missing_contact():
    with pytest.raises(ValidationFailedError) as exc:
        WitsAdapter()._require_next_of_kin(FieldMapping(values={}))
    assert exc.value.field == "nok_surname"


def test_require_next_of_kin_rejects_same_mobile():
    with pytest.raises(ValidationFailedError) as exc:
        WitsAdapter()._require_next_of_kin(FieldMapping(values={
            "nok_surname": "Doe",
            "nok_phone": "+27825550142",  # same number, different formatting
            "phone": "0825550142",
        }))
    assert exc.value.field == "nok_phone"


# --- registry resolution ----------------------------------------------------------------


def test_get_adapter_by_slug():
    adapter = get_adapter("wits")
    assert isinstance(adapter, WitsAdapter)


def test_slug_for_website_wits_domain():
    assert slug_for_website("https://www.wits.ac.za") == "wits"
    assert slug_for_website("https://self-service.wits.ac.za/psc/csprodonl") == "wits"


# --- field mapping -----------------------------------------------------------------------


class _Profile:
    is_sa_citizen = True
    title = "miss"
    first_name = "Jane"
    last_name = "Doe"
    id_number = "0803124001089"
    date_of_birth = date(2008, 3, 12)
    phone = "0825550142"
    street_address = "24 Acacia Road"
    suburb = "Soshanguve East"
    province = "gauteng"
    postal_code = "0152"
    gender = "female"
    home_language = "ENGLISH"
    ethnicity = "AFRICAN"
    marital_status = None
    disability = None


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


class _Nok:
    contact_type = "next_of_kin"
    title = "mr"
    first_name = "John"
    last_name = "Doe"
    phone = "0825550188"
    email = "john.doe.test26@gmail.com"
    relationship = "father"


def test_wits_mapping_builds_expected_values():
    mapping = build_field_mapping(
        "wits",
        profile=_Profile(),
        application=_Application(),
        academic_record=_Record(),
        contacts=[_Nok()],
        email="jane.doe.test26@gmail.com",
    )
    assert mapping.get("nationality") == "South Africa"
    assert mapping.get("date_of_birth") == "12/03/2008"  # dd/mm/yyyy for split_dob
    assert mapping.get("gender") == "Female"
    assert mapping.get("application_year") == "2027"
    assert mapping.get("current_activity") == "School"
    # plain province name, NOT '<province> DoE' (live-verified Wits list)
    assert mapping.get("examining_authority") == "Gauteng"
    assert mapping.get("examination_year") == "2026"
    assert mapping.get("examination_month") == "November"
    assert mapping.get("subjects")[1]["percentage"] == 72
    assert mapping.get("programme") == "Civil Engineering"
    assert mapping.get("marital_status") == "Single"  # default
    assert mapping.get("population_group") == "Black"  # AFRICAN -> Wits' 'Black'
    assert mapping.get("home_language") == "English"
    assert mapping.get("has_disability") == "No"
    assert mapping.get("nok_title") == "Mr"
    assert mapping.get("nok_initial") == "J"
    assert mapping.get("nok_surname") == "Doe"
    assert mapping.get("nok_phone") == "0825550188"
    assert mapping.get("nok_relationship") == "Father"


def test_wits_mapping_drops_unknowns_and_defaults():
    class _Empty:
        pass

    mapping = build_field_mapping(
        "wits",
        profile=_Empty(),
        application=_Empty(),
        academic_record=None,
        contacts=[],
        email=None,
    )
    assert mapping.get("examining_authority") is None  # no province captured
    assert mapping.get("nok_surname") is None  # adapter precondition raises
    # defaults that always apply
    assert mapping.get("current_activity") == "School"
    assert mapping.get("tertiary_studies") == "No"
    assert mapping.get("examination_month") == "November"
    assert mapping.get("marital_status") == "Single"
