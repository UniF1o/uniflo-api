"""Tests for POST /applications/{id}/challenge (answering a pending email
challenge) and the `pending_challenge` block on application reads."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.applications import service
from app.db import get_session
from app.main import app

client = TestClient(app)


def override_session():
    """Endpoint tests patch the service layer, so the session is never used —
    but the dependency must still be overridden or FastAPI builds a real
    engine from DATABASE_URL (absent/dummy in CI)."""
    app.dependency_overrides[get_session] = lambda: MagicMock()

VALID_USER_ID = "a1b2c3d4-0000-0000-0000-000000000000"
VALID_APPLICATION_ID = uuid.uuid4()
VALID_PROFILE_ID = uuid.uuid4()
CHALLENGE_ID = uuid.uuid4()


def auth_headers():
    return {"Authorization": "Bearer validtoken"}


def mock_auth(mock_decode):
    mock_decode.return_value = {
        "sub": VALID_USER_ID,
        "email": "student@gmail.com",
        "role": "student",
    }


def make_mock_application(pending_challenge=None):
    mock = MagicMock()
    mock.id = VALID_APPLICATION_ID
    mock.student_id = VALID_PROFILE_ID
    mock.university_id = uuid.uuid4()
    mock.programme = "BSc Computer Science"
    mock.programme_id = None
    mock.application_year = 2027
    mock.status = "action_required"
    mock.submitted_at = None
    mock.updated_at = None
    mock.created_at = datetime.now(timezone.utc)
    mock.popi_consent_at = datetime.now(timezone.utc)
    mock.agreement_consent_at = None
    mock.latest_job = None
    mock.choices = []
    mock.pending_challenge = pending_challenge
    return mock


def make_mock_challenge(requested_fields=None, supplied_at=None):
    mock = MagicMock()
    mock.id = CHALLENGE_ID
    mock.application_id = VALID_APPLICATION_ID
    mock.portal_slug = "uct"
    mock.requested_fields = requested_fields or ["otp"]
    mock.supplied_values = None
    mock.created_at = datetime.now(timezone.utc)
    mock.supplied_at = supplied_at
    return mock


# --- endpoint ------------------------------------------------------------------------


def test_supply_challenge_success():
    override_session()
    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.supply_challenge") as mock_supply:
        mock_auth(mock_decode)
        mock_supply.return_value = make_mock_application()

        response = client.post(
            f"/applications/{VALID_APPLICATION_ID}/challenge",
            json={"values": {"otp": "123456"}},
            headers=auth_headers(),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["pending_challenge"] is None
    mock_supply.assert_called_once()
    assert mock_supply.call_args.args[3] == {"otp": "123456"}


def test_supply_challenge_no_pending_404():
    override_session()
    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.supply_challenge") as mock_supply:
        mock_auth(mock_decode)
        mock_supply.side_effect = HTTPException(
            status_code=404, detail="no_pending_challenge"
        )

        response = client.post(
            f"/applications/{VALID_APPLICATION_ID}/challenge",
            json={"values": {"otp": "123456"}},
            headers=auth_headers(),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json()["detail"] == "no_pending_challenge"


def test_supply_challenge_empty_values_422():
    override_session()
    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.post(
            f"/applications/{VALID_APPLICATION_ID}/challenge",
            json={"values": {}},
            headers=auth_headers(),
        )
    app.dependency_overrides.clear()
    assert response.status_code == 422


def test_supply_challenge_blank_value_422():
    override_session()
    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.post(
            f"/applications/{VALID_APPLICATION_ID}/challenge",
            json={"values": {"otp": "   "}},
            headers=auth_headers(),
        )
    app.dependency_overrides.clear()
    assert response.status_code == 422


def test_supply_challenge_requires_auth():
    response = client.post(
        f"/applications/{VALID_APPLICATION_ID}/challenge",
        json={"values": {"otp": "123456"}},
    )
    assert response.status_code == 401


def test_get_application_serializes_pending_challenge():
    override_session()
    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.get_application") as mock_get:
        mock_auth(mock_decode)
        mock_get.return_value = make_mock_application(
            pending_challenge=make_mock_challenge()
        )

        response = client.get(
            f"/applications/{VALID_APPLICATION_ID}", headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "action_required"
    assert body["pending_challenge"]["portal_slug"] == "uct"
    assert body["pending_challenge"]["requested_fields"] == ["otp"]


# --- service logic -------------------------------------------------------------------


def _exec_result(first=None, all_=None):
    result = MagicMock()
    result.first.return_value = first
    result.all.return_value = all_ if all_ is not None else []
    return result


def test_service_supply_challenge_stores_requested_fields_only():
    profile = MagicMock()
    profile.id = VALID_PROFILE_ID
    application = make_mock_application()
    challenge = make_mock_challenge(requested_fields=["temp_id", "password"])

    session = MagicMock()
    session.get.return_value = application
    # exec order: profile lookup, pending challenge, latest job, choices,
    # pending challenge (re-read after supply).
    session.exec.side_effect = [
        _exec_result(first=profile),
        _exec_result(first=challenge),
        _exec_result(first=None),
        _exec_result(all_=[]),
        _exec_result(first=None),
    ]

    result = service.supply_challenge(
        session,
        VALID_USER_ID,
        VALID_APPLICATION_ID,
        {"temp_id": "T123", "password": "s3cret!", "extra": "dropped"},
    )

    assert challenge.supplied_values == {"temp_id": "T123", "password": "s3cret!"}
    assert challenge.supplied_at is not None
    session.commit.assert_called_once()
    assert result is application


def test_service_supply_challenge_missing_fields_422():
    profile = MagicMock()
    profile.id = VALID_PROFILE_ID
    application = make_mock_application()
    challenge = make_mock_challenge(requested_fields=["temp_id", "password"])

    session = MagicMock()
    session.get.return_value = application
    session.exec.side_effect = [
        _exec_result(first=profile),
        _exec_result(first=challenge),
    ]

    try:
        service.supply_challenge(
            session, VALID_USER_ID, VALID_APPLICATION_ID, {"temp_id": "T123"}
        )
        raise AssertionError("expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail["missing_fields"] == ["password"]
    session.commit.assert_not_called()


def test_service_supply_challenge_wrong_owner_404():
    profile = MagicMock()
    profile.id = uuid.uuid4()  # different profile than the application's owner
    application = make_mock_application()

    session = MagicMock()
    session.get.return_value = application
    session.exec.side_effect = [_exec_result(first=profile)]

    try:
        service.supply_challenge(
            session, VALID_USER_ID, VALID_APPLICATION_ID, {"otp": "123456"}
        )
        raise AssertionError("expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 404
