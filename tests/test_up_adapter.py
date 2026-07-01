"""Unit tests for the UP adapter's pure/offline logic: field schema sanity,
captcha filename decoding, NSC level derivation, study-choice row ranking
(eligibility-gate fallback order), the upload-row map, the UP field mapping,
and registry resolution."""

from datetime import date

import pytest

from app.automation.adapters import get_adapter, slug_for_website
from app.automation.adapters.up import (
    _UPLOAD_ROWS,
    UPAdapter,
    _iso_date,
    decode_captcha_sources,
    load_field_schema,
    nsc_level,
    rank_choice_rows,
)
from app.automation.mapping import build_field_mapping

_ALLOWED_TYPES = {"text", "date", "select", "checkbox", "file", "subject_loop"}


# --- field schema ------------------------------------------------------------------


def test_schema_is_well_formed():
    schema = load_field_schema()
    assert schema["slug"] == "up"
    ids = [f["field_id"] for f in schema["fields"]]
    assert len(ids) == len(set(ids)), "field_ids must be unique"
    for field in schema["fields"]:
        assert field["type"] in _ALLOWED_TYPES, field["field_id"]
        assert field["label"], field["field_id"]


def test_form_schema_injects_university_id():
    adapter = UPAdapter()
    schema = adapter.form_schema()
    assert schema["university_id"] == str(adapter.university_id)


# --- captcha decoding (filenames spell the answer — live finding 2026-06-11) --------


def test_decode_captcha_lowercase_sequence():
    sources = [
        "https://upnet.up.ac.za/cs/upapply/cache/UP_L_R_1.JPG",
        "https://upnet.up.ac.za/cs/upapply/cache/UP_L_M_1.JPG",
        "https://upnet.up.ac.za/cs/upapply/cache/UP_L_E_1.JPG",
        "https://upnet.up.ac.za/cs/upapply/cache/UP_L_E_1.JPG",
        "https://upnet.up.ac.za/cs/upapply/cache/UP_L_E_1.JPG",
        "https://upnet.up.ac.za/cs/upapply/cache/UP_L_C_1.JPG",
    ]
    assert decode_captcha_sources(sources) == "rmeeec"  # verified live


def test_decode_captcha_case_and_digit_markers():
    assert decode_captcha_sources(["/cache/UP_U_A_2.JPG"]) == "A"
    assert decode_captcha_sources(["/cache/UP_L_A_2.JPG"]) == "a"
    assert decode_captcha_sources(["/cache/UP_N_6_3.JPG"]) == "6"


def test_decode_captcha_unknown_scheme_returns_none():
    assert decode_captcha_sources(["/cache/CAPTCHA_42.PNG"]) is None
    assert decode_captcha_sources(["/cache/UP_L_R_1.JPG", "nope.gif"]) is None
    assert decode_captcha_sources([]) is None


# --- NSC level bands ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("percent", "level"),
    [(100, 7), (80, 7), (79, 6), (75, 6), (70, 6), (69, 5), (60, 5),
     (59, 4), (50, 4), (49, 3), (40, 3), (39, 2), (30, 2), (29, 1), (0, 1)],
)
def test_nsc_level_bands(percent, level):
    assert nsc_level(percent) == level


# --- study-choice ranking (live rows from the 2026-06-11 spike) ----------------------

_LIVE_ROWS = [
    "12136017 Undergraduate BEng in Civil Engineering Open 5-year programme: "
    "design, build and maintain",
    "12130017 Undergraduate BEng in Civil Engineering Open 4-year programme, "
    "Design, build and maintain",
    "02133364 Undergraduate BSc in Geography Geography and Environmental "
    "Science Open Transport and civil",
]


def test_rank_choice_rows_orders_by_match():
    ranked = rank_choice_rows("Civil Engineering", _LIVE_ROWS)
    assert len(ranked) >= 2
    assert all("BEng in Civil Engineering" in row for row in ranked[:2])
    # the eligibility-gate fallback walks this order: 4yr/5yr BEng before BSc Geo


def test_rank_choice_rows_excludes_closed_programmes():
    rows = ["12130017 Undergraduate BEng in Civil Engineering Closed 4-year"]
    assert rank_choice_rows("Civil Engineering", rows) == []


def test_rank_choice_rows_empty_inputs():
    assert rank_choice_rows("", _LIVE_ROWS) == []
    assert rank_choice_rows("Civil Engineering", []) == []
    assert rank_choice_rows("Astrophysics", _LIVE_ROWS) == []


# --- documentation upload rows --------------------------------------------------------


