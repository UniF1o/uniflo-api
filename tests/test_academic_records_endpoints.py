import uuid
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app

client = TestClient(app)

VALID_USER_ID = "a1b2c3d4-0000-0000-0000-000000000000"
VALID_PROFILE_ID = uuid.uuid4()
VALID_RECORD_ID = uuid.uuid4()


def auth_headers():
    return {"Authorization": "Bearer validtoken"}


def mock_auth(mock_decode):
    mock_decode.return_value = {
        "sub": VALID_USER_ID,
        "email": "student@gmail.com",
        "role": "student",
    }


def make_mock_profile():
    mock = MagicMock()
    mock.id = VALID_PROFILE_ID
    mock.user_id = uuid.UUID(VALID_USER_ID)
    return mock


def make_mock_record():
    mock = MagicMock()
    mock.id = VALID_RECORD_ID
    mock.student_id = VALID_PROFILE_ID
    mock.institution = "Northview High School"
    mock.year = 2024
    mock.subjects = [
        {"name": "Mathematics", "mark": 78, "custom_name": None},
        {"name": "English Home Language", "mark": 85, "custom_name": None},
        {"name": "Other", "mark": 82, "custom_name": "Dramatic Arts"},
    ]
    mock.aggregate = 81.7
    return mock


VALID_PAYLOAD = {
    "institution": "Northview High School",
    "year": 2024,
    "subjects": [
        {"name": "Mathematics", "mark": 78},
        {"name": "English Home Language", "mark": 85},
        {"name": "Other", "custom_name": "Dramatic Arts", "mark": 82},
    ],
}


# POST /academic-records creates the record and returns 201
def test_create_record_success():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.academic_records.service.upsert_record"
    ) as mock_upsert:
        mock_auth(mock_decode)
        mock_upsert.return_value = make_mock_record()
        response = client.post(
            "/academic-records", json=VALID_PAYLOAD, headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    body = response.json()
    assert body["aggregate"] == 81.7
    assert body["subjects"][2]["custom_name"] == "Dramatic Arts"


# POST upserts -- a second submit still returns 201 (one record per student)
def test_create_record_upsert_returns_201():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.academic_records.service.upsert_record"
    ) as mock_upsert:
        mock_auth(mock_decode)
        mock_upsert.return_value = make_mock_record()
        response = client.post(
            "/academic-records", json=VALID_PAYLOAD, headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201


# POST returns 403 when the student has no profile
def test_create_record_no_profile():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = None  # no profile
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.post(
            "/academic-records", json=VALID_PAYLOAD, headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.json()["detail"] == "profile_not_found"


# Domain validation runs in the service and returns a plain-string detail
def _post_invalid(payload):
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = make_mock_profile()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.post(
            "/academic-records", json=payload, headers=auth_headers()
        )

    app.dependency_overrides.clear()
    return response


def test_reject_other_without_custom_name():
    payload = {**VALID_PAYLOAD, "subjects": [{"name": "Other", "mark": 60}]}
    response = _post_invalid(payload)
    assert response.status_code == 422
    assert "custom_name is required" in response.json()["detail"]


def test_reject_custom_name_on_known_subject():
    payload = {
        **VALID_PAYLOAD,
        "subjects": [{"name": "Mathematics", "mark": 70, "custom_name": "x"}],
    }
    response = _post_invalid(payload)
    assert response.status_code == 422
    assert "only allowed when subject name is 'Other'" in response.json()["detail"]


def test_reject_duplicate_subject():
    payload = {
        **VALID_PAYLOAD,
        "subjects": [
            {"name": "Mathematics", "mark": 70},
            {"name": "Mathematics", "mark": 80},
        ],
    }
    response = _post_invalid(payload)
    assert response.status_code == 422
    assert "Duplicate subject" in response.json()["detail"]


def test_reject_mark_out_of_range():
    payload = {**VALID_PAYLOAD, "subjects": [{"name": "Mathematics", "mark": 150}]}
    response = _post_invalid(payload)
    assert response.status_code == 422
    assert "between 0 and 100" in response.json()["detail"]


def test_reject_year_out_of_range():
    response = _post_invalid({**VALID_PAYLOAD, "year": 1999})
    assert response.status_code == 422
    assert "Year must be between" in response.json()["detail"]


def test_reject_empty_institution():
    response = _post_invalid({**VALID_PAYLOAD, "institution": "   "})
    assert response.status_code == 422
    assert "Institution is required" in response.json()["detail"]


def test_reject_no_subjects():
    response = _post_invalid({**VALID_PAYLOAD, "subjects": []})
    assert response.status_code == 422
    assert "At least one subject" in response.json()["detail"]


# GET returns the record when it exists
def test_get_record_success():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.academic_records.service.get_record"
    ) as mock_get:
        mock_auth(mock_decode)
        mock_get.return_value = make_mock_record()
        response = client.get("/academic-records", headers=auth_headers())

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["institution"] == "Northview High School"


# GET returns 200 + null when there is no record (or no profile) yet
def test_get_record_none_returns_null():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.academic_records.service.get_record"
    ) as mock_get:
        mock_auth(mock_decode)
        mock_get.return_value = None
        response = client.get("/academic-records", headers=auth_headers())

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() is None


# PATCH updates the record and returns 200
def test_patch_record_success():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.academic_records.service.patch_record"
    ) as mock_patch:
        mock_auth(mock_decode)
        mock_patch.return_value = make_mock_record()
        response = client.patch(
            "/academic-records",
            json={"institution": "Southview College"},
            headers=auth_headers(),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200


# PATCH returns 404 when the student has no academic record yet
def test_patch_record_not_found():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.academic_records.service.patch_record"
    ) as mock_patch:
        mock_auth(mock_decode)
        mock_patch.side_effect = HTTPException(
            status_code=404, detail="academic_record_not_found"
        )
        response = client.patch(
            "/academic-records", json={"year": 2025}, headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json()["detail"] == "academic_record_not_found"


# All academic-records endpoints require a valid token
def test_academic_records_require_auth():
    assert client.get("/academic-records").status_code == 401
    assert client.post("/academic-records", json=VALID_PAYLOAD).status_code == 401
    assert client.patch("/academic-records", json={"year": 2025}).status_code == 401
