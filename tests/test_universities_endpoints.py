import uuid
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app

client = TestClient(app)

VALID_UNIVERSITY_ID = uuid.uuid4()


def make_mock_university(name="University of Cape Town", is_active=True):
    mock_uni = MagicMock()
    mock_uni.id = VALID_UNIVERSITY_ID
    mock_uni.name = name
    mock_uni.website = "https://www.uct.ac.za"
    mock_uni.portal_url = "https://apply.uct.ac.za"
    mock_uni.open_date = "2026-04-01"
    mock_uni.close_date = "2026-09-30"
    mock_uni.is_active = is_active
    return mock_uni


# GET /universities returns list of universities in alphabetical order
def test_list_universities_success():
    mock_session = MagicMock()
    mock_session.exec.return_value.all.return_value = [
        make_mock_university("University of Cape Town"),
        make_mock_university("University of Johannesburg"),
        make_mock_university("University of the Witwatersrand"),
    ]
    app.dependency_overrides[get_session] = lambda: mock_session

    response = client.get("/universities")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert "items" in response.json()
    assert len(response.json()["items"]) == 3


# GET /universities?q=cape returns filtered results
def test_list_universities_search_filter():
    mock_session = MagicMock()
    mock_session.exec.return_value.all.return_value = [
        make_mock_university("University of Cape Town"),
    ]
    app.dependency_overrides[get_session] = lambda: mock_session

    response = client.get("/universities?q=cape")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["name"] == "University of Cape Town"


# GET /universities?q=nomatch returns empty items list not 404
def test_list_universities_no_results():
    mock_session = MagicMock()
    mock_session.exec.return_value.all.return_value = []
    app.dependency_overrides[get_session] = lambda: mock_session

    response = client.get("/universities?q=nomatch")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {"items": []}


# GET /universities?is_active=false returns inactive universities only
def test_list_universities_inactive_filter():
    mock_session = MagicMock()
    mock_session.exec.return_value.all.return_value = [
        make_mock_university("University of Cape Town", is_active=False),
    ]
    app.dependency_overrides[get_session] = lambda: mock_session

    response = client.get("/universities?is_active=false")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["items"][0]["is_active"] is False


# GET /universities/{id} returns university when it exists
def test_get_university_success():
    mock_session = MagicMock()
    mock_session.get.return_value = make_mock_university()
    app.dependency_overrides[get_session] = lambda: mock_session

    response = client.get(f"/universities/{VALID_UNIVERSITY_ID}")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["name"] == "University of Cape Town"


# GET /universities/{id} returns 404 when university does not exist
def test_get_university_not_found():
    mock_session = MagicMock()
    mock_session.get.return_value = None
    app.dependency_overrides[get_session] = lambda: mock_session

    response = client.get(f"/universities/{uuid.uuid4()}")

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json()["detail"] == "university_not_found"


# GET /universities/{id} returns 422 when id is not a valid UUID
def test_get_university_invalid_uuid():
    response = client.get("/universities/not-a-uuid")
    assert response.status_code == 422


# GET /universities is public — no token required
def test_universities_are_public():
    mock_session = MagicMock()
    mock_session.exec.return_value.all.return_value = []
    app.dependency_overrides[get_session] = lambda: mock_session

    response = client.get("/universities")

    app.dependency_overrides.clear()
    assert response.status_code == 200