def test_upload_row_indices_match_live_grid():
    # fixed indices verified live: 0 SA ID, 2 Gr11 results, 3 Gr12 results
    assert _UPLOAD_ROWS["ID_COPY"] == 0
    assert _UPLOAD_ROWS["GRADE11_RESULTS"] == 2
    assert _UPLOAD_ROWS["MATRIC_RESULTS"] == 3


# --- date conversion -------------------------------------------------------------------


def test_iso_date_accepts_both_extra_formats():
    assert _iso_date("12/03/2008") == "2008-03-12"  # credentials.extra dd/mm/yyyy
    assert _iso_date("2008-03-12") == "2008-03-12"  # already ISO


# --- registry resolution ----------------------------------------------------------------


def test_get_adapter_by_slug():
    adapter = get_adapter("up")
    assert isinstance(adapter, UPAdapter)


def test_slug_for_website_up_domain():
    assert slug_for_website("https://www.up.ac.za") == "up"
    assert slug_for_website("https://upnet.up.ac.za/psc/upapply") == "up"


# --- field mapping -----------------------------------------------------------------------


class _Profile:
    title = "miss"
    first_name = "Jane"
    last_name = "Doe"
    id_number = "0803124001089"
    date_of_birth = date(2008, 3, 12)
    phone = "0825550142"
    street_address = "24 Acacia Road"
    suburb = "Soshanguve"
    city = "Pretoria"
    province = "gauteng"
    postal_code = "0152"
    gender = "female"
    home_language = "ENGLISH"
    ethnicity = "AFRICAN"
    wants_residence = False
    applying_nsfas = True


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


def test_up_mapping_builds_expected_values():
    mapping = build_field_mapping(
        "up",
        profile=_Profile(),
        application=_Application(),
        academic_record=_Record(),
        contacts=[],
        email="jane.doe.test26@gmail.com",
    )
    assert mapping.get("date_of_birth") == "2008-03-12"  # ISO for the native input
    assert mapping.get("application_year") == "2027"
    assert mapping.get("title") == "Miss"
    assert mapping.get("preferred_name") == "Jane"  # defaults to the first name
    assert mapping.get("gender") == "Female"
    assert mapping.get("home_language") == "English"
    assert mapping.get("population_group") == "African"
    assert mapping.get("tell_us_more") == "I am currently still in high school"
    assert mapping.get("prev_enrolled") == "No"
    assert mapping.get("final_school_year") == "2026"
    assert mapping.get("examining_authority") == "Gauteng DoE"
    assert mapping.get("school_grades_type") == "Nat Senior Cert or IEB"
    assert mapping.get("highest_grade") == "Grade 11"
    assert mapping.get("exemption_type") == "Currently busy with schooling"
    assert mapping.get("subjects")[0]["percentage"] == 75
    assert mapping.get("programme") == "Civil Engineering"
    assert mapping.get("wants_residence") == "No"
    assert mapping.get("applying_nsfas") == "Yes"
    assert mapping.get("up_funding") == "No"


def test_up_upgrading_mapping_sets_completed_matric_fields():
    """UP gains the upgrading branch with no adapter code change — the existing
    data-driven Secondary/Demographic sections select whatever the mapping puts
    in tell_us_more / highest_grade / exemption_type. A grade_12_final record
    plus an 'Upgrading' activity must drive the completed-matric values."""
    class _Upgrader(_Profile):
        current_activity = "Upgrading matric"

    gr12 = type("R", (), {
        "record_type": "grade_12_final", "year": 2026,
        "institution": "Soshanguve South Secondary School",
        "subjects": [{"name": "Mathematics", "mark": 72}],
    })()
    mapping = build_field_mapping(
        "up", profile=_Upgrader(), application=_Application(),
        academic_record=[gr12], email=None,
    )
    assert mapping.get("tell_us_more") == "I am repeating school /subjects"
    assert mapping.get("highest_grade") == "Grade 12"
    assert mapping.get("exemption_type") == "Admit to Bachelor Studies"
    assert mapping.get("final_school_year") == "2026"


def test_up_mapping_drops_unknowns_and_defaults():
    class _Empty:
        pass

    mapping = build_field_mapping(
        "up",
        profile=_Empty(),
        application=_Empty(),
        academic_record=None,
        contacts=[],
        email=None,
    )
    assert mapping.get("examining_authority") is None  # no province → adapter asks
    assert mapping.get("final_school_year") is None
    # defaults that always apply
    assert mapping.get("tell_us_more") == "I am currently still in high school"
    assert mapping.get("prev_enrolled") == "No"
    assert mapping.get("wants_residence") == "No"
    assert mapping.get("highest_grade") == "Grade 11"
