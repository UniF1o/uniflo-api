"""Completed-matric / gap-year branch selection and UP / UJ / Wits mapping.

Verifies:
- _applicant_branch returns the correct branch from record type and
  current_activity.
- _guard_applicant_type permits completed-matric for UP, UJ, and Wits; blocks
  at-university / upgrader / postgrad for all portals; and blocks
  completed-matric for portals that haven't built the branch yet (UCT).
- build_field_mapping (UP, UJ, Wits) produces completed-matric field values
  when the branch is completed_matric.
"""

import pytest

from app.automation.mapping import (
    _applicant_branch,
    _guard_applicant_type,
    build_field_mapping,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _Profile:
    is_sa_citizen = True
    title = "mr"
    first_name = "Sipho"
    last_name = "Dlamini"
    id_number = "0412025123086"
    date_of_birth = None
    phone = "0825550199"
    street_address = "8 Maple Road"
    suburb = "Soshanguve East"
    city = "Pretoria"
    province = "Gauteng"
    postal_code = "0152"
    gender = "male"
    home_language = "Zulu"
    ethnicity = "African"
    religion = None
    marital_status = None
    disability = None
    applying_nsfas = None
    wants_residence = None
    applying_institutional_funding = None
    mailing_same_as_residential = None
    mailing_street_address = None
    mailing_suburb = None
    mailing_postal_code = None
    redress_factors = None
    preferred_name = None
    nbt_reference = None
    nbt_year = None
    nbt_date = None
    exam_number = "G28F9001"


class _GapYearProfile(_Profile):
    current_activity = "Gap Year"


class _EmployedProfile(_Profile):
    current_activity = "Working"


class _CurrentGr12Profile(_Profile):
    current_activity = "Currently in Grade 12"


class _AtUniversityProfile(_Profile):
    current_activity = "At university"


class _UpgraderProfile(_Profile):
    current_activity = "Upgrading"


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


_GR11 = _record("grade_11_final", 2024, [
    {"name": "Mathematics", "mark": 72, "nsc_level": 6, "percentage": 72},
    {"name": "Physical Sciences", "mark": 68, "nsc_level": 5, "percentage": 68},
])

_GR12_FINAL = _record("grade_12_final", 2025, [
    {"name": "Mathematics", "mark": 74, "nsc_level": 6, "percentage": 74},
    {"name": "Physical Sciences", "mark": 70, "nsc_level": 6, "percentage": 70},
])


# ---------------------------------------------------------------------------
# _applicant_branch
# ---------------------------------------------------------------------------


def test_branch_grade_12_final_record_returns_completed():
    assert _applicant_branch(_GapYearProfile(), [_GR12_FINAL]) == "completed_matric"


def test_branch_gap_year_activity_no_final_record():
    assert _applicant_branch(_GapYearProfile(), [_GR11]) == "completed_matric"


def test_branch_employed_activity_returns_completed():
    assert _applicant_branch(_EmployedProfile(), [_GR11]) == "completed_matric"


def test_branch_current_gr12_returns_current_learner():
    assert _applicant_branch(_CurrentGr12Profile(), [_GR11]) == "current_learner"


def test_branch_grade_12_final_wins_over_current_gr12_activity():
    """grade_12_final record → completed_matric even when activity says Grade 12."""
    assert _applicant_branch(_CurrentGr12Profile(), [_GR12_FINAL]) == "completed_matric"


def test_branch_no_activity_no_records_returns_current_learner():
    profile = type("P", (), {"current_activity": None})()
    assert _applicant_branch(profile, []) == "current_learner"


# ---------------------------------------------------------------------------
# _guard_applicant_type
# ---------------------------------------------------------------------------


def test_guard_permits_current_gr12_for_up():
    _guard_applicant_type(_CurrentGr12Profile(), "up", [_GR11])


def test_guard_permits_gap_year_for_up():
    _guard_applicant_type(_GapYearProfile(), "up", [_GR12_FINAL])


def test_guard_permits_employed_for_up():
    _guard_applicant_type(_EmployedProfile(), "up", [])


def test_guard_blocks_at_university_for_up():
    with pytest.raises(ValueError, match="at-university"):
        _guard_applicant_type(_AtUniversityProfile(), "up", [])


def test_guard_blocks_upgrader_for_up():
    with pytest.raises(ValueError, match="upgrader"):
        _guard_applicant_type(_UpgraderProfile(), "up", [])


def test_guard_blocks_at_university_for_uj():
    with pytest.raises(ValueError):
        _guard_applicant_type(_AtUniversityProfile(), "uj", [])


def test_guard_permits_gap_year_for_uj():
    # Task 6 — UJ now implements the completed-matric branch.
    _guard_applicant_type(_GapYearProfile(), "uj", [_GR12_FINAL])


def test_guard_permits_employed_for_uj():
    _guard_applicant_type(_EmployedProfile(), "uj", [])


def test_guard_permits_gap_year_for_wits():
    # Task 6 — Wits now implements the completed-matric branch.
    _guard_applicant_type(_GapYearProfile(), "wits", [_GR12_FINAL])


def test_guard_permits_employed_for_wits():
    _guard_applicant_type(_EmployedProfile(), "wits", [])


def test_guard_blocks_completed_matric_for_uct():
    with pytest.raises(ValueError):
        _guard_applicant_type(_GapYearProfile(), "uct", [_GR12_FINAL])


# ---------------------------------------------------------------------------
# UP mapping — completed-matric branch
# ---------------------------------------------------------------------------


def _up_map(profile, records):
    return build_field_mapping(
        "up",
        profile=profile,
        application=_Application(),
        academic_record=records,
        email="sipho.test@gmail.com",
    )


def test_up_completed_matric_highest_grade_is_12():
    m = _up_map(_GapYearProfile(), [_GR12_FINAL])
    assert m.values["highest_grade"] == "Grade 12"


def test_up_completed_matric_exemption_type_contains_admit():
    m = _up_map(_GapYearProfile(), [_GR12_FINAL])
    assert "admit" in m.values["exemption_type"].lower()


def test_up_completed_matric_tell_us_more_unemployed_for_gap_year():
    m = _up_map(_GapYearProfile(), [_GR12_FINAL])
    assert "unemployed" in m.values["tell_us_more"].lower()


def test_up_completed_matric_tell_us_more_employed_for_working():
    m = _up_map(_EmployedProfile(), [_GR12_FINAL])
    assert "working" in m.values["tell_us_more"].lower()


def test_up_completed_matric_subjects_from_gr12_final():
    m = _up_map(_GapYearProfile(), [_GR12_FINAL])
    names = [s["name"].upper() for s in m.values["subjects"]]
    assert "MATHEMATICS" in names
    maths = next(s for s in m.values["subjects"] if s["name"].upper() == "MATHEMATICS")
    assert maths["percentage"] == 74  # GR12_FINAL has 74; GR11 has 72


def test_up_completed_matric_uses_gr12_final_school():
    m = _up_map(_GapYearProfile(), [_GR12_FINAL])
    assert m.values.get("school") == "Soshanguve South Secondary School"


def test_up_current_learner_highest_grade_is_11():
    m = _up_map(_CurrentGr12Profile(), [_GR11])
    assert m.values["highest_grade"] == "Grade 11"


def test_up_current_learner_tell_us_more_still_in_school():
    m = _up_map(_CurrentGr12Profile(), [_GR11])
    assert m.values["tell_us_more"] == "I am currently still in high school"


def test_up_current_learner_subjects_from_gr11():
    m = _up_map(_CurrentGr12Profile(), [_GR11])
    maths = next(s for s in m.values["subjects"] if s["name"].upper() == "MATHEMATICS")
    assert maths["percentage"] == 72  # GR11 data (not GR12_FINAL's 74)


def test_up_completed_matric_matric_year_from_gr12_final():
    """final_school_year is taken from the grade_12_final record's year."""
    m = _up_map(_GapYearProfile(), [_GR12_FINAL])
    assert m.values.get("final_school_year") == "2025"


def test_up_current_learner_blocked_for_at_university():
    with pytest.raises(ValueError):
        _up_map(_AtUniversityProfile(), [])


# ---------------------------------------------------------------------------
# UJ mapping — completed-matric branch (Task 6)
# ---------------------------------------------------------------------------


def _uj_map(profile, records):
    return build_field_mapping(
        "uj",
        profile=profile,
        application=_Application(),
        academic_record=records,
        contacts=[],
        email="sipho.test@gmail.com",
    )


def test_uj_completed_matric_endorsement_is_bachelors():
    m = _uj_map(_GapYearProfile(), [_GR12_FINAL])
    assert m.values["endorsement"] == "BACHELORS DEGREE"


def test_uj_completed_matric_present_activity_not_pupil():
    m = _uj_map(_GapYearProfile(), [_GR12_FINAL])
    assert m.values["present_activity"] == "UNEMPLOYED"


def test_uj_completed_matric_present_activity_employed_for_working():
    m = _uj_map(_EmployedProfile(), [_GR12_FINAL])
    assert m.values["present_activity"] == "EMPLOYED"


def test_uj_completed_matric_subjects_from_gr12_final():
    m = _uj_map(_GapYearProfile(), [_GR12_FINAL])
    maths = next(s for s in m.values["subjects"] if s["name"].upper() == "MATHEMATICS")
    assert maths["percentage"] == 74  # GR12_FINAL (not GR11's 72)


def test_uj_completed_matric_school_from_gr12_final():
    m = _uj_map(_GapYearProfile(), [_GR12_FINAL])
    assert m.values.get("school") == "Soshanguve South Secondary School"


def test_uj_current_learner_endorsement_unchanged():
    m = _uj_map(_CurrentGr12Profile(), [_GR11])
    assert m.values["endorsement"] == "CURRENTLY IN GR.12"


def test_uj_current_learner_subjects_from_gr11():
    m = _uj_map(_CurrentGr12Profile(), [_GR11])
    maths = next(s for s in m.values["subjects"] if s["name"].upper() == "MATHEMATICS")
    assert maths["percentage"] == 72


def test_uj_current_learner_blocked_for_at_university():
    with pytest.raises(ValueError):
        _uj_map(_AtUniversityProfile(), [])


# ---------------------------------------------------------------------------
# Wits mapping — completed-matric branch (Task 6)
# ---------------------------------------------------------------------------


class _Guardian:
    contact_type = "next_of_kin"
    title = "mr"
    first_name = "John"
    last_name = "Dlamini"
    phone = "0825550188"
    email = "john.dlamini.test@gmail.com"
    relationship = "father"
    street_address = None
    suburb = None
    city = None
    province = None
    postal_code = None


def _wits_map(profile, records):
    return build_field_mapping(
        "wits",
        profile=profile,
        application=_Application(),
        academic_record=records,
        contacts=[_Guardian()],
        email="sipho.test@gmail.com",
    )


def test_wits_completed_matric_school_status_key_is_set():
    m = _wits_map(_GapYearProfile(), [_GR12_FINAL])
    assert m.values.get("school_status") == "Completed Grd 12 OR Upgrading"


def test_wits_current_learner_no_school_status_key():
    m = _wits_map(_CurrentGr12Profile(), [_GR11])
    assert "school_status" not in m.values


def test_wits_completed_matric_subjects_from_gr12_final():
    m = _wits_map(_GapYearProfile(), [_GR12_FINAL])
    maths = next(s for s in m.values["subjects"] if s["name"].upper() == "MATHEMATICS")
    assert maths["percentage"] == 74  # GR12_FINAL (not GR11's 72)


def test_wits_completed_matric_school_from_gr12_final():
    m = _wits_map(_GapYearProfile(), [_GR12_FINAL])
    assert m.values.get("school") == "Soshanguve South Secondary School"


def test_wits_completed_matric_activity_is_gap_year():
    m = _wits_map(_GapYearProfile(), [_GR12_FINAL])
    assert m.values["current_activity"] == "Gap Year"


def test_wits_completed_matric_activity_employed_for_working():
    m = _wits_map(_EmployedProfile(), [_GR12_FINAL])
    assert m.values["current_activity"] == "Employment Or Occupation"


def test_wits_current_learner_activity_is_school():
    m = _wits_map(_CurrentGr12Profile(), [_GR11])
    assert m.values["current_activity"] == "School"


def test_wits_current_learner_subjects_from_gr11():
    m = _wits_map(_CurrentGr12Profile(), [_GR11])
    maths = next(s for s in m.values["subjects"] if s["name"].upper() == "MATHEMATICS")
    assert maths["percentage"] == 72  # GR11 data


def test_wits_current_learner_blocked_for_at_university():
    with pytest.raises(ValueError):
        _wits_map(_AtUniversityProfile(), [])
