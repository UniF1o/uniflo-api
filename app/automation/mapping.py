"""Build a portal `FieldMapping` from the Uniflo data model.

This is the deterministic bridge between our DB (StudentProfile, Contact,
AcademicRecord, Application) and an adapter's `field_id`s. It maps the
straightforward fields directly. Two free-text fields are passed through as-is
and resolved by the adapter against the live LOV at fill time:

  * **subject names** — `academic_records.subjects` stores plain NSC names
    ("Mathematics") → resolved to UJ's qualifier-tagged LOV entries by
    `app.automation.subjects`.
  * **faculty / programme** — `application.programme` is free text →
    `app.automation.adapters.uj_programmes` resolves the faculty + an
    `(ELIGIBLE TO APPLY-Y)` programme from the live LOV (never an ineligible one).

Pure + side-effect free so it unit-tests without a DB.
"""

from datetime import date
from typing import Any, Optional

from app.automation.base import FieldMapping


def _g(obj: Any, attr: str, default: Any = None) -> Any:
    """Attribute (model) or key (dict) access — whichever `obj` supports."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _yn(value: Optional[bool]) -> Optional[str]:
    if value is None:
        return None
    return "Yes" if value else "No"


def _format_dob(value: Any) -> Optional[str]:
    """UJ wants DD-MON-YYYY (e.g. 12-MAR-2008)."""
    if isinstance(value, date):
        return value.strftime("%d-%b-%Y").upper()
    return None


def _initials(first: Optional[str], middles: Optional[str]) -> Optional[str]:
    parts = [p for p in [first, middles] if p]
    letters = "".join(w[0] for chunk in parts for w in chunk.split())
    return letters.upper() or None


def _full_first_names(first: Optional[str], middles: Optional[str]) -> Optional[str]:
    names = " ".join(p for p in [first, middles] if p).strip()
    return names or None


def _coerce_subjects(raw: Any) -> list[dict]:
    """Normalise `academic_records.subjects` JSON into [{name, percentage}].
    Accepts a list of dicts (various key names) or a {name: mark} dict."""
    out: list[dict] = []
    if isinstance(raw, dict):
        items = raw.items()
        for name, mark in items:
            out.append({"name": str(name).upper(), "percentage": mark})
        return out
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = (
                item.get("name")
                or item.get("subject")
                or item.get("subject_name")
            )
            mark = (
                item.get("percentage")
                if item.get("percentage") is not None
                else item.get("mark")
                if item.get("mark") is not None
                else item.get("final")
                if item.get("final") is not None
                else item.get("result")
            )
            if name is not None:
                out.append({"name": str(name).upper(), "percentage": mark})
    return out


def _contact_by_type(contacts: Any, contact_type: str) -> Optional[Any]:
    for c in contacts or []:
        if _g(c, "contact_type") == contact_type:
            return c
    return None


def _contact_name(contact: Any) -> Optional[str]:
    parts = [_g(contact, "first_name"), _g(contact, "last_name")]
    name = " ".join(p for p in parts if p).strip()
    return name or None


def build_field_mapping(
    slug: str,
    *,
    profile: Any,
    application: Any,
    academic_record: Any = None,
    contacts: Any = None,
    email: Optional[str] = None,
) -> FieldMapping:
    """Build a `FieldMapping` for the given portal `slug`. Raises ValueError for
    a portal with no mapping yet."""
    if slug == "uj":
        return _uj_mapping(
            profile=profile,
            application=application,
            academic_record=academic_record,
            contacts=contacts,
            email=email,
        )
    if slug == "uct":
        return _uct_mapping(
            profile=profile,
            application=application,
            academic_record=academic_record,
            contacts=contacts,
            email=email,
        )
    if slug == "up":
        return _up_mapping(
            profile=profile,
            application=application,
            academic_record=academic_record,
            email=email,
        )
    if slug == "wits":
        return _wits_mapping(
            profile=profile,
            application=application,
            academic_record=academic_record,
            contacts=contacts,
            email=email,
        )
    raise ValueError(f"no field mapping built for portal slug {slug!r}")


def _title_case(value: Optional[str]) -> Optional[str]:
    """UCT's dropdowns use title-case entries ('English', 'African') where the
    profile may hold uppercase/lowercase."""
    if not value:
        return None
    return value.strip().title() or None


def _uct_sex(gender: Optional[str]) -> Optional[str]:
    if not gender:
        return None
    g = gender.strip().lower()
    if g.startswith("f"):
        return "Female"
    if g.startswith("m"):
        return "Male"
    if g.startswith("t"):
        return "Trans"
    return None


def _uct_date(value: Any, fmt: str) -> Optional[str]:
    if isinstance(value, date):
        return value.strftime(fmt)
    return None


def _uct_mapping(
    *, profile: Any, application: Any, academic_record: Any, contacts: Any,
    email: Optional[str],
) -> FieldMapping:
    """UCT field values keyed to uct.fields.json. Guardian falls back through
    guardian → next_of_kin → fee_payer contact types (UCT wants a P/G + fee
    payer; 'guardian is also fee payer' keeps step 4 to one person). Subjects
    carry the Gr11 final %; the Gr12 April % defaults to the same value until
    per-record-type capture lands (the grid auto-copies subjects anyway).
    Redress answers pass through from `profile.redress_factors` (keys match the
    uct.fields.json redress_* ids, with or without the prefix)."""
    guardian = (
        _contact_by_type(contacts, "guardian")
        or _contact_by_type(contacts, "next_of_kin")
        or _contact_by_type(contacts, "fee_payer")
    )
    app_year = _g(application, "application_year")
    matric_year = _g(academic_record, "year")
    if matric_year is None and isinstance(app_year, int):
        matric_year = app_year - 1

    redress_raw = _g(profile, "redress_factors") or {}
    redress: dict[str, Any] = {}
    if isinstance(redress_raw, dict):
        for key, value in redress_raw.items():
            name = key if key.startswith("redress_") else f"redress_{key}"
            redress[name] = value

    values: dict[str, Any] = {
        # account creation (also passed via credentials.extra by the wiring)
        "first_name": _g(profile, "first_name"),
        "last_name": _g(profile, "last_name"),
        "date_of_birth": _uct_date(_g(profile, "date_of_birth"), "%d/%m/%Y"),
        "id_number": _g(profile, "id_number"),
        "email": email,
        # step 2 — personal
        "title": _title_case(_g(profile, "title")),
        "sex": _uct_sex(_g(profile, "gender")),
        "home_language": _title_case(_g(profile, "home_language")),
        "citizenship_type": "SA Citizen" if _g(profile, "is_sa_citizen") else None,
        "race": _title_case(_g(profile, "ethnicity")),
        "sa_id": _g(profile, "id_number"),
        # step 3 — contact
        "postal_code": _g(profile, "postal_code"),
        "suburb": (_g(profile, "suburb") or "").upper() or None,
        "address_line_1": _g(profile, "street_address"),
        "phone": _g(profile, "phone"),
        # step 4 — parent/guardian + fee payer
        "guardian_title": _title_case(_g(guardian, "title")),
        "guardian_first_name": _g(guardian, "first_name"),
        "guardian_last_name": _g(guardian, "last_name"),
        "guardian_id_number": _g(guardian, "id_number"),
        "guardian_relationship": _title_case(_g(guardian, "relationship")),
        "guardian_email": _g(guardian, "email"),
        "guardian_phone": _g(guardian, "phone"),
        "guardian_is_fee_payer": True,
        # step 5 — school + subjects
        "matric_year": str(matric_year) if matric_year is not None else None,
        "school_terms": "4 Terms",
        "school_qualification": "NSC(DBE, IEB or SACAI)",
        "school": _g(academic_record, "institution"),
        "school_province": _title_case(_g(profile, "province")),
        "subjects": _coerce_subjects(_g(academic_record, "subjects")),
        # step 6 / 11 / 12 — switches
        "applied_before": "No",
        "nsfas_other_institution": "No",
        "needs_financial_assistance": _yn(_g(profile, "applying_nsfas")),
        "wants_housing": _yn(_g(profile, "wants_residence")),
        # step 8 — choices
        "choice_level": "Undergraduate",
        "programme": _g(application, "programme"),
        # step 10 — NBT (precondition; student-supplied)
        "nbt_registration_number": _g(profile, "nbt_reference"),
        "nbt_year": _g(profile, "nbt_year"),
        "nbt_date": _uct_date(_g(profile, "nbt_date"), "%d/%m/%y"),
    }
    values.update(redress)
    return FieldMapping(values={k: v for k, v in values.items() if v is not None})


def _up_gender(gender: Optional[str]) -> Optional[str]:
    """UP's set (live-verified): Female / Male / Unspecified-Non-Binary."""
    if not gender:
        return None
    g = gender.strip().lower()
    if g.startswith("f"):
        return "Female"
    if g.startswith("m"):
        return "Male"
    return "Unspecified/Non-Binary"


