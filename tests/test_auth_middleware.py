from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.api.middleware.auth import ensure_user_synced
from app.db import get_session
from app.main import app

client = TestClient(app)


def test_public_route_health():
    response = client.get("/health")
    assert response.status_code == 200


def test_public_route_docs():
    response = client.get("/docs")
    assert response.status_code == 200


def test_missing_auth_header():
    response = client.get("/profile")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid authorization header"


def test_malformed_auth_header():
    response = client.get("/profile", headers={"Authorization": "notvalid"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid authorization header"


def test_expired_token():
    import jwt

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_decode.side_effect = jwt.ExpiredSignatureError
        response = client.get(
            "/profile", headers={"Authorization": "Bearer expiredtoken"}
        )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_invalid_token():
    import jwt

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_decode.side_effect = jwt.InvalidTokenError
        response = client.get(
            "/profile", headers={"Authorization": "Bearer invalidtoken"}
        )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_valid_token_passes_through():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = None
    app.dependency_overrides[get_session] = lambda: mock_session
    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = {
            "sub": "a1b2c3d4-0000-0000-0000-000000000000",
            "email": "student@gmail.com",
            "role": "student",
        }
        response = client.get(
            "/profile", headers={"Authorization": "Bearer validtoken"}
        )
    assert response.status_code == 404


# ensure_user_synced inserts a users row when missing
def test_ensure_user_synced_creates_when_missing():
    mock_session = MagicMock()
    mock_session.get.return_value = None
    with patch("app.api.middleware.auth.Session") as MockSession, \
         patch("app.api.middleware.auth.get_engine"):
        MockSession.return_value.__enter__.return_value = mock_session
        ensure_user_synced(
            "a1b2c3d4-0000-0000-0000-000000000000", "student@gmail.com"
        )

    assert mock_session.add.called
    assert mock_session.commit.called


# ensure_user_synced updates email when the JWT's email differs
def test_ensure_user_synced_updates_email_drift():
    existing = MagicMock()
    existing.email = "old@gmail.com"
    mock_session = MagicMock()
    mock_session.get.return_value = existing
    with patch("app.api.middleware.auth.Session") as MockSession, \
         patch("app.api.middleware.auth.get_engine"):
        MockSession.return_value.__enter__.return_value = mock_session
        ensure_user_synced(
            "a1b2c3d4-0000-0000-0000-000000000000", "new@gmail.com"
        )

    assert existing.email == "new@gmail.com"
    assert mock_session.commit.called


# ensure_user_synced is a no-op when sub or email is missing from the JWT
def test_ensure_user_synced_skips_when_missing_claims():
    with patch("app.api.middleware.auth.Session") as MockSession, \
         patch("app.api.middleware.auth.get_engine"):
        ensure_user_synced(None, "student@gmail.com")
        ensure_user_synced("a1b2c3d4-0000-0000-0000-000000000000", None)

    assert not MockSession.called
