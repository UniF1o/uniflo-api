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
    """Normalise `academic_records.subjects` JSON into
    [{name, percentage, nsc_level?}]. Accepts a list of dicts (various key
    names) or a {name: mark} dict. The captured NSC level rides along so
    portals that want it (UP) use the student's actual level rather than a
    derived one."""
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
                subject = {"name": str(name).upper(), "percentage": mark}
                if item.get("nsc_level") is not None:
                    subject["nsc_level"] = item["nsc_level"]
                out.append(subject)
    return out


# --- academic-record selection (by record_type) -------------------------------------

def _as_records(academic_record: Any) -> list[Any]:
    """`build_field_mapping` accepts one record or the student's full list."""
    if academic_record is None:
        return []
    if isinstance(academic_record, (list, tuple)):
        return [r for r in academic_record if r is not None]
    return [academic_record]


def _pick_record(
    records: list[Any], *preferred: str, fallback: bool = True
) -> Optional[Any]:
    """The first record matching a preferred `record_type` (in order); with
    `fallback` (the default) the first record at all — so a single legacy
    record keeps working. `fallback=False` returns None on no match (used
    where merging the wrong grade's marks would be worse than none)."""
    for record_type in preferred:
        for record in records:
            if _g(record, "record_type") == record_type:
                return record
    if fallback:
        return records[0] if records else None
    return None


def _matric_year(records: list[Any], app_year: Any) -> Optional[int]:
    """The Grade 12 (matric) year: a captured Grade-12 record's year wins;
    otherwise the year before the intake year (apply 2027 → matric 2026); a
    bare record's year is the last resort (legacy single-record behaviour)."""
    gr12 = _pick_record(records, "grade_12_final", "grade_12_april", "grade_12_june")
    if gr12 is not None and _g(gr12, "record_type", "").startswith("grade_12"):
        return _g(gr12, "year")
    if isinstance(app_year, int):
        return app_year - 1
    return _g(records[0], "year") if records else None


def _marks_by_subject(record: Any) -> dict[str, Any]:
    """Subject name (uppercased) → mark, for merging Gr12 April/June marks
    onto the Gr11 subject list by name."""
    return {
        s["name"]: s.get("percentage")
        for s in _coerce_subjects(_g(record, "subjects"))
        if s.get("percentage") is not None
    }


# --- contact resolution ----------------------------------------------------------------

# Across the four live-verified portals, ONE adult contact satisfies every
# requirement: UP asks for nobody; UJ's next of kin and account/fee payer may
# be the same person ("can be yourself or any other party"); UCT collapses
# parent/guardian + fee payer via its "guardian is also fee payer" checkbox;
# Wits' emergency contact has a "same details as Next of Kin" toggle. These
# fallback chains make any single captured contact power all portals — a
# separate fee_payer row is only needed when the payer genuinely differs.
_CONTACT_FALLBACKS: dict[str, tuple[str, ...]] = {
    "next_of_kin": ("next_of_kin", "guardian", "fee_payer"),
    "guardian": ("guardian", "next_of_kin", "fee_payer"),
    "fee_payer": ("fee_payer", "guardian", "next_of_kin"),
    "emergency": ("emergency", "next_of_kin", "guardian", "fee_payer"),
}


def _contact_by_type(contacts: Any, contact_type: str) -> Optional[Any]:
    for c in contacts or []:
        if _g(c, "contact_type") == contact_type:
            return c
    return None


def _resolve_contact(contacts: Any, role: str) -> Optional[Any]:
    """The contact for a portal role, falling back through the equivalence
    chain above when the exact type wasn't captured."""
    for contact_type in _CONTACT_FALLBACKS.get(role, (role,)):
        contact = _contact_by_type(contacts, contact_type)
        if contact is not None:
            return contact
    return None


def _payer_field(payer: Any, profile: Any, field: str) -> Any:
    """A fee-payer address field, standing in the student's own when the payer
    exists but carries no address. None when there is no payer at all (so the
    usual drop-unmapped behaviour applies)."""
    if payer is None:
        return None
    return _g(payer, field) or _g(profile, field)


