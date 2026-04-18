from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.db import get_session

client = TestClient(app)

VALID_SECRET = "test-webhook-secret"


def mock_session_override():
    mock_session = MagicMock()
    yield mock_session


# Request with wrong webhook secret should be blocked with 401
def test_user_created_wrong_secret():
    app.dependency_overrides[get_session] = mock_session_override
    with patch("app.api.webhooks.router.settings") as mock_settings:
        mock_settings.WEBHOOK_SECRET = VALID_SECRET
        response = client.post(
            "/webhooks/user-created",
            headers={"x-webhook-secret": "wrongsecret"},
            json={"record": {"id": "a1b2c3d4-0000-0000-0000-000000000000", "email": "student@gmail.com"}}
        )
    app.dependency_overrides.clear()
    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorised"


# Valid webhook creates a new user in the database
def test_user_created_success():
    mock_session = MagicMock()
    mock_session.get.return_value = None  # user doesn't exist yet
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.webhooks.router.settings") as mock_settings:
        mock_settings.WEBHOOK_SECRET = VALID_SECRET
        response = client.post(
            "/webhooks/user-created",
            headers={"x-webhook-secret": VALID_SECRET},
            json={"record": {"id": "a1b2c3d4-0000-0000-0000-000000000000", "email": "student@gmail.com"}}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# Webhook fires twice for same user — should return early without creating duplicate
def test_user_created_already_exists():
    mock_session = MagicMock()
    mock_session.get.return_value = MagicMock()  # user already exists
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.webhooks.router.settings") as mock_settings:
        mock_settings.WEBHOOK_SECRET = VALID_SECRET
        response = client.post(
            "/webhooks/user-created",
            headers={"x-webhook-secret": VALID_SECRET},
            json={"record": {"id": "a1b2c3d4-0000-0000-0000-000000000000", "email": "student@gmail.com"}}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "user already exists"


# Valid webhook deletes existing user from database
def test_user_deleted_success():
    mock_session = MagicMock()
    mock_session.get.return_value = MagicMock()  # user exists
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.webhooks.router.settings") as mock_settings:
        mock_settings.DELETE_WEBHOOK_SECRET = VALID_SECRET
        response = client.post(
            "/webhooks/user-deleted",
            headers={"x-webhook-secret": VALID_SECRET},
            json={"record": {"id": "a1b2c3d4-0000-0000-0000-000000000000"}}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# Delete webhook fires for user that doesn't exist in our table
def test_user_deleted_not_found():
    mock_session = MagicMock()
    mock_session.get.return_value = None  # user doesn't exist
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.webhooks.router.settings") as mock_settings:
        mock_settings.DELETE_WEBHOOK_SECRET = VALID_SECRET
        response = client.post(
            "/webhooks/user-deleted",
            headers={"x-webhook-secret": VALID_SECRET},
            json={"record": {"id": "a1b2c3d4-0000-0000-0000-000000000000"}}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "user doesn't exist"