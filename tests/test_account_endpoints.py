from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app

client = TestClient(app)

VALID_USER_ID = "a1b2c3d4-0000-0000-0000-000000000000"


def auth_headers():
    return {"Authorization": "Bearer validtoken"}


def mock_auth(mock_decode):
    mock_decode.return_value = {
        "sub": VALID_USER_ID,
        "email": "student@gmail.com",
        "role": "student",
    }


# DELETE /account deletes the account and returns 200 {}
def test_delete_account_success():
    from unittest.mock import MagicMock
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.account.service.delete_account") as mock_delete:
        mock_auth(mock_decode)
        mock_delete.return_value = None
        response = client.delete("/account", headers=auth_headers())

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {}


# DELETE /account returns 404 when the user does not exist
def test_delete_account_not_found():
    from unittest.mock import MagicMock
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.account.service.delete_account") as mock_delete:
        mock_auth(mock_decode)
        mock_delete.side_effect = HTTPException(status_code=404, detail="user_not_found")
        response = client.delete("/account", headers=auth_headers())

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json()["detail"] == "user_not_found"


# DELETE /account returns 500 when the Supabase admin call fails
def test_delete_account_supabase_failure():
    from unittest.mock import MagicMock
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.account.service.delete_account") as mock_delete:
        mock_auth(mock_decode)
        mock_delete.side_effect = HTTPException(
            status_code=500, detail="account_deletion_auth_failed"
        )
        response = client.delete("/account", headers=auth_headers())

    app.dependency_overrides.clear()
    assert response.status_code == 500
    assert response.json()["detail"] == "account_deletion_auth_failed"


# DELETE /account returns 401 without a valid token
def test_delete_account_no_auth():
    response = client.delete("/account")
    assert response.status_code == 401