# --- programme choices -----------------------------------------------------------------

def _choice(choices: Any, application: Any, n: int) -> Any:
    """Programme choice `n` (1-based): the ordered `application_choices` list
    when provided, the legacy `applications.programme` column for choice 1,
    and attribute passthrough last (keeps dict/namespace test fixtures
    working)."""
    if choices and len(choices) >= n:
        return choices[n - 1]
    if n == 1:
        return _g(application, "programme")
    return _g(application, ("programme_second", "programme_third")[n - 2])


# Portals that implement the completed-matric / gap-year automation branch.
# Extended in Task 6 as each adapter gains completed-matric support.
_COMPLETED_MATRIC_SLUGS: frozenset[str] = frozenset({"up", "uj"})


def _applicant_branch(profile: Any, records: list[Any]) -> str:
    """'completed_matric' or 'current_learner'.

    A grade_12_final record is the primary signal; current_activity patterns
    are the fallback for applicants who completed matric but haven't uploaded
    their final results yet."""
    if _pick_record(records, "grade_12_final", fallback=False) is not None:
        return "completed_matric"
    activity = str(_g(profile, "current_activity") or "").lower()
    if any(k in activity for k in ("gap", "employ", "work", "occupat", "complete")):
        return "completed_matric"
    return "current_learner"


def _guard_applicant_type(
    profile: Any, slug: str, records: list[Any]
) -> None:
    """Raise ValueError for applicant types the automation can't handle.

    Universally blocked: at-university / transfer, upgrader (separate branch),
    postgrad. Completed-matric / gap-year is permitted for UP (Task 5); other
    portals still require the applicant to be currently in Grade 12 until Task 6
    extends their adapters."""
    activity = str(_g(profile, "current_activity") or "").lower()
    if activity and any(
        k in activity for k in ("universit", "upgrad", "postgrad")
    ):
        raise ValueError(
            f"{slug}: portal automation does not support at-university, "
            f"upgrader or postgrad applicants — activity: {activity!r}"
        )
    if slug in _COMPLETED_MATRIC_SLUGS:
        return
    if activity and any(
        k in activity for k in ("gap", "employ", "work", "occupat", "complete")
    ):
        raise ValueError(
            f"{slug}: portal automation currently supports applicants still in "
            f"Grade 12 — profile activity {activity!r} would be misreported; "
            "manual application required until the completed-matric flow is built"
        )


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
    choices: Any = None,
) -> FieldMapping:
    """Build a `FieldMapping` for the given portal `slug`. Raises ValueError
    for a portal with no mapping yet (and for applicant situations the
    adapters would misreport — see `_require_current_schooling`).
    `academic_record` takes either one record or the student's full list —
    with a list, each portal picks by `record_type` (Gr11 finals feed the
    grids; UCT additionally merges grade_12_april/grade_12_june marks).
    `choices` is the ordered programme list from `application_choices`
    (choice 1 mirrors `applications.programme`)."""
    records = _as_records(academic_record)
    _guard_applicant_type(profile, slug, records)
    if slug == "uj":
        return _uj_mapping(
            profile=profile,
            application=application,
            academic_record=academic_record,
            contacts=contacts,
            email=email,
            choices=choices,
        )
    if slug == "uct":
        return _uct_mapping(
            profile=profile,
            application=application,
            academic_record=academic_record,
            contacts=contacts,
            email=email,
            choices=choices,
        )
    if slug == "up":
        return _up_mapping(
            profile=profile,
            application=application,
            academic_record=academic_record,
            email=email,
            choices=choices,
        )
    if slug == "wits":
        return _wits_mapping(
            profile=profile,
            application=application,
            academic_record=academic_record,
            contacts=contacts,
            email=email,
            choices=choices,
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
    email: Optional[str], choices: Any = None,
) -> FieldMapping:
    """UCT field values keyed to uct.fields.json. The guardian resolves via
    the shared contact chain (UCT wants a P/G + fee payer; 'guardian is also
    fee payer' keeps step 4 to one person). Subjects carry the Gr11 final %;
    Grade 12 **April** marks come from a `grade_12_april` record when captured
    (defaulting to the Gr11 final % otherwise) and the optional **June** marks
    from a `grade_12_june` record — merged by subject name. Redress answers
    pass through from `profile.redress_factors` (keys match the
    uct.fields.json redress_* ids, with or without the prefix)."""
    guardian = _resolve_contact(contacts, "guardian")
    records = _as_records(academic_record)
    gr11 = _pick_record(records, "grade_11_final")
    app_year = _g(application, "application_year")
    matric_year = _matric_year(records, app_year)

    subjects = _coerce_subjects(_g(gr11, "subjects"))
    april = _marks_by_subject(
        _pick_record(records, "grade_12_april", fallback=False)
    )
    june = _marks_by_subject(
        _pick_record(records, "grade_12_june", fallback=False)
    )
    for subject in subjects:
        if subject["name"] in april:
            subject["april"] = april[subject["name"]]
        if subject["name"] in june:
            subject["june"] = june[subject["name"]]

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
        "school": _g(gr11, "institution"),
        "school_province": _title_case(_g(profile, "province")),
        "subjects": subjects,
        # step 6 / 11 / 12 — switches
        "applied_before": "No",
        "nsfas_other_institution": "No",
        "needs_financial_assistance": _yn(_g(profile, "applying_nsfas")),
        "wants_housing": _yn(_g(profile, "wants_residence")),
        # step 8 — choices
        "choice_level": "Undergraduate",
        "programme": _choice(choices, application, 1),
        "programme_second": _choice(choices, application, 2),
        # step 10 — NBT (precondition; student-supplied)
        "nbt_registration_number": _g(profile, "nbt_reference"),
        "nbt_year": _g(profile, "nbt_year"),
        "nbt_date": _uct_date(_g(profile, "nbt_date"), "%d/%m/%y"),
    }
    values.update(redress)
    return FieldMapping(values={k: v for k, v in values.items() if v is not None})


