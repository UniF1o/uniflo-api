from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

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

    with patch("app.api.middleware.auth._jwks_client") as mock_client:
        mock_client.get_signing_key_from_jwt.return_value = MagicMock()
        with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError
            response = client.get(
                "/profile", headers={"Authorization": "Bearer expiredtoken"}
            )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_invalid_token():
    import jwt

    with patch("app.api.middleware.auth._jwks_client") as mock_client:
        mock_client.get_signing_key_from_jwt.return_value = MagicMock()
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
    with patch("app.api.middleware.auth._jwks_client") as mock_client:
        mock_client.get_signing_key_from_jwt.return_value = MagicMock()
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
