from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app
from app.db import get_session

client = TestClient(app)

VALID_USER_ID = "a1b2c3d4-0000-0000-0000-000000000000"

VALID_PROFILE_DATA = {
    "first_name": "John",
    "last_name": "Doe",
    "id_number": "0001015009087",
    "date_of_birth": "2000-01-01",
    "phone": "0821234567",
    "address": "1 Main Road, Cape Town",
    "nationality": "South African",
    "gender": "Male",
    "home_language": "English"
}


def auth_headers():
    return {"Authorization": "Bearer validtoken"}


def mock_auth(mock_decode):
    mock_decode.return_value = {
        "sub": VALID_USER_ID,
        "email": "student@gmail.com",
        "role": "student"
    }


# POST /profile creates a new profile and returns 201
def test_create_profile_success():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = None  # no existing profile
    mock_profile = MagicMock()
    mock_profile.id = "b1a6c3d4-0000-0000-0000-000000000000"
    mock_profile.user_id = VALID_USER_ID
    mock_profile.first_name = "John"
    mock_profile.last_name = "Doe"
    mock_profile.id_number = "0001015009087"
    mock_profile.date_of_birth = "2000-01-01"
    mock_profile.phone = "0821234567"
    mock_profile.address = "1 Main Road, Cape Town"
    mock_profile.nationality = "South African"
    mock_profile.gender = "Male"
    mock_profile.home_language = "English"
    mock_profile.updated_at = None
    mock_session.refresh.side_effect = lambda p: None
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.post(
            "/profile",
            json=VALID_PROFILE_DATA,
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201


# POST /profile called twice by same user returns 409
def test_create_profile_already_exists():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = MagicMock()  # profile exists
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.post(
            "/profile",
            json=VALID_PROFILE_DATA,
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 409
    assert response.json()["detail"] == "Profile already exists"


# GET /profile returns profile for authenticated user
def test_get_profile_success():
    mock_session = MagicMock()
    mock_profile = MagicMock()
    mock_profile.id = "b1a6c3d4-0000-0000-0000-000000000000"
    mock_profile.user_id = VALID_USER_ID
    mock_profile.first_name = "John"
    mock_profile.last_name = "Doe"
    mock_profile.id_number = "0001015009087"
    mock_profile.date_of_birth = "2000-01-01"
    mock_profile.phone = "0821234567"
    mock_profile.address = "1 Main Road, Cape Town"
    mock_profile.nationality = "South African"
    mock_profile.gender = "Male"
    mock_profile.home_language = "English"
    mock_profile.updated_at = None
    mock_session.exec.return_value.first.return_value = mock_profile
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
    mock_profile = MagicMock()
    mock_profile.id = "b1a6c3d4-0000-0000-0000-000000000000"
    mock_profile.user_id = VALID_USER_ID
    mock_profile.first_name = "John"
    mock_profile.last_name = "Doe"
    mock_profile.id_number = "0001015009087"
    mock_profile.date_of_birth = "2000-01-01"
    mock_profile.phone = "0821234567"
    mock_profile.address = "1 Main Road, Cape Town"
    mock_profile.nationality = "South African"
    mock_profile.gender = "Male"
    mock_profile.home_language = "English"
    mock_profile.updated_at = None
    mock_session.exec.return_value.first.return_value = mock_profile
    mock_session.refresh.side_effect = lambda p: None
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.patch(
            "/profile",
            json={"phone": "0839876543"},
            headers=auth_headers()
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
            "/profile",
            json={"phone": "0839876543"},
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 404


# All profile endpoints return 401 without a valid token
def test_profile_endpoints_require_auth():
    response = client.get("/profile")
    assert response.status_code == 401

    response = client.post("/profile", json=VALID_PROFILE_DATA)
    assert response.status_code == 401

    response = client.patch("/profile", json={"phone": "0839876543"})
    assert response.status_code == 401