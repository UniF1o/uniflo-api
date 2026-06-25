import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app

client = TestClient(app)

ADMIN_ID = "b2c3d4e5-0000-0000-0000-000000000000"
STUDENT_ID = "a1b2c3d4-0000-0000-0000-000000000000"
ADMIN_JWT = {"sub": ADMIN_ID, "email": "admin@uniflo.co.za"}
STUDENT_JWT = {"sub": STUDENT_ID, "email": "student@gmail.com"}


def _admin_user():
    user = MagicMock()
    user.id = uuid.UUID(ADMIN_ID)
    user.email = "admin@uniflo.co.za"
    user.role = "admin"
    return user


def _student_user():
    user = MagicMock()
    user.id = uuid.UUID(STUDENT_ID)
    user.email = "student@gmail.com"
    user.role = "student"
    return user


# ---------------------------------------------------------------------------
# GET /admin/stats
# ---------------------------------------------------------------------------


def test_admin_stats_returns_200_for_admin():
    mock_session = MagicMock()
    mock_session.get.return_value = _admin_user()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.admin.service.get_stats"
    ) as mock_fn:
        mock_decode.return_value = ADMIN_JWT
        mock_fn.return_value = MagicMock(
            total_students=3,
            active_universities=4,
            applications_by_status=[],
            model_dump=lambda: {
                "total_students": 3,
                "active_universities": 4,
                "applications_by_status": [],
            },
        )
        response = client.get(
            "/admin/stats", headers={"Authorization": "Bearer validtoken"}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200


def test_admin_stats_returns_403_for_student():
    mock_session = MagicMock()
    mock_session.get.return_value = _student_user()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = STUDENT_JWT
        response = client.get(
            "/admin/stats", headers={"Authorization": "Bearer validtoken"}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_stats_returns_401_without_token():
    response = client.get("/admin/stats")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /admin/students
# ---------------------------------------------------------------------------


def test_admin_students_returns_403_for_student():
    mock_session = MagicMock()
    mock_session.get.return_value = _student_user()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = STUDENT_JWT
        response = client.get(
            "/admin/students", headers={"Authorization": "Bearer validtoken"}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403


def test_admin_students_returns_200_for_admin():
    mock_session = MagicMock()
    mock_session.get.return_value = _admin_user()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.admin.service.list_students"
    ) as mock_fn:
        mock_decode.return_value = ADMIN_JWT
        mock_fn.return_value = MagicMock(
            items=[], total=0, page=1, per_page=50,
        )
        response = client.get(
            "/admin/students", headers={"Authorization": "Bearer validtoken"}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /admin/applications
# ---------------------------------------------------------------------------


def test_admin_applications_returns_403_for_student():
    mock_session = MagicMock()
    mock_session.get.return_value = _student_user()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = STUDENT_JWT
        response = client.get(
            "/admin/applications", headers={"Authorization": "Bearer validtoken"}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /admin/universities
# ---------------------------------------------------------------------------


def test_admin_universities_returns_403_for_student():
    mock_session = MagicMock()
    mock_session.get.return_value = _student_user()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = STUDENT_JWT
        response = client.get(
            "/admin/universities", headers={"Authorization": "Bearer validtoken"}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403


def test_admin_universities_returns_200_for_admin():
    mock_session = MagicMock()
    mock_session.get.return_value = _admin_user()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.universities.service.list_universities"
    ) as mock_fn:
        mock_decode.return_value = ADMIN_JWT
        mock_fn.return_value = []
        response = client.get(
            "/admin/universities", headers={"Authorization": "Bearer validtoken"}
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {"items": []}


# ---------------------------------------------------------------------------
# POST /admin/universities
# ---------------------------------------------------------------------------


def test_admin_universities_create_returns_403_for_student():
    mock_session = MagicMock()
    mock_session.get.return_value = _student_user()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = STUDENT_JWT
        response = client.post(
            "/admin/universities",
            json={"name": "Test U", "website": "https://test.ac.za", "portal_url": "https://portal.test.ac.za"},
            headers={"Authorization": "Bearer validtoken"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /admin/universities/{id}
# ---------------------------------------------------------------------------


def test_admin_universities_update_returns_404_for_unknown_id():
    mock_session = MagicMock()
    mock_session.get.side_effect = [_admin_user(), None]  # admin check, then university lookup
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = ADMIN_JWT
        response = client.patch(
            f"/admin/universities/{uuid.uuid4()}",
            json={"is_active": True},
            headers={"Authorization": "Bearer validtoken"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 404
