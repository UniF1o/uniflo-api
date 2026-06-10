"""Adapter registry, the profile→FieldMapping builder, and the background
dispatch helpers. No DB or browser — the DB-bound `_run_real_automation` is
covered by the pure helpers it composes (`_apply_result`, `_map_error_code`,
`_generate_pin`) plus the routing test."""

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.api.automation.background as bg
from app.api.automation.background import (
    JOB_ERROR_CODES,
    _apply_result,
    _map_error_code,
    derive_portal_pin,
)
from app.automation.adapters import (
    UJAdapter,
    get_adapter,
    get_adapter_for_university,
    registered_slugs,
)
from app.automation.mapping import build_field_mapping
from app.automation.results import JobFailure, RunOutcome, SubmissionResult

# --- registry ------------------------------------------------------------------

def test_get_adapter_by_slug():
    assert isinstance(get_adapter("uj"), UJAdapter)
    assert get_adapter("does-not-exist") is None


def test_get_adapter_for_university():
    assert isinstance(get_adapter_for_university(UJAdapter.university_id), UJAdapter)
    assert get_adapter_for_university(uuid.uuid4()) is None


def test_registered_slugs():
    assert "uj" in registered_slugs()


# --- mapping builder -----------------------------------------------------------

def _profile():
    return SimpleNamespace(
        is_sa_citizen=True, id_number="0803124001089", nationality="South Africa",
        date_of_birth=date(2008, 3, 12), title="Miss", first_name="Jane",
        middle_names=None, last_name="Doe", maiden_name=None, marital_status="Single",
        home_language="English", ethnicity="African", street_address="24 Acacia Road",
        suburb="Soshanguve", city="Pretoria", province="Gauteng", postal_code="0152",
        phone="0825550142", wants_residence=False, disability=None, exam_number=None,
        current_activity=None,
    )


