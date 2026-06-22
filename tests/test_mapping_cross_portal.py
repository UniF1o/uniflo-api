"""Cross-portal mapping behaviours from the 2026-06-12 review: record_type-
aware academic-record selection (Gr11 grids + UCT April/June merge), the
shared contact fallback chains (one captured contact powers every portal),
and the fact-check fixes (Wits religion, UP institutional funding, NSC level
passthrough, Wits postal divergence)."""

from datetime import date

from app.automation.mapping import build_field_mapping


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
    city = "Pretoria"
    province = "gauteng"
    postal_code = "0152"
    gender = "female"
    home_language = "ENGLISH"
    ethnicity = "AFRICAN"
    religion = "christian"
    marital_status = None
    disability = None
    applying_institutional_funding = True
    mailing_same_as_residential = False
    mailing_street_address = "PO Box 99"
    mailing_suburb = "Soshanguve"
    mailing_postal_code = "0164"


class _Application:
    programme = "Civil Engineering"
    application_year = 2027


def _record(record_type, year, subjects):
    return type("R", (), {
        "record_type": record_type, "year": year,
        "institution": "Soshanguve South Secondary School",
        "subjects": subjects,
    })()


_GR11 = _record("grade_11_final", 2025, [
    {"name": "Mathematics", "mark": 72, "nsc_level": 6},
    {"name": "English Home Language", "mark": 75},
])
_GR12_APRIL = _record("grade_12_april", 2026, [
    {"name": "Mathematics", "mark": 68},
])
_GR12_JUNE = _record("grade_12_june", 2026, [
    {"name": "Mathematics", "mark": 74},
    {"name": "English Home Language", "mark": 78},
])


class _Guardian:
    contact_type = "guardian"
    title = "mr"
    first_name = "John"
    last_name = "Doe"
    phone = "0825550188"
    email = "john.doe.test26@gmail.com"
    relationship = "father"
    id_number = "7506155123085"
    street_address = None
    suburb = None
    city = None
    province = None
    postal_code = None


# --- record_type-aware selection -------------------------------------------------


def test_uct_merges_grade12_april_and_june_by_subject():
    mapping = build_field_mapping(
        "uct", profile=_Profile(), application=_Application(),
        academic_record=[_GR12_APRIL, _GR11, _GR12_JUNE], contacts=[],
        email="jane@x.com",
    )
    subjects = {s["name"]: s for s in mapping.get("subjects")}
    maths = subjects["MATHEMATICS"]
    assert maths["percentage"] == 72  # Gr11 final feeds the grid
    assert maths["april"] == 68
    assert maths["june"] == 74
    english = subjects["ENGLISH HOME LANGUAGE"]
    assert "april" not in english  # no April mark captured for it
    assert english["june"] == 78


def test_uct_no_june_keys_without_a_june_record():
    mapping = build_field_mapping(
        "uct", profile=_Profile(), application=_Application(),
        academic_record=[_GR11], contacts=[], email=None,
    )
    assert all("june" not in s and "april" not in s for s in mapping.get("subjects"))


def test_grids_use_gr11_record_not_latest_year():
    # the old "latest by year" pick would have grabbed the 2026 April record
    mapping = build_field_mapping(
        "wits", profile=_Profile(), application=_Application(),
        academic_record=[_GR12_APRIL, _GR11], contacts=[_Guardian()], email=None,
    )
    names = [s["name"] for s in mapping.get("subjects")]
    assert "ENGLISH HOME LANGUAGE" in names  # only on the Gr11 record


def test_matric_year_comes_from_gr12_record_or_intake():
    mapping = build_field_mapping(
        "wits", profile=_Profile(), application=_Application(),
        academic_record=[_GR11], contacts=[_Guardian()], email=None,
    )
    # Gr11 record year is 2025; matric year must be intake-1 = 2026, not 2025
    assert mapping.get("examination_year") == "2026"


def test_nsc_level_rides_along_for_up():
    mapping = build_field_mapping(
        "up", profile=_Profile(), application=_Application(),
        academic_record=[_GR11], contacts=[], email=None,
    )
    maths = next(s for s in mapping.get("subjects") if s["name"] == "MATHEMATICS")
    assert maths["nsc_level"] == 6


# --- one contact powers every portal -----------------------------------------------


def test_single_guardian_covers_uj_nok_and_fee_payer():
    mapping = build_field_mapping(
        "uj", profile=_Profile(), application=_Application(),
        academic_record=[_GR11], contacts=[_Guardian()], email="jane@x.com",
    )
    assert mapping.get("nok_name") == "John Doe"
    assert mapping.get("account_name") == "John Doe"
    assert mapping.get("account_mobile") == "0825550188"
    # the payer has no own address -> the student's stands in (UJ has no
    # "same as student" option)
    assert mapping.get("account_addr_1") == "24 Acacia Road"
    assert mapping.get("account_postal_code") == "0152"


def test_single_guardian_covers_wits_nok():
    mapping = build_field_mapping(
        "wits", profile=_Profile(), application=_Application(),
        academic_record=[_GR11], contacts=[_Guardian()], email="jane@x.com",
    )
    assert mapping.get("nok_surname") == "Doe"
    assert mapping.get("nok_phone") == "0825550188"
    assert mapping.get("nok_relationship") == "Father"


