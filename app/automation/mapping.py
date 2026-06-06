"""Build a portal `FieldMapping` from the Uniflo data model.

This is the deterministic bridge between our DB (StudentProfile, Contact,
AcademicRecord, Application) and an adapter's `field_id`s. It maps the
straightforward fields directly; two areas need a resolution layer that isn't
built yet (tracked as the AI-mapping item):

  * **subject names** — `academic_records.subjects` stores plain NSC names
    (e.g. "Mathematics"); UJ's LOV wants its qualifier-tagged variant
    ("MATHEMATICS (NSC/NCV/ISC)"). We pass the upper-cased name as a best-effort
    search term.
  * **faculty / programme** — `application.programme` is free text; UJ wants a
    faculty + an `(ELIGIBLE TO APPLY-Y)` programme from its LOV. Left as
    pass-through (`faculty` unset) until a per-portal programme catalogue / AI
    resolver exists; a real run will currently stall on Page E.

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
    raise ValueError(f"no field mapping built for portal slug {slug!r}")


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