def _up_tell_us_more_completed(profile: Any) -> str:
    """Map current_activity to the UP 'Tell us more' option for a completed-matric
    applicant. Working/employed students get the employed option; all others
    (gap-year, unspecified) get the unemployed option."""
    activity = str(_g(profile, "current_activity") or "").lower()
    if any(k in activity for k in ("employ", "work", "occupat")):
        return (
            "I am working/employed and haven't studied before at a tertiary institution"
        )
    return "I am unemployed and haven't studied before at a tertiary institution"


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
    email: Optional[str], choices: Any = None,
) -> FieldMapping:
    """UP field values keyed to up.fields.json. The new-application identity
    fields also travel via credentials.extra (the runtime hands the mapping over
    only after login). Subjects carry the captured NSC level when present (the
    adapter otherwise derives level = band(percent) — UP's percent dropdown is
    gated on the level). The examining authority defaults to '<province> DoE'
    and is fuzzy-matched against the live board list by the adapter.

    Branch-aware: grade_12_final records / gap-year current_activity trigger the
    completed-matric path (highest_grade=Grade 12, grade_12_final subjects,
    completed-matric tell_us_more and exemption_type)."""
    records = _as_records(academic_record)
    branch = _applicant_branch(profile, records)
    is_completed = branch == "completed_matric"

    app_year = _g(application, "application_year")
    matric_year = _matric_year(records, app_year)
    province = _title_case(_g(profile, "province"))

    if is_completed:
        subject_record = (
            _pick_record(records, "grade_12_final", fallback=False)
            or _pick_record(records, "grade_11_final")
        )
        tell_us_more = _up_tell_us_more_completed(profile)
        highest_grade = "Grade 12"
        exemption_type = "Admit to Bachelor Studies"
    else:
        subject_record = _pick_record(records, "grade_11_final")
        tell_us_more = "I am currently still in high school"
        highest_grade = "Grade 11"
        exemption_type = "Currently busy with schooling"

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
        "tell_us_more": tell_us_more,
        # Tertiary / Secondary Education
        "prev_enrolled": "No",
        "final_school_year": str(matric_year) if matric_year is not None else None,
        "examining_authority": f"{province} DoE" if province else None,
        "school": _g(subject_record, "institution"),
        "school_grades_type": "Nat Senior Cert or IEB",
        "highest_grade": highest_grade,
        "exam_number": _g(profile, "exam_number"),
        "exemption_type": exemption_type,
        "subjects": _coerce_subjects(_g(subject_record, "subjects")),
        # Study Choice
        "programme": _choice(choices, application, 1),
        "programme_second": _choice(choices, application, 2),
        # General Details
        "wants_residence": _yn(_g(profile, "wants_residence")) or "No",
        "preferred_residence": _g(profile, "preferred_residence"),
        "applying_nsfas": _yn(_g(profile, "applying_nsfas")) or "No",
        "up_funding": _yn(_g(profile, "applying_institutional_funding")) or "No",
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
    email: Optional[str], choices: Any = None,
) -> FieldMapping:
    """Wits field values keyed to wits.fields.json. The Create-Application-ID
    identity fields also travel via credentials.extra (the runtime hands the
    mapping over only after login). The examining authority is the plain
    province name (live-verified — not '<province> DoE' like UP); the next of
    kin is required and the portal enforces NOK mobile/email ≠ applicant's
    (preconditioned by the adapter). A mailing address differing from the
    residential one flows to step 9 (Postal) via postal_same=False + the
    postal_* block; otherwise the portal's 'Same as Domicilium' is used."""
    nok = _resolve_contact(contacts, "next_of_kin")
    records = _as_records(academic_record)
    gr11 = _pick_record(records, "grade_11_final")
    app_year = _g(application, "application_year")
    matric_year = _matric_year(records, app_year)
    nok_first = _g(nok, "first_name") or ""
    postal_same = _g(profile, "mailing_same_as_residential")

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
        "school": _g(gr11, "institution"),
        "examining_authority": _title_case(_g(profile, "province")),
        "examination_year": str(matric_year) if matric_year is not None else None,
        "examination_month": "November",
        "exam_number": _g(profile, "exam_number"),
        "subjects": _coerce_subjects(_g(gr11, "subjects")),
        # 5 Tertiary Education
        "tertiary_studies": "No",
        # 6 Study Choices
        "programme": _choice(choices, application, 1),
        "programme_second": _choice(choices, application, 2),
        "programme_third": _choice(choices, application, 3),
        # 7 Domicilium Address; 8 (Residential) is always 'Same as Domicilium'
        "address_line_1": _g(profile, "street_address"),
        "suburb": _g(profile, "suburb"),
        "postal_code": _g(profile, "postal_code"),
        # 9 Postal Address — only diverges when the profile says so
        "postal_same": _yn(postal_same if postal_same is not None else True),
        "postal_address_line_1": _g(profile, "mailing_street_address"),
        "postal_suburb": _g(profile, "mailing_suburb"),
        "postal_postal_code": _g(profile, "mailing_postal_code"),
        # 11 Demographic Details
        "marital_status": _title_case(_g(profile, "marital_status")) or "Single",
        "population_group": _wits_population(_g(profile, "ethnicity")),
        "home_language": _title_case(_g(profile, "home_language")),
        # the profile column is `religion` (the earlier key never resolved)
        "religious_affiliation": _title_case(_g(profile, "religion")),
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


