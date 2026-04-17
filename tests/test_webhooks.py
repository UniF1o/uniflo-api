from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

VALID_SECRET = "test-webhook-secret"


# Request with wrong webhook secret should be blocked with 401
def test_user_created_wrong_secret():
    response = client.post(
        "/webhooks/user-created",
        headers={"x-webhook-secret": "wrongsecret"},
        json={"record": {"id": "16fd2706-8baf-433b-82eb-8c7fada847da", "email": "student@gmail.com"}}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorised"


# Valid webhook creates a new user in the database
# session is mocked — no real database needed
def test_user_created_success():
    with patch("app.api.webhooks.router.settings") as mock_settings, \
         patch("app.api.webhooks.router.get_session") as mock_get_session:

        mock_settings.WEBHOOK_SECRET = VALID_SECRET

        mock_session = MagicMock()
        mock_session.get.return_value = None  # user doesn't exist yet
        mock_get_session.return_value = iter([mock_session])

        response = client.post(
            "/webhooks/user-created",
            headers={"x-webhook-secret": VALID_SECRET},
            json={"record": {"id": "16fd2706-8baf-433b-82eb-8c7fada847da", "email": "student@gmail.com"}}
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# Webhook fires twice for same user — second call should return early without creating duplicate
def test_user_created_already_exists():
    with patch("app.api.webhooks.router.settings") as mock_settings, \
         patch("app.api.webhooks.router.get_session") as mock_get_session:

        mock_settings.WEBHOOK_SECRET = VALID_SECRET

        mock_session = MagicMock()
        mock_session.get.return_value = MagicMock()  # user already exists
        mock_get_session.return_value = iter([mock_session])

        response = client.post(
            "/webhooks/user-created",
            headers={"x-webhook-secret": VALID_SECRET},
            json={"record": {"id": "16fd2706-8baf-433b-82eb-8c7fada847da", "email": "student@gmail.com"}}
        )

    assert response.status_code == 200
    assert response.json()["status"] == "user already exists"


# Valid webhook deletes existing user from database
def test_user_deleted_success():
    with patch("app.api.webhooks.router.settings") as mock_settings, \
         patch("app.api.webhooks.router.get_session") as mock_get_session:

        mock_settings.DELETE_WEBHOOK_SECRET = VALID_SECRET

        mock_session = MagicMock()
        mock_session.get.return_value = MagicMock()  # user exists
        mock_get_session.return_value = iter([mock_session])

        response = client.post(
            "/webhooks/user-deleted",
            headers={"x-webhook-secret": VALID_SECRET},
            json={"record": {"id": "16fd2706-8baf-433b-82eb-8c7fada847da"}}
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# Delete webhook fires for user that doesn't exist in our table
def test_user_deleted_not_found():
    with patch("app.api.webhooks.router.settings") as mock_settings, \
         patch("app.api.webhooks.router.get_session") as mock_get_session:

        mock_settings.DELETE_WEBHOOK_SECRET = VALID_SECRET

        mock_session = MagicMock()
        mock_session.get.return_value = None  # user doesn't exist
        mock_get_session.return_value = iter([mock_session])

        response = client.post(
            "/webhooks/user-deleted",
            headers={"x-webhook-secret": VALID_SECRET},
            json={"record": {"id": "16fd2706-8baf-433b-82eb-8c7fada847da"}}
        )

    assert response.status_code == 200
    assert response.json()["status"] == "user doesn't exist"