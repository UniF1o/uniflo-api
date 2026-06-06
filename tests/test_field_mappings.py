"""field_mappings persistence (app.ai.field_mapping.persist_field_mapping) and
the review-screen read (applications service.get_field_mapping). DB mocked."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.ai.field_mapping import persist_field_mapping
from app.ai.schemas import FieldMappingEntry, FieldMappingResponse
from app.api.applications import service

USER_ID = "a1b2c3d4-0000-0000-0000-000000000000"


def _response(app_id, uni_id):
    return FieldMappingResponse(
        university_id=uni_id,
        application_id=app_id,
        entries=[
            FieldMappingEntry(field_id="surname", value="Doe", confidence=0.95),
            FieldMappingEntry(field_id="programme", value="Civil", confidence=0.6),
        ],
        overall_confidence=0.8,
    )


# --- persistence ---------------------------------------------------------------

def test_persist_inserts_when_absent():
    session = MagicMock()
    session.exec.return_value.first.return_value = None
    rec = persist_field_mapping(session, _response(uuid4(), uuid4()), threshold=0.85)
    session.add.assert_called_once()
    assert rec.overall_confidence == 0.8
    assert rec.confidence_threshold == 0.85
    assert len(rec.entries) == 2
    assert rec.entries[0]["field_id"] == "surname"
    assert rec.entries[0]["confidence"] == 0.95


def test_persist_updates_existing():
    session = MagicMock()
    existing = MagicMock()
    session.exec.return_value.first.return_value = existing
    rec = persist_field_mapping(session, _response(uuid4(), uuid4()), threshold=0.9)
    assert rec is existing
    assert existing.overall_confidence == 0.8
    assert existing.confidence_threshold == 0.9
    assert len(existing.entries) == 2


# --- review-screen read --------------------------------------------------------

def _record(app_id, uni_id):
    return SimpleNamespace(
        application_id=app_id,
        university_id=uni_id,
        overall_confidence=0.8,
        confidence_threshold=0.85,
        entries=[
            {"field_id": "surname", "value": "Doe", "confidence": 0.95,
             "reasoning": "", "source_profile_field": "last_name"},
            {"field_id": "programme", "value": "Civil", "confidence": 0.6,
             "reasoning": "guess", "source_profile_field": None},
        ],
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )


def test_get_field_mapping_flags_low_confidence():
    profile_id, app_id, uni_id = uuid4(), uuid4(), uuid4()
    session = MagicMock()
    profile = SimpleNamespace(id=profile_id)
    application = SimpleNamespace(student_id=profile_id)
    session.exec.return_value.first.side_effect = [profile, _record(app_id, uni_id)]
    session.get.return_value = application

    result = service.get_field_mapping(session, USER_ID, app_id)
    assert result.overall_confidence == 0.8
    by_id = {e.field_id: e for e in result.entries}
    assert by_id["surname"].flagged is False   # 0.95 >= 0.85
    assert by_id["programme"].flagged is True   # 0.6 < 0.85


def test_get_field_mapping_404_when_not_owned():
    session = MagicMock()
    session.exec.return_value.first.return_value = SimpleNamespace(id=uuid4())
    session.get.return_value = SimpleNamespace(student_id=uuid4())  # different owner
    with pytest.raises(HTTPException) as exc:
        service.get_field_mapping(session, USER_ID, uuid4())
    assert exc.value.status_code == 404


def test_get_field_mapping_404_when_no_mapping():
    profile_id = uuid4()
    session = MagicMock()
    session.exec.return_value.first.side_effect = [
        SimpleNamespace(id=profile_id), None
    ]
    session.get.return_value = SimpleNamespace(student_id=profile_id)
    with pytest.raises(HTTPException) as exc:
        service.get_field_mapping(session, USER_ID, uuid4())
    assert exc.value.status_code == 404
    assert exc.value.detail == "field_mapping_not_found"
