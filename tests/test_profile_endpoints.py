from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app

client = TestClient(app)

VALID_USER_ID = "a1b2c3d4-0000-0000-0000-000000000000"

VALID_PROFILE_DATA = {
    "first_name": "John",
    "last_name": "Doe",
    "id_number": "0001015009087",
    "date_of_birth": "2000-01-01",
    "phone": "0821234567",
    "street_address": "1 Main Road",
    "suburb": "Gardens",
    "city": "Cape Town",
    "province": "Western Cape",
    "postal_code": "8001",
    "nationality": "South African",
    "gender": "Male",
    "home_language": "English",
    "religion": "Christianity",
    "disability": "None",
    "marital_status": "Single",
    "ethnicity": "African",
}


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
    mock.id = "b1a6c3d4-0000-0000-0000-000000000000"
    mock.user_id = VALID_USER_ID
    mock.first_name = "John"
    mock.last_name = "Doe"
    mock.id_number = "0001015009087"
    mock.date_of_birth = "2000-01-01"
    mock.phone = "0821234567"
    mock.street_address = "1 Main Road"
    mock.suburb = "Gardens"
    mock.city = "Cape Town"
    mock.province = "Western Cape"
    mock.postal_code = "8001"
    mock.nationality = "South African"
    mock.gender = "Male"
    mock.home_language = "English"
    mock.religion = "Christianity"
    mock.disability = "None"
    mock.marital_status = "Single"
    mock.ethnicity = "African"
    mock.updated_at = None
    return mock


# POST /profile creates a new profile and returns 201
def test_create_profile_success():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = None  # no existing profile
    mock_session.refresh.side_effect = lambda p: None
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.post(
            "/profile", json=VALID_PROFILE_DATA, headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201


# POST /profile called twice by same user upserts and returns 201
def test_create_profile_already_exists():
    mock_session = MagicMock()
    mock_profile = make_mock_profile()
    mock_session.exec.return_value.first.return_value = mock_profile  # profile exists
    mock_session.refresh.side_effect = lambda p: None
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.post(
            "/profile", json=VALID_PROFILE_DATA, headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201


# GET /profile returns profile for authenticated user
def test_get_profile_success():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = make_mock_profile()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.get("/profile", headers=auth_headers())

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["first_name"] == "John"


# GET /profile returns 404 when no profile exists
def test_get_profile_not_found():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = None
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.get("/profile", headers=auth_headers())

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"


# PATCH /profile updates only the fields provided
def test_update_profile_success():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = make_mock_profile()
    mock_session.refresh.side_effect = lambda p: None
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.patch(
            "/profile", json={"phone": "0839876543"}, headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200


# PATCH /profile returns 404 when no profile exists
def test_update_profile_not_found():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = None
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.patch(
            "/profile", json={"phone": "0839876543"}, headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 404


# PATCH /profile returns 422 for invalid postal code
def test_update_profile_invalid_postal_code():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.patch(
            "/profile", json={"postal_code": "12345"}, headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422


# All profile endpoints return 401 without a valid token
def test_profile_endpoints_require_auth():
    response = client.get("/profile")
    assert response.status_code == 401

    response = client.post("/profile", json=VALID_PROFILE_DATA)
    assert response.status_code == 401

    response = client.patch("/profile", json={"phone": "0839876543"})
    assert response.status_code == 401
