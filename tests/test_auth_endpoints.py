from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app

client = TestClient(app)


def get_auth_headers():
    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = {
            "sub": "a1b2c3d4-0000-0000-0000-000000000000",
            "email": "student@gmail.com",
            "role": "student"
        }
        return {"Authorization": "Bearer validtoken"}


# GET /auth/me returns user when they exist in the database
def test_get_me_existing_user():
    mock_session = MagicMock()
    mock_user = MagicMock()
    mock_user.id = "a1b2c3d4-0000-0000-0000-000000000000"
    mock_user.email = "student@gmail.com"
    mock_user.role = "student"
    mock_session.get.return_value = mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = {
            "sub": "a1b2c3d4-0000-0000-0000-000000000000",
            "email": "student@gmail.com",
            "role": "student"
        }
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer validtoken"}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["email"] == "student@gmail.com"
    assert response.json()["role"] == "student"


# GET /auth/me self-heals — creates user row if webhook missed it on sign-up
def test_get_me_self_heal():
    mock_session = MagicMock()
    mock_session.get.return_value = None  # user doesn't exist in DB yet
    mock_user = MagicMock()
    mock_user.id = "a1b2c3d4-0000-0000-0000-000000000000"
    mock_user.email = "student@gmail.com"
    mock_user.role = "student"
    mock_session.refresh.side_effect = lambda u: None
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = {
            "sub": "a1b2c3d4-0000-0000-0000-000000000000",
            "email": "student@gmail.com",
            "role": "student"
        }
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer validtoken"}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert mock_session.add.called
    assert mock_session.commit.called


# GET /auth/me returns 401 with no token
def test_get_me_no_token():
    response = client.get("/auth/me")
    assert response.status_code == 401