"""International (passport) and upgrading branch mapping.

Verifies:
- _applicant_branch returns "upgrading" for an upgrader.
- _guard_applicant_type permits upgrading everywhere and blocks Grade 8-11.
- build_field_mapping wires the international passport/permit reveal for
  UJ / UCT / Wits, and the upgrading flags for UJ / UP.
- UP rejects international applicants (signup-gated) with a manual-apply error.
"""

import pytest

from app.automation.mapping import (
    _applicant_branch,
    _guard_applicant_type,
    build_field_mapping,
)


class _Profile:
    is_sa_citizen = True
    citizenship_status = None
    passport_number = None
    study_permit_type = None
    nationality = "South Africa"
    title = "mr"
    first_name = "Sipho"
    middle_names = None
    last_name = "Dlamini"
    id_number = "0412025123086"
    date_of_birth = None
    phone = "0825550199"
    street_address = "8 Maple Road"
    suburb = "Soshanguve East"
    city = "Pretoria"
    province = "Gauteng"
    postal_code = "0152"
    gender = "Male"
    home_language = "Zulu"
    ethnicity = "African"
    exam_number = "G28F9001"
    current_activity = None


class _IntlProfile(_Profile):
    is_sa_citizen = False
    citizenship_status = "International"
    nationality = "Zimbabwe"
    passport_number = "ZW1234567"
    study_permit_type = "Study Visa"
    id_number = None
    gender = "Female"


class _UpgraderProfile(_Profile):
    current_activity = "Upgrading matric"


class _Grade9Profile(_Profile):
    current_activity = "In Grade 9"


class _Application:
    programme = "BEng Computer Engineering"
    application_year = 2027


def _record(record_type, year, subjects):
    return type("R", (), {
        "record_type": record_type,
        "year": year,
        "institution": "Soshanguve South Secondary School",
        "subjects": subjects,
    })()


_SUBJECTS = [
    {"name": "Mathematics", "mark": 72, "percentage": 72},
    {"name": "English Home Language", "mark": 70, "percentage": 70},
    {"name": "Physical Sciences", "mark": 65, "percentage": 65},
]
_GR12_FINAL = _record("grade_12_final", 2026, _SUBJECTS)


# --- branch + guard ---------------------------------------------------------------------

def test_branch_upgrading():
    assert _applicant_branch(_UpgraderProfile(), [_GR12_FINAL]) == "upgrading"


def test_guard_permits_upgrading_for_all_portals():
    for slug in ("up", "uj", "wits", "uct"):
        _guard_applicant_type(_UpgraderProfile(), slug, [_GR12_FINAL])


def test_guard_blocks_high_school_for_all_portals():
    for slug in ("up", "uj", "wits", "uct"):
        with pytest.raises(ValueError, match="high school"):
            _guard_applicant_type(_Grade9Profile(), slug, [])


# --- international (passport) mapping ----------------------------------------------------

def test_uj_international_mapping():
    m = build_field_mapping(
        "uj", profile=_IntlProfile(), application=_Application(),
        academic_record=[_GR12_FINAL], email="x@y.z",
    )
    assert m.values["sa_citizen"] == "No"
    assert m.values["citizenship_code"] == "Zimbabwe"
    assert m.values["passport_number"] == "ZW1234567"
    assert m.values["study_permit"] == "Study Visa"
    # UJ's gender <select> labels are 'F Female' / 'M Male' (uj.fields.json).
    assert m.values["gender"] == "F Female"


def test_uct_international_mapping():
    m = build_field_mapping(
        "uct", profile=_IntlProfile(), application=_Application(),
        academic_record=[_GR12_FINAL], email=None,
    )
    assert m.values["citizenship_type"] == "International (Non-SA Citizen)"
    assert m.values["passport_number"] == "ZW1234567"
    assert m.values["passport_country"] == "Zimbabwe"
    # SA-ID field is swapped out on the international branch.
    assert "sa_id" not in m.values


def test_wits_international_mapping():
    m = build_field_mapping(
        "wits", profile=_IntlProfile(), application=_Application(),
        academic_record=[_GR12_FINAL], email=None,
    )
    assert m.values["nationality"] == "Zimbabwe"
    assert m.values["passport_number"] == "ZW1234567"
    assert "id_number" not in m.values


def test_up_international_applies_manually():
    with pytest.raises(ValueError, match="manually"):
        build_field_mapping(
            "up", profile=_IntlProfile(), application=_Application(),
            academic_record=[_GR12_FINAL], email=None,
        )


# --- upgrading mapping ------------------------------------------------------------------

def test_uj_upgrading_sets_flag():
    m = build_field_mapping(
        "uj", profile=_UpgraderProfile(), application=_Application(),
        academic_record=[_GR12_FINAL], email=None,
    )
    assert m.values["upgrading"] == "Yes"


def test_up_upgrading_tell_us_more():
    m = build_field_mapping(
        "up", profile=_UpgraderProfile(), application=_Application(),
        academic_record=[_GR12_FINAL], email=None,
    )
    assert m.values["tell_us_more"] == "I am repeating school /subjects"


def test_wits_upgrading_school_status():
    m = build_field_mapping(
        "wits", profile=_UpgraderProfile(), application=_Application(),
        academic_record=[_GR12_FINAL], email=None,
    )
    assert m.values["current_activity"] == "Currently upgrading matric"
    assert m.values["school_status"] == "Completed Grd 12 OR Upgrading"