def _up_mapping(
    *, profile: Any, application: Any, academic_record: Any,
    email: Optional[str],
) -> FieldMapping:
    """UP field values keyed to up.fields.json. The new-application identity
    fields also travel via credentials.extra (the runtime hands the mapping over
    only after login). Subject percentages double as the NSC level source (the
    adapter derives level = band(percent) — UP's percent dropdown is gated on
    the level). The examining authority defaults to '<province> DoE' and is
    fuzzy-matched against the live board list by the adapter."""
    app_year = _g(application, "application_year")
    matric_year = _g(academic_record, "year")
    if matric_year is None and isinstance(app_year, int):
        matric_year = app_year - 1
    province = _title_case(_g(profile, "province"))

    values: dict[str, Any] = {
        # new-application form (also passed via credentials.extra)
        "first_name": _g(profile, "first_name"),
        "last_name": _g(profile, "last_name"),
        "email": email,
        "date_of_birth": _uct_date(_g(profile, "date_of_birth"), "%Y-%m-%d"),
        "id_number": _g(profile, "id_number"),
        "application_year": str(app_year) if app_year is not None else None,
        # Personal Information
        "title": _title_case(_g(profile, "title")),
        "preferred_name": _g(profile, "preferred_name") or _g(profile, "first_name"),
        # Contact Details
        "address_line_1": _g(profile, "street_address"),
        "suburb": _g(profile, "suburb"),
        "city": _g(profile, "city"),
        "postal_code": _g(profile, "postal_code"),
        "phone": _g(profile, "phone"),
        # Demographic Details
        "gender": _up_gender(_g(profile, "gender")),
        "home_language": _title_case(_g(profile, "home_language")),
        "population_group": _title_case(_g(profile, "ethnicity")),
        "tell_us_more": "I am currently still in high school",
        # Tertiary / Secondary Education
        "prev_enrolled": "No",
        "final_school_year": str(matric_year) if matric_year is not None else None,
        "examining_authority": f"{province} DoE" if province else None,
        "school": _g(academic_record, "institution"),
        "school_grades_type": "Nat Senior Cert or IEB",
        "highest_grade": "Grade 11",
        "exam_number": _g(profile, "exam_number"),
        "exemption_type": "Currently busy with schooling",
        "subjects": _coerce_subjects(_g(academic_record, "subjects")),
        # Study Choice
        "programme": _g(application, "programme"),
        "programme_second": _g(application, "programme_second"),
        # General Details
        "wants_residence": _yn(_g(profile, "wants_residence")) or "No",
        "applying_nsfas": _yn(_g(profile, "applying_nsfas")) or "No",
        "up_funding": "No",
    }
    return FieldMapping(values={k: v for k, v in values.items() if v is not None})