def test_no_payer_address_fallback_without_a_contact():
    mapping = build_field_mapping(
        "uj", profile=_Profile(), application=_Application(),
        academic_record=[_GR11], contacts=[], email=None,
    )
    assert mapping.get("account_name") is None
    assert mapping.get("account_addr_1") is None  # no phantom payer


# --- fact-check fixes ----------------------------------------------------------------


def test_wits_religion_reads_the_profile_column():
    mapping = build_field_mapping(
        "wits", profile=_Profile(), application=_Application(),
        academic_record=[_GR11], contacts=[_Guardian()], email=None,
    )
    assert mapping.get("religious_affiliation") == "Christian"


def test_up_institutional_funding_passes_through():
    mapping = build_field_mapping(
        "up", profile=_Profile(), application=_Application(),
        academic_record=[_GR11], contacts=[], email=None,
    )
    assert mapping.get("up_funding") == "Yes"


def test_wits_postal_divergence_flows_to_step9():
    mapping = build_field_mapping(
        "wits", profile=_Profile(), application=_Application(),
        academic_record=[_GR11], contacts=[_Guardian()], email=None,
    )
    assert mapping.get("postal_same") == "No"
    assert mapping.get("postal_address_line_1") == "PO Box 99"
    assert mapping.get("postal_suburb") == "Soshanguve"
    assert mapping.get("postal_postal_code") == "0164"


def test_wits_postal_defaults_to_same():
    class _SameProfile(_Profile):
        mailing_same_as_residential = None
        mailing_street_address = None
        mailing_suburb = None
        mailing_postal_code = None

    mapping = build_field_mapping(
        "wits", profile=_SameProfile(), application=_Application(),
        academic_record=[_GR11], contacts=[_Guardian()], email=None,
    )
    assert mapping.get("postal_same") == "Yes"


# --- programme choices flow from application_choices ----------------------------------


def test_choices_list_feeds_second_and_third_programmes():
    choices = ["Civil Engineering", "Construction Studies", "Bachelor of Science"]
    wits = build_field_mapping(
        "wits", profile=_Profile(), application=_Application(),
        academic_record=[_GR11], contacts=[_Guardian()], email=None,
        choices=choices,
    )
    assert wits.get("programme") == "Civil Engineering"
    assert wits.get("programme_second") == "Construction Studies"
    assert wits.get("programme_third") == "Bachelor of Science"
    uct = build_field_mapping(
        "uct", profile=_Profile(), application=_Application(),
        academic_record=[_GR11], contacts=[_Guardian()], email=None,
        choices=choices[:2],
    )
    assert uct.get("programme_second") == "Construction Studies"
    up = build_field_mapping(
        "up", profile=_Profile(), application=_Application(),
        academic_record=[_GR11], contacts=[], email=None, choices=choices[:2],
    )
    assert up.get("programme_second") == "Construction Studies"


def test_single_choice_keeps_legacy_programme_column():
    mapping = build_field_mapping(
        "up", profile=_Profile(), application=_Application(),
        academic_record=[_GR11], contacts=[], email=None, choices=[],
    )
    assert mapping.get("programme") == "Civil Engineering"
    assert mapping.get("programme_second") is None


# --- current-Grade-12 integrity guard ---------------------------------------------------


def test_non_school_activity_fails_fast_for_non_up_portals():
    """UJ / UCT / Wits still reject gap-year applicants until Task 6 extends them."""
    import pytest

    class _GapYearProfile(_Profile):
        current_activity = "Gap Year"

    for slug in ("uj", "uct", "wits"):
        with pytest.raises(ValueError, match="Grade 12"):
            build_field_mapping(
                slug, profile=_GapYearProfile(), application=_Application(),
                academic_record=[_GR11], contacts=[_Guardian()], email=None,
            )


def test_gap_year_permitted_for_up():
    """UP now supports gap-year / completed-matric applicants (Task 5)."""

    class _GapYearProfile(_Profile):
        current_activity = "Gap Year"

    m = build_field_mapping(
        "up", profile=_GapYearProfile(), application=_Application(),
        academic_record=[_GR11], email=None,
    )
    assert m.values["highest_grade"] == "Grade 12"


def test_school_activity_passes_the_guard():
    class _SchoolProfile(_Profile):
        current_activity = "GRADE 12 PUPIL"

    mapping = build_field_mapping(
        "uj", profile=_SchoolProfile(), application=_Application(),
        academic_record=[_GR11], contacts=[_Guardian()], email=None,
    )
    assert mapping.get("present_activity") == "GRADE 12 PUPIL"


def test_up_preferred_residence_passes_through():
    class _ResidenceProfile(_Profile):
        wants_residence = True
        preferred_residence = "TuksRes Boekenhout"

    mapping = build_field_mapping(
        "up", profile=_ResidenceProfile(), application=_Application(),
        academic_record=[_GR11], contacts=[], email=None,
    )
    assert mapping.get("wants_residence") == "Yes"
    assert mapping.get("preferred_residence") == "TuksRes Boekenhout"
