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