def _wits_gender(gender: Optional[str]) -> Optional[str]:
    """Wits' set (live-verified): Female / Gender Neutral / Male."""
    if not gender:
        return None
    g = gender.strip().lower()
    if g.startswith("f"):
        return "Female"
    if g.startswith("m"):
        return "Male"
    return "Gender Neutral"


def _wits_population(ethnicity: Optional[str]) -> Optional[str]:
    """Wits' Population Group set (live-verified): Asian / Black / Coloured /
    Indian / White — notably 'Black' where the profile stores 'African'."""
    if not ethnicity:
        return None
    e = ethnicity.strip().lower()
    if e in ("african", "black", "black african"):
        return "Black"
    return ethnicity.strip().title()


def _wits_mapping(
    *, profile: Any, application: Any, academic_record: Any, contacts: Any,
    email: Optional[str],
) -> FieldMapping:
    """Wits field values keyed to wits.fields.json. The Create-Application-ID
    identity fields also travel via credentials.extra (the runtime hands the
    mapping over only after login). The examining authority is the plain
    province name (live-verified — not '<province> DoE' like UP); the next of
    kin is required and the portal enforces NOK mobile/email ≠ applicant's
    (preconditioned by the adapter)."""
    nok = (
        _contact_by_type(contacts, "next_of_kin")
        or _contact_by_type(contacts, "guardian")
        or _contact_by_type(contacts, "fee_payer")
    )
    app_year = _g(application, "application_year")
    matric_year = _g(academic_record, "year")
    if matric_year is None and isinstance(app_year, int):
        matric_year = app_year - 1
    nok_first = _g(nok, "first_name") or ""

    values: dict[str, Any] = {
        # Create Application ID (also passed via credentials.extra)
        "nationality": "South Africa" if _g(profile, "is_sa_citizen") else None,
        "title": _title_case(_g(profile, "title")),
        "first_name": _g(profile, "first_name"),
        "middle_names": _g(profile, "middle_names"),
        "last_name": _g(profile, "last_name"),
        "date_of_birth": _uct_date(_g(profile, "date_of_birth"), "%d/%m/%Y"),
        "gender": _wits_gender(_g(profile, "gender")),
        "id_number": _g(profile, "id_number"),
        "email": email,
        "phone": _g(profile, "phone"),
        "application_year": str(app_year) if app_year is not None else None,
        # 3 Current Activities
        "current_activity": _g(profile, "current_activity") or "School",
        # 4 Secondary Education
        "school": _g(academic_record, "institution"),
        "examining_authority": _title_case(_g(profile, "province")),
        "examination_year": str(matric_year) if matric_year is not None else None,
        "examination_month": "November",
        "exam_number": _g(profile, "exam_number"),
        "subjects": _coerce_subjects(_g(academic_record, "subjects")),
        # 5 Tertiary Education
        "tertiary_studies": "No",
        # 6 Study Choices
        "programme": _g(application, "programme"),
        "programme_second": _g(application, "programme_second"),
        "programme_third": _g(application, "programme_third"),
        # 7 Domicilium Address (8/9 reuse it via 'Same as Other Address')
        "address_line_1": _g(profile, "street_address"),
        "suburb": _g(profile, "suburb"),
        "postal_code": _g(profile, "postal_code"),
        # 11 Demographic Details
        "marital_status": _title_case(_g(profile, "marital_status")) or "Single",
        "population_group": _wits_population(_g(profile, "ethnicity")),
        "home_language": _title_case(_g(profile, "home_language")),
        "religious_affiliation": _g(profile, "religious_affiliation"),
        "has_disability": _yn(bool(_g(profile, "disability"))),
        # 12 Next of Kin (+ 13 Emergency Contact copies it)
        "nok_title": _title_case(_g(nok, "title")),
        "nok_initial": (nok_first[:1].upper() or None),
        "nok_surname": _g(nok, "last_name"),
        "nok_phone": _g(nok, "phone"),
        "nok_email": _g(nok, "email"),
        "nok_relationship": _title_case(_g(nok, "relationship")),
    }
    return FieldMapping(values={k: v for k, v in values.items() if v is not None})


