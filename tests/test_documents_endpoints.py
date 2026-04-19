import uuid
from io import BytesIO
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app
from app.db import get_session

client = TestClient(app)

VALID_USER_ID = "a1b2c3d4-0000-0000-0000-000000000000"
VALID_PROFILE_ID = uuid.uuid4()
VALID_DOCUMENT_ID = uuid.uuid4()


def auth_headers():
    return {"Authorization": "Bearer validtoken"}


def mock_auth(mock_decode):
    mock_decode.return_value = {
        "sub": VALID_USER_ID,
        "email": "student@gmail.com",
        "role": "student"
    }


def make_mock_profile():
    mock_profile = MagicMock()
    mock_profile.id = VALID_PROFILE_ID
    mock_profile.user_id = uuid.UUID(VALID_USER_ID)
    return mock_profile


def make_mock_document():
    mock_document = MagicMock()
    mock_document.id = VALID_DOCUMENT_ID
    mock_document.student_id = VALID_PROFILE_ID
    mock_document.type = "ID_COPY"
    mock_document.storage_url = "https://supabase.co/storage/v1/object/public/documents/id.pdf"
    mock_document.uploaded_at = "2026-04-19T00:00:00"
    return mock_document


# POST /documents/upload with valid PDF returns 201
def test_upload_document_success():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = make_mock_profile()
    mock_session.refresh.side_effect = lambda d: None
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.documents.service.get_supabase") as mock_get_supabase:

        mock_auth(mock_decode)
        mock_get_supabase.storage.from_.return_value.upload.return_value = {}
        mock_get_supabase.storage.from_.return_value.get_public_url.return_value = (
            "https://supabase.co/storage/v1/object/public/documents/id.pdf"
        )

        response = client.post(
            "/documents/upload",
            headers=auth_headers(),
            data={"document_type": "ID_COPY"},
            files={"file": ("id.pdf", BytesIO(b"fake pdf content"), "application/pdf")}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201


# POST /documents/upload with invalid file type returns 422
def test_upload_document_invalid_type():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = make_mock_profile()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.post(
            "/documents/upload",
            headers=auth_headers(),
            data={"document_type": "ID_COPY"},
            files={"file": ("id.gif", BytesIO(b"fake gif content"), "image/gif")}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422


# POST /documents/upload returns 404 if student has no profile
def test_upload_document_no_profile():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = None  # no profile
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.post(
            "/documents/upload",
            headers=auth_headers(),
            data={"document_type": "ID_COPY"},
            files={"file": ("id.pdf", BytesIO(b"fake pdf content"), "application/pdf")}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 404


# GET /documents returns all documents for authenticated student
def test_get_documents_success():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = make_mock_profile()
    mock_session.exec.return_value.all.return_value = [make_mock_document()]
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.get("/documents", headers=auth_headers())

    app.dependency_overrides.clear()
    assert response.status_code == 200


# GET /documents returns empty list when no documents exist
def test_get_documents_empty():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = make_mock_profile()
    mock_session.exec.return_value.all.return_value = []
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.get("/documents", headers=auth_headers())

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == []


# DELETE /documents/{id} deletes document and returns 200
def test_delete_document_success():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = make_mock_profile()
    mock_session.get.return_value = make_mock_document()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
         patch("app.api.documents.service.get_supabase") as mock_get_supabase:

        mock_auth(mock_decode)
        mock_get_supabase.storage.from_.return_value.remove.return_value = {}

        response = client.delete(
            f"/documents/{VALID_DOCUMENT_ID}",
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# DELETE /documents/{id} returns 404 for non-existent document
def test_delete_document_not_found():
    mock_session = MagicMock()
    mock_session.exec.return_value.first.return_value = make_mock_profile()
    mock_session.get.return_value = None  # document doesn't exist
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.delete(
            f"/documents/{VALID_DOCUMENT_ID}",
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 404


# DELETE /documents/{id} returns 403 when document belongs to different student
def test_delete_document_wrong_owner():
    mock_session = MagicMock()
    mock_profile = make_mock_profile()
    mock_document = make_mock_document()
    mock_document.student_id = uuid.uuid4()  # different student's profile id
    mock_session.exec.return_value.first.return_value = mock_profile
    mock_session.get.return_value = mock_document
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_auth(mock_decode)
        response = client.delete(
            f"/documents/{VALID_DOCUMENT_ID}",
            headers=auth_headers()
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403


# All document endpoints return 401 without a valid token
def test_documents_endpoints_require_auth():
    response = client.get("/documents")
    assert response.status_code == 401

    response = client.post(
        "/documents/upload",
        data={"document_type": "ID_COPY"},
        files={"file": ("id.pdf", BytesIO(b"content"), "application/pdf")}
    )
    assert response.status_code == 401

    response = client.delete(f"/documents/{VALID_DOCUMENT_ID}")
    assert response.status_code == 401