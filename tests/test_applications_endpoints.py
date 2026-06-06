import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app

client = TestClient(app)

VALID_USER_ID = "a1b2c3d4-0000-0000-0000-000000000000"
VALID_UNIVERSITY_ID = uuid.uuid4()
VALID_APPLICATION_ID = uuid.uuid4()
VALID_PROFILE_ID = uuid.uuid4()


def auth_headers():
    return {"Authorization": "Bearer validtoken"}


def mock_auth(mock_decode):
    mock_decode.return_value = {
        "sub": VALID_USER_ID,
        "email": "student@gmail.com",
        "role": "student"
    }


def make_mock_profile():
    mock = MagicMock()
    mock.id = VALID_PROFILE_ID
    mock.user_id = uuid.UUID(VALID_USER_ID)
    return mock


def make_mock_university(is_active=True, close_date=None):
    from datetime import date
    mock = MagicMock()
    mock.id = VALID_UNIVERSITY_ID
    mock.name = "University of Cape Town"
    mock.is_active = is_active
    mock.close_date = close_date or date(2027, 9, 30)
    return mock


def make_mock_job():
    mock = MagicMock()
    mock.id = uuid.uuid4()
    mock.application_id = VALID_APPLICATION_ID
    mock.status = "pending"
    mock.attempts = 0
    mock.last_error = None
    mock.screenshot_url = None
    mock.updated_at = None
    mock.created_at = datetime.now(timezone.utc)
    return mock


def make_mock_application():
    mock = MagicMock()
    mock.id = VALID_APPLICATION_ID
    mock.student_id = VALID_PROFILE_ID
    mock.university_id = VALID_UNIVERSITY_ID
    mock.programme = "BSc Computer Science"
    mock.application_year = 2027
    mock.status = "pending"
    mock.submitted_at = None
    mock.updated_at = None
    mock.created_at = datetime.now(timezone.utc)
    mock.latest_job = make_mock_job()
    mock.choices = [
        _make_choice(1, "BSc Computer Science"),
        _make_choice(2, "BEng Electrical"),
    ]
    return mock


def _make_choice(choice_number, programme, eligible=None):
    mock = MagicMock()
    mock.choice_number = choice_number
    mock.programme = programme
    mock.eligible = eligible
    return mock


VALID_PAYLOAD = {
    "university_id": str(VALID_UNIVERSITY_ID),
    "programme": "BSc Computer Science",
    "application_year": 2027
}