def _uj_mapping(
    *, profile: Any, application: Any, academic_record: Any, contacts: Any,
    email: Optional[str],
) -> FieldMapping:
    is_sa = _g(profile, "is_sa_citizen")
    nok = _contact_by_type(contacts, "next_of_kin")
    payer = _contact_by_type(contacts, "fee_payer")
    app_year = _g(application, "application_year")
    # matric (Gr12) year: a captured grade-12 record's year, else the year before
    # the intake year (apply 2027 → matric 2026).
    matric_year = _g(academic_record, "year")
    if matric_year is None and isinstance(app_year, int):
        matric_year = app_year - 1

    values: dict[str, Any] = {
        # Page A — Biographical
        "sa_citizen": _yn(is_sa),
        "id_number": _g(profile, "id_number"),
        "citizenship_code": "South Africa" if is_sa else _g(profile, "nationality"),
        "date_of_birth": _format_dob(_g(profile, "date_of_birth")),
        "title": (_g(profile, "title") or "").upper() or None,
        "initials": _initials(_g(profile, "first_name"), _g(profile, "middle_names")),
        "surname": _g(profile, "last_name"),
        "first_names": _full_first_names(
            _g(profile, "first_name"), _g(profile, "middle_names")
        ),
        "maiden_name": _g(profile, "maiden_name"),
        "marital_status": _g(profile, "marital_status"),
        "home_language": (_g(profile, "home_language") or "").upper() or None,
        "ethnic_group": (_g(profile, "ethnicity") or "").upper() or None,
        "street_address_1": _g(profile, "street_address"),
        "street_address_2": _g(profile, "suburb"),
        "street_address_3": _g(profile, "city"),
        "street_address_4": _g(profile, "province"),
        "postal_code": _g(profile, "postal_code"),
        "sa_cell": _g(profile, "phone"),
        "email": email,
        "verify_email": email,
        "apply_residence": _yn(_g(profile, "wants_residence")),
        "has_disability": _yn(bool(_g(profile, "disability"))),
        # Page B — Next of Kin + Account (fee payer)
        "nok_name": _contact_name(nok),
        "nok_mobile": _g(nok, "phone"),
        "account_name": _contact_name(payer),
        "account_mobile": _g(payer, "phone"),
        "account_addr_1": _g(payer, "street_address"),
        "account_addr_2": _g(payer, "suburb"),
        "account_addr_3": _g(payer, "city"),
        "account_addr_4": _g(payer, "province"),
        "account_postal_code": _g(payer, "postal_code"),
        "account_email": _g(payer, "email"),
        # Page C — Matric
        "matric_year": str(matric_year) if matric_year is not None else None,
        "ug_or_pg": "Undergraduate",
        "upgrading": "No",
        "matric_type": "SA Matric",
        "endorsement": "CURRENTLY IN GR.12",
        "exam_number": _g(profile, "exam_number"),
        "subjects": _coerce_subjects(_g(academic_record, "subjects")),
        # Page D — Previous Studies
        "school": _g(academic_record, "institution"),
        "present_activity": _g(profile, "current_activity") or "GRADE 12 PUPIL",
        "studied_before": "No",
        # Page E — Qualifications (faculty unresolved — see module docstring)
        "academic_year": str(app_year) if app_year is not None else None,
        "applying_for": "Curricular Courses",
        "programme": _g(application, "programme"),
        "year_of_study": "FIRST YEAR",
    }
    # Drop keys that resolved to None so the adapter's "unmapped → skip" logic
    # (and conditional-field handling) behaves as designed.
    return FieldMapping(values={k: v for k, v in values.items() if v is not None})
