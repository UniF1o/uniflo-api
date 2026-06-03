import uuid
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app

client = TestClient(app)

VALID_USER_ID = "a1b2c3d4-0000-0000-0000-000000000000"
VALID_PROFILE_ID = uuid.uuid4()
VALID_CONTACT_ID = uuid.uuid4()


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


def make_mock_contact(contact_type="next_of_kin"):
    mock = MagicMock()
    mock.id = VALID_CONTACT_ID
    mock.student_id = VALID_PROFILE_ID
    mock.contact_type = contact_type
    mock.title = "Mrs"
    mock.first_name = "Jane"
    mock.last_name = "Doe"
    mock.relationship = "Mother"
    mock.id_number = None
    mock.email = "jane@example.com"
    mock.phone = "0820000000"
    mock.street_address = None
    mock.suburb = None
    mock.city = None
    mock.province = None
    mock.postal_code = None
    mock.updated_at = None
    return mock


VALID_CONTACT_PAYLOAD = {
    "contact_type": "next_of_kin",
    "first_name": "Jane",
    "last_name": "Doe",
    "relationship": "Mother",
    "phone": "0820000000",
    "email": "jane@example.com",
}


# POST /contacts upserts a contact and returns 201
def test_upsert_contact_success():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.contacts.service.upsert_contact"
    ) as mock_upsert:
        mock_auth(mock_decode)
        mock_upsert.return_value = make_mock_contact()
        response = client.post(
            "/contacts", json=VALID_CONTACT_PAYLOAD, headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    assert response.json()["contact_type"] == "next_of_kin"


# POST /contacts rejects an unknown contact_type
def test_upsert_contact_invalid_type():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.post(
            "/contacts",
            json={**VALID_CONTACT_PAYLOAD, "contact_type": "cousin"},
            headers=auth_headers(),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422


# POST /contacts returns 403 when the student has no profile
def test_upsert_contact_no_profile():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.contacts.service.upsert_contact"
    ) as mock_upsert:
        mock_auth(mock_decode)
        mock_upsert.side_effect = HTTPException(
            status_code=403, detail="profile_not_found"
        )
        response = client.post(
            "/contacts", json=VALID_CONTACT_PAYLOAD, headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.json()["detail"] == "profile_not_found"


# GET /contacts lists every contact for the student
def test_list_contacts_success():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.contacts.service.list_contacts"
    ) as mock_list:
        mock_auth(mock_decode)
        mock_list.return_value = [
            make_mock_contact("next_of_kin"),
            make_mock_contact("fee_payer"),
        ]
        response = client.get("/contacts", headers=auth_headers())

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert len(response.json()) == 2


# DELETE /contacts?contact_type=... removes the contact and returns 204
def test_delete_contact_success():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.contacts.service.delete_contact"
    ) as mock_delete:
        mock_auth(mock_decode)
        mock_delete.return_value = None
        response = client.delete(
            "/contacts?contact_type=next_of_kin", headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 204


# DELETE /contacts returns 404 when the contact does not exist
def test_delete_contact_not_found():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.contacts.service.delete_contact"
    ) as mock_delete:
        mock_auth(mock_decode)
        mock_delete.side_effect = HTTPException(
            status_code=404, detail="contact_not_found"
        )
        response = client.delete(
            "/contacts?contact_type=fee_payer", headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 404


# The service create path: profile resolves, no existing contact -> insert
def test_upsert_contact_service_creates_new():
    from app.api.contacts import service as contacts_service
    from app.api.contacts.schemas import ContactType, ContactWrite

    mock_session = MagicMock()
    profile = make_mock_profile()
    # first .first() -> profile lookup; second -> existing-contact lookup (none)
    mock_session.exec.return_value.first.side_effect = [profile, None]

    data = ContactWrite(
        contact_type=ContactType.NEXT_OF_KIN,
        first_name="Jane",
        phone="0820000000",
    )
    contact = contacts_service.upsert_contact(mock_session, VALID_USER_ID, data)

    assert contact.contact_type == "next_of_kin"  # stored as the value, not the enum
    assert contact.first_name == "Jane"
    assert contact.student_id == profile.id
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


# All contact endpoints require a valid token
def test_contacts_require_auth():
    assert client.get("/contacts").status_code == 401
    assert client.post("/contacts", json=VALID_CONTACT_PAYLOAD).status_code == 401
    assert (
        client.delete("/contacts?contact_type=next_of_kin").status_code == 401
    )