def _uj_present_activity_completed(profile: Any) -> str:
    """UJ Page D 'What are you currently doing?' for a completed-matric applicant.
    Employed/working → EMPLOYED; gap-year/unspecified → UNEMPLOYED. The adapter
    fuzzy-matches against the live LOV, so minor text differences resolve at fill
    time. [VERIFY at the first live completed-matric run — only the GRADE 12 PUPIL
    option was walked live]."""
    activity = str(_g(profile, "current_activity") or "").lower()
    if any(k in activity for k in ("employ", "work", "occupat")):
        return "EMPLOYED"
    return "UNEMPLOYED"


def _uj_mapping(
    *, profile: Any, application: Any, academic_record: Any, contacts: Any,
    email: Optional[str], choices: Any = None,
) -> FieldMapping:
    is_sa = _g(profile, "is_sa_citizen")
    # One captured contact covers both roles (UJ's account contact "can be
    # yourself or any other party") — resolved via the shared fallback chains.
    nok = _resolve_contact(contacts, "next_of_kin")
    payer = _resolve_contact(contacts, "fee_payer")
    records = _as_records(academic_record)
    # Branch-aware (Task 6): a grade_12_final record / gap-year activity takes the
    # completed-matric path — Page C endorsement becomes the Bachelor's-degree NSC
    # pass (not "CURRENTLY IN GR.12"), the subjects/school come from the final
    # record, and Page D activity is no longer "GRADE 12 PUPIL".
    is_completed = _applicant_branch(profile, records) == "completed_matric"
    if is_completed:
        subject_record = (
            _pick_record(records, "grade_12_final", fallback=False)
            or _pick_record(records, "grade_11_final")
        )
        # A completed-matric degree applicant presents the Bachelor's-degree NSC
        # endorsement; UJ's endorsement LOV is fuzzy-matched, so minor text
        # differences resolve at fill time ([VERIFY] at the first live run — only
        # the current-Gr12 endorsement was walked).
        endorsement = "BACHELORS DEGREE"
        present_activity = _uj_present_activity_completed(profile)
    else:
        subject_record = _pick_record(records, "grade_11_final")
        endorsement = "CURRENTLY IN GR.12"
        present_activity = _g(profile, "current_activity") or "GRADE 12 PUPIL"
    app_year = _g(application, "application_year")
    matric_year = _matric_year(records, app_year)

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
        # Page B — Next of Kin + Account (fee payer). UJ demands the payer's
        # full address with no "same as student" option — when the resolved
        # payer has no address of their own, the student's address stands in
        # (matriculants typically live with the person paying).
        "nok_name": _contact_name(nok),
        "nok_mobile": _g(nok, "phone"),
        "account_name": _contact_name(payer),
        "account_mobile": _g(payer, "phone"),
        "account_addr_1": _payer_field(payer, profile, "street_address"),
        "account_addr_2": _payer_field(payer, profile, "suburb"),
        "account_addr_3": _payer_field(payer, profile, "city"),
        "account_addr_4": _payer_field(payer, profile, "province"),
        "account_postal_code": _payer_field(payer, profile, "postal_code"),
        "account_email": _g(payer, "email"),
        # Page C — Matric
        "matric_year": str(matric_year) if matric_year is not None else None,
        "ug_or_pg": "Undergraduate",
        "upgrading": "No",
        "matric_type": "SA Matric",
        "endorsement": endorsement,
        "exam_number": _g(profile, "exam_number"),
        "subjects": _coerce_subjects(_g(subject_record, "subjects")),
        # Page D — Previous Studies
        "school": _g(subject_record, "institution"),
        "present_activity": present_activity,
        "studied_before": "No",
        # Page E — Qualifications (faculty unresolved — see module docstring).
        # programme_second is mapped but the UJ adapter doesn't drive "Add
        # Qualification" yet (LOV reset behaviour untested) — known gap.
        "academic_year": str(app_year) if app_year is not None else None,
        "applying_for": "Curricular Courses",
        "programme": _choice(choices, application, 1),
        "programme_second": _choice(choices, application, 2),
        "year_of_study": "FIRST YEAR",
    }
    # Drop keys that resolved to None so the adapter's "unmapped → skip" logic
    # (and conditional-field handling) behaves as designed.
    return FieldMapping(values={k: v for k, v in values.items() if v is not None})