# POST /applications creates application and job, returns 201
def test_create_application_success():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = make_mock_profile()
    mock_session.get.side_effect = lambda model, id: (
        make_mock_university() if model.__name__ == "University" else None
    )
    mock_session.flush.return_value = None
    mock_session.refresh.return_value = None
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.create_application") as mock_create:
        mock_auth(mock_decode)
        mock_create.return_value = make_mock_application()
        response = client.post(
            "/applications",
            json=VALID_PAYLOAD,
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201


# POST /applications returns 403 when student has no profile
def test_create_application_no_profile():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.create_application") as mock_create:
        mock_auth(mock_decode)
        from fastapi import HTTPException
        mock_create.side_effect = HTTPException(
            status_code=403, detail="profile_not_found"
        )
        response = client.post(
            "/applications",
            json=VALID_PAYLOAD,
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.json()["detail"] == "profile_not_found"


# POST /applications returns 422 when student profile is incomplete
def test_create_application_incomplete_profile():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.create_application") as mock_create:
        mock_auth(mock_decode)
        from fastapi import HTTPException
        mock_create.side_effect = HTTPException(
            status_code=422,
            detail={"code": "profile_incomplete", "missing_fields": ["phone", "address"]},
        )
        response = client.post(
            "/applications",
            json=VALID_PAYLOAD,
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "profile_incomplete"


# POST /applications returns 400 when university is inactive
def test_create_application_inactive_university():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.create_application") as mock_create:
        mock_auth(mock_decode)
        from fastapi import HTTPException
        mock_create.side_effect = HTTPException(
            status_code=400, detail="university_inactive"
        )
        response = client.post(
            "/applications",
            json=VALID_PAYLOAD,
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["detail"] == "university_inactive"


# POST /applications returns 400 when application deadline has passed
def test_create_application_closed():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.create_application") as mock_create:
        mock_auth(mock_decode)
        from fastapi import HTTPException
        mock_create.side_effect = HTTPException(
            status_code=400,
            detail={"code": "applications_closed", "close_date": "2026-09-30"}
        )
        response = client.post(
            "/applications",
            json=VALID_PAYLOAD,
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 400


# POST /applications returns 422 when application_year is invalid
def test_create_application_invalid_year():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.post(
            "/applications",
            json={**VALID_PAYLOAD, "application_year": 2025},
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422


# POST /applications returns 422 when programme is too short
def test_create_application_programme_too_short():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.post(
            "/applications",
            json={**VALID_PAYLOAD, "programme": "AB"},
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422


# POST /applications accepts additional_programmes and returns ordered choices
def test_create_application_with_additional_programmes():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.create_application") as mock_create:
        mock_auth(mock_decode)
        mock_create.return_value = make_mock_application()
        response = client.post(
            "/applications",
            json={**VALID_PAYLOAD, "additional_programmes": ["BEng Electrical"]},
            headers=auth_headers(),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    choices = response.json()["choices"]
    assert [c["choice_number"] for c in choices] == [1, 2]
    assert choices[0]["programme"] == "BSc Computer Science"


# POST /applications rejects more than the allowed number of extra choices
def test_create_application_too_many_choices():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.post(
            "/applications",
            json={
                **VALID_PAYLOAD,
                "additional_programmes": ["Prog Two", "Prog Three", "Prog Four"],
            },
            headers=auth_headers(),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422


# GET /applications returns all applications for authenticated student
def test_list_applications_success():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.list_applications") as mock_list:
        mock_auth(mock_decode)
        mock_list.return_value = [make_mock_application(), make_mock_application()]
        response = client.get("/applications", headers=auth_headers())

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert len(response.json()) == 2


# GET /applications/{id} returns application when owned by student
def test_get_application_success():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.get_application") as mock_get:
        mock_auth(mock_decode)
        mock_get.return_value = make_mock_application()
        response = client.get(
            f"/applications/{VALID_APPLICATION_ID}",
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200


# GET /applications/{id} returns 404 when not found or not owned
def test_get_application_not_found():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.get_application") as mock_get:
        mock_auth(mock_decode)
        from fastapi import HTTPException
        mock_get.side_effect = HTTPException(
            status_code=404, detail="application_not_found"
        )
        response = client.get(
            f"/applications/{uuid.uuid4()}",
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json()["detail"] == "application_not_found"


# GET /applications/{id}/field-mappings returns the review-screen mapping
def test_field_mappings_endpoint_success():
    from app.api.applications.schemas import FieldMappingEntryRead, FieldMappingRead

    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    mapping = FieldMappingRead(
        application_id=VALID_APPLICATION_ID,
        university_id=VALID_UNIVERSITY_ID,
        overall_confidence=0.8,
        confidence_threshold=0.85,
        entries=[
            FieldMappingEntryRead(field_id="surname", value="Doe", confidence=0.95, flagged=False),
            FieldMappingEntryRead(field_id="programme", value="Civil", confidence=0.6, flagged=True),
        ],
        created_at=datetime.now(timezone.utc),
    )
    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.get_field_mapping") as mock_get:
        mock_auth(mock_decode)
        mock_get.return_value = mapping
        response = client.get(
            f"/applications/{VALID_APPLICATION_ID}/field-mappings",
            headers=auth_headers(),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    flagged = {e["field_id"]: e["flagged"] for e in body["entries"]}
    assert flagged == {"surname": False, "programme": True}


# POST /applications/{id}/consent records acceptance and returns the application
def test_consent_endpoint_success():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.record_consent") as mock_consent:
        mock_auth(mock_decode)
        mock_consent.return_value = make_mock_application()
        response = client.post(
            f"/applications/{VALID_APPLICATION_ID}/consent",
            json={"popi": True, "agreement": True},
            headers=auth_headers(),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200


def test_record_consent_service_sets_timestamps():
    from app.api.applications import service

    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = make_mock_profile()
    mock_session.exec.return_value.all.return_value = []
    appn = make_mock_application()
    appn.popi_consent_at = None
    appn.agreement_consent_at = None
    mock_session.get.return_value = appn

    service.record_consent(
        mock_session, VALID_USER_ID, VALID_APPLICATION_ID, popi=True, agreement=True
    )
    assert appn.popi_consent_at is not None
    assert appn.agreement_consent_at is not None
    mock_session.commit.assert_called_once()


def test_record_consent_requires_a_flag():
    import pytest
    from fastapi import HTTPException

    from app.api.applications import service
    with pytest.raises(HTTPException) as exc:
        service.record_consent(
            MagicMock(), VALID_USER_ID, VALID_APPLICATION_ID,
            popi=False, agreement=False,
        )
    assert exc.value.status_code == 422


# POST /applications/{id}/retry re-enqueues automation and returns the application
def test_retry_application_success():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.applications.service.retry_application") as mock_retry, \
         patch("app.api.applications.router.process_application") as mock_proc:
        mock_auth(mock_decode)
        mock_retry.return_value = make_mock_application()
        response = client.post(
            f"/applications/{VALID_APPLICATION_ID}/retry",
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    mock_proc.assert_called_once()  # automation re-enqueued


def test_retry_application_blocks_submitted():
    from fastapi import HTTPException

    from app.api.applications import service

    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = make_mock_profile()
    appn = make_mock_application()
    appn.status = "submitted"
    mock_session.get.return_value = appn

    import pytest
    with pytest.raises(HTTPException) as exc:
        service.retry_application(mock_session, VALID_USER_ID, VALID_APPLICATION_ID)
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "already_submitted"


def test_retry_application_blocks_in_progress():
    from fastapi import HTTPException

    from app.api.applications import service

    mock_session = MagicMock()
    job = make_mock_job()
    job.status = "processing"
    # get_student_profile, then get_latest_job
    mock_session.exec.return_value.first.side_effect = [make_mock_profile(), job]
    appn = make_mock_application()
    appn.status = "processing"
    mock_session.get.return_value = appn

    import pytest
    with pytest.raises(HTTPException) as exc:
        service.retry_application(mock_session, VALID_USER_ID, VALID_APPLICATION_ID)
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "already_in_progress"


# All application endpoints return 401 without a valid token
def test_applications_require_auth():
    response = client.get("/applications")
    assert response.status_code == 401

    response = client.post("/applications", json=VALID_PAYLOAD)
    assert response.status_code == 401

    response = client.get(f"/applications/{VALID_APPLICATION_ID}")
    assert response.status_code == 401