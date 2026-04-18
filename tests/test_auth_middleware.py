from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)


# Public route /health should be accessible without any token
def test_public_route_health():
    response = client.get("/health")
    assert response.status_code == 200


# Public route /docs should be accessible without any token
def test_public_route_docs():
    response = client.get("/docs")
    assert response.status_code == 200


# Request with no Authorization header at all should be blocked with 401
def test_missing_auth_header():
    response = client.get("/profile")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid authorization header"


# Request with an Authorization header that doesn't start with "Bearer " should be blocked with 401
def test_malformed_auth_header():
    response = client.get("/profile", headers={"Authorization": "notvalid"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid authorization header"


# Request with a token that has expired should be blocked with 401
# jwt.decode is mocked to raise ExpiredSignatureError — no real token needed
def test_expired_token():
    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        import jwt

        mock_decode.side_effect = jwt.ExpiredSignatureError
        response = client.get(
            "/profile", headers={"Authorization": "Bearer expiredtoken"}
        )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


# Request with a tampered or malformed token should be blocked with 401
# jwt.decode is mocked to raise InvalidTokenError — no real token needed
def test_invalid_token():
    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        import jwt

        mock_decode.side_effect = jwt.InvalidTokenError
        response = client.get(
            "/profile", headers={"Authorization": "Bearer invalidtoken"}
        )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


# Request with a valid token should pass through the middleware
# jwt.decode is mocked to return a valid payload — no real Supabase token needed
# /profile doesn't exist yet so 404 — but 404 confirms middleware let the request through
def test_valid_token_passes_through():
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