def _contact(ctype, **kw):
    base = dict(
        contact_type=ctype, first_name=None, last_name=None, phone=None, email=None,
        street_address=None, suburb=None, city=None, province=None, postal_code=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_uj_mapping_direct_fields():
    contacts = [
        _contact("next_of_kin", first_name="John", last_name="Doe", phone="0825550188"),
        _contact(
            "fee_payer", first_name="John", last_name="Doe", phone="0825550188",
            email="john@x.com", street_address="24 Acacia Road", suburb="Soshanguve",
            city="Pretoria", province="Gauteng", postal_code="0152",
        ),
    ]
    record = SimpleNamespace(
        year=2026, institution="SOSHANGUVE SECONDARY SCHOOL",
        subjects=[
            {"subject": "Mathematics", "mark": 72},
            {"name": "English Home Language", "percentage": 75},
        ],
    )
    application = SimpleNamespace(programme="BEng Civil", application_year=2027)
    m = build_field_mapping(
        "uj", profile=_profile(), application=application, academic_record=record,
        contacts=contacts, email="jane@x.com",
    )
    assert m.get("sa_citizen") == "Yes"
    assert m.get("citizenship_code") == "South Africa"
    assert m.get("date_of_birth") == "12-MAR-2008"
    assert m.get("title") == "MISS"
    assert m.get("initials") == "J"
    assert m.get("surname") == "Doe"
    assert m.get("home_language") == "ENGLISH"
    assert m.get("ethnic_group") == "AFRICAN"
    assert m.get("street_address_1") == "24 Acacia Road"
    assert m.get("email") == "jane@x.com" and m.get("verify_email") == "jane@x.com"
    assert m.get("apply_residence") == "No"
    assert m.get("nok_name") == "John Doe" and m.get("nok_mobile") == "0825550188"
    assert m.get("account_email") == "john@x.com"
    assert m.get("matric_year") == "2026"
    assert m.get("academic_year") == "2027"
    assert m.get("school") == "SOSHANGUVE SECONDARY SCHOOL"
    assert m.get("present_activity") == "GRADE 12 PUPIL"
    subs = m.get("subjects")
    assert {"name": "MATHEMATICS", "percentage": 72} in subs
    assert {"name": "ENGLISH HOME LANGUAGE", "percentage": 75} in subs


def test_uj_mapping_matric_year_falls_back_to_intake_minus_one():
    application = SimpleNamespace(programme="X", application_year=2027)
    m = build_field_mapping(
        "uj", profile=_profile(), application=application,
        academic_record=None, contacts=[], email=None,
    )
    assert m.get("matric_year") == "2026"  # 2027 intake → 2026 matric
    # unmapped (None) keys are dropped
    assert m.get("email") is None
    assert "nok_name" not in m.values


def test_build_field_mapping_unknown_slug():
    application = SimpleNamespace(programme="X", application_year=2027)
    with pytest.raises(ValueError):
        build_field_mapping("wits", profile=_profile(), application=application)


# --- background helpers --------------------------------------------------------

def test_derive_portal_pin_valid_and_deterministic():
    for _ in range(300):
        aid = uuid.uuid4()
        pin = derive_portal_pin(aid)
        assert len(pin) == 5 and pin.isdigit()
        assert pin[0] != "0"  # cannot start with 0
        assert all(pin[i] != pin[i + 1] for i in range(4))  # no consecutive repeats
        # deterministic: same application id -> same PIN (stable across retries)
        assert derive_portal_pin(aid) == pin


def test_derive_portal_pin_differs_by_application():
    a, b = uuid.uuid4(), uuid.uuid4()
    # overwhelmingly likely to differ; guards against a constant PIN
    assert derive_portal_pin(a) != derive_portal_pin(b)


def test_consent_required_is_canonical():
    assert "consent_required" in JOB_ERROR_CODES


# --- AI mapping generation -----------------------------------------------------

def test_ai_configured(monkeypatch):
    monkeypatch.setattr(bg.settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(bg.settings, "GEMINI_API_KEY", "k")
    assert bg._ai_configured() is True
    monkeypatch.setattr(bg.settings, "GEMINI_API_KEY", None)
    assert bg._ai_configured() is False
    monkeypatch.setattr(bg.settings, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(bg.settings, "ANTHROPIC_API_KEY", "k")
    assert bg._ai_configured() is True


def test_portal_form_schema_from_uj_adapter():
    form = bg._portal_form_schema(UJAdapter())
    assert form.slug == "uj"
    ids = {f.field_id for f in form.fields}
    assert {"sa_citizen", "programme"} <= ids


def test_generate_ai_mapping_skips_when_unconfigured(monkeypatch):
    monkeypatch.setattr(bg, "_ai_configured", lambda: False)
    session = MagicMock()
    bg._generate_ai_mapping(
        session, SimpleNamespace(id=uuid.uuid4()), object(), None, None
    )
    session.commit.assert_not_called()


def test_generate_ai_mapping_persists_when_configured(monkeypatch):
    import app.ai.client as client_mod
    import app.ai.field_mapping as fm
    from app.ai.schemas import FieldMappingEntry, FieldMappingResponse

    app_id = uuid.uuid4()
    monkeypatch.setattr(bg, "_ai_configured", lambda: True)
    monkeypatch.setattr(bg, "_portal_form_schema", lambda adapter: object())
    monkeypatch.setattr(
        client_mod.AIClient, "from_env", classmethod(lambda cls: object())
    )

    async def fake_map(**kwargs):
        return FieldMappingResponse(
            university_id=uuid.uuid4(),
            application_id=app_id,
            entries=[FieldMappingEntry(field_id="surname", value="Doe", confidence=0.9)],
            overall_confidence=0.9,
        )

    captured = {}
    monkeypatch.setattr(fm, "map_application_to_portal", fake_map)
    monkeypatch.setattr(
        fm, "persist_field_mapping", lambda session, response: captured.update(r=response)
    )

    session = MagicMock()
    adapter = SimpleNamespace(form_schema=lambda: {})
    bg._generate_ai_mapping(
        session, SimpleNamespace(id=app_id), adapter, MagicMock(), None
    )
    assert captured["r"].application_id == app_id
    session.commit.assert_called_once()


def test_generate_ai_mapping_survives_failure(monkeypatch):
    import app.ai.client as client_mod
    import app.ai.field_mapping as fm

    monkeypatch.setattr(bg, "_ai_configured", lambda: True)
    monkeypatch.setattr(bg, "_portal_form_schema", lambda adapter: object())
    monkeypatch.setattr(
        client_mod.AIClient, "from_env", classmethod(lambda cls: object())
    )

    async def boom(**kwargs):
        raise RuntimeError("gemini down")

    monkeypatch.setattr(fm, "map_application_to_portal", boom)
    session = MagicMock()
    adapter = SimpleNamespace(form_schema=lambda: {})
    # must not raise (best-effort) and must not commit a partial mapping
    bg._generate_ai_mapping(
        session, SimpleNamespace(id=uuid.uuid4()), adapter, MagicMock(), None
    )
    session.commit.assert_not_called()


def test_consent_gate(monkeypatch):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(bg.settings, "AUTOMATION_ALLOW_SUBMIT", True)
    # no POPI consent -> can't even run (won't tick POPI / fill)
    assert bg._consent_gate(
        SimpleNamespace(popi_consent_at=None, agreement_consent_at=None)
    ) == (False, False)
    # POPI only -> runs, but no submit (agreement missing)
    assert bg._consent_gate(
        SimpleNamespace(popi_consent_at=now, agreement_consent_at=None)
    ) == (True, False)
    # both consented + setting on -> run + submit
    assert bg._consent_gate(
        SimpleNamespace(popi_consent_at=now, agreement_consent_at=now)
    ) == (True, True)
    # both consented but submit gate OFF -> run, never submit
    monkeypatch.setattr(bg.settings, "AUTOMATION_ALLOW_SUBMIT", False)
    assert bg._consent_gate(
        SimpleNamespace(popi_consent_at=now, agreement_consent_at=now)
    ) == (True, False)


def test_map_error_code_stays_in_canonical_set():
    assert _map_error_code("timeout") == "timeout"
    assert _map_error_code("portal_changed") == "form_submit_failed"
    assert _map_error_code("auth_failed") == "login_failed"
    assert _map_error_code(None) == "internal_error"
    assert _map_error_code("something_unknown") == "internal_error"
    for code in ("timeout", "portal_changed", "auth_failed", None, "x"):
        assert _map_error_code(code) in JOB_ERROR_CODES


def _app_job():
    return (
        SimpleNamespace(status="processing", submitted_at=None),
        SimpleNamespace(status="processing", attempts=0, last_error=None),
    )


def test_apply_result_filled_leaves_processing_unsubmitted():
    app, job = _app_job()
    _apply_result(app, job, SubmissionResult(outcome=RunOutcome.FILLED))
    assert app.status == "processing" and app.submitted_at is None
    assert job.status == "processing" and job.attempts == 1 and job.last_error is None


def test_apply_result_submitted_sets_submitted_at():
    app, job = _app_job()
    _apply_result(app, job, SubmissionResult(outcome=RunOutcome.SUBMITTED))
    assert app.status == "submitted" and app.submitted_at is not None
    assert job.status == "submitted" and job.last_error is None


def test_apply_result_failed_maps_error_code():
    app, job = _app_job()
    job.attempts = 1
    _apply_result(
        app, job,
        SubmissionResult(
            outcome=RunOutcome.FAILED,
            failure=JobFailure(code="portal_changed", message="drift"),
        ),
    )
    assert app.status == "failed"
    assert job.status == "failed" and job.last_error == "form_submit_failed"
    assert job.attempts == 2


# --- routing -------------------------------------------------------------------

def test_process_application_routes_by_flag(monkeypatch):
    calls = []
    monkeypatch.setattr(bg, "_run_fake_automation", lambda aid: calls.append(("fake", aid)))
    monkeypatch.setattr(bg, "_run_real_automation", lambda aid: calls.append(("real", aid)))
    aid = uuid.uuid4()

    monkeypatch.setattr(bg.settings, "FAKE_AUTOMATION", True)
    bg.process_application(aid)
    monkeypatch.setattr(bg.settings, "FAKE_AUTOMATION", False)
    bg.process_application(aid)

    assert calls == [("fake", aid), ("real", aid)]
