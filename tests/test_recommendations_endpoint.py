"""Tests for GET /recommendations and GET /universities/{id}/programmes.

Uses TestClient + mocked service following the conftest.py pattern
(autouse fixtures patch _jwks_client and ensure_user_synced).
No real DB is touched.
"""
import uuid
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app

client = TestClient(app)

USER_ID = "a1b2c3d4-0000-0000-0000-000000000001"
UNIVERSITY_ID = str(uuid.uuid4())
PROGRAMME_ID_1 = str(uuid.uuid4())
PROGRAMME_ID_2 = str(uuid.uuid4())
PROGRAMME_ID_3 = str(uuid.uuid4())


def _auth_headers():
    return {"Authorization": "Bearer validtoken"}


def _mock_auth(mock_decode):
    mock_decode.return_value = {
        "sub": USER_ID,
        "email": "student@test.com",
        "role": "student",
    }


def _make_recommendations_response():
    """Minimal RecommendationsResponse-shaped dict with all three buckets."""
    from app.api.recommendations.schemas import (
        MatchStatus,
        ProgrammeMatch,
        RecommendationsResponse,
        UnmetRule,
    )

    return RecommendationsResponse(
        university_id=UNIVERSITY_ID,
        intake_year=2027,
        record_type_used="grade_12_june",
        aps=34,
        aps_max=42,
        programmes=[
            ProgrammeMatch(
                id=PROGRAMME_ID_1,
                name="BEng (Civil Engineering) ENGAGE",
                faculty="Engineering, Built Environment and IT",
                qualification_code="12136017",
                qualification_type="degree",
                duration_years=5,
                min_aps=33,
                status=MatchStatus.QUALIFIES,
                unmet_rules=[],
                notes=None,
            ),
            ProgrammeMatch(
                id=PROGRAMME_ID_2,
                name="BEng (Civil Engineering)",
                faculty="Engineering, Built Environment and IT",
                qualification_code="12130017",
                min_aps=35,
                status=MatchStatus.BORDERLINE,
                unmet_rules=[
                    UnmetRule(
                        requirement="APS 35",
                        have="APS 34",
                        shortfall="1 point",
                    )
                ],
                notes=None,
            ),
            ProgrammeMatch(
                id=PROGRAMME_ID_3,
                name="BSc (Actuarial and Financial Mathematics)",
                faculty="Natural and Agricultural Sciences",
                qualification_code="02133186",
                min_aps=38,
                status=MatchStatus.NOT_YET,
                unmet_rules=[
                    UnmetRule(
                        requirement="Mathematics 70%",
                        have="Mathematics 58%",
                        shortfall="12%",
                    ),
                    UnmetRule(
                        requirement="APS 38",
                        have="APS 34",
                        shortfall="4 points",
                    ),
                ],
                notes=None,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# GET /recommendations — happy path
# ---------------------------------------------------------------------------


def test_recommendations_happy_path_three_buckets():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.recommendations.service.get_recommendations"
    ) as mock_fn:
        _mock_auth(mock_decode)
        mock_fn.return_value = _make_recommendations_response()

        response = client.get(
            f"/recommendations?university_id={UNIVERSITY_ID}",
            headers=_auth_headers(),
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["university_id"] == UNIVERSITY_ID
    assert data["aps"] == 34
    assert data["aps_max"] == 42
    assert data["record_type_used"] == "grade_12_june"
    assert len(data["programmes"]) == 3
    # new fields round-trip
    assert data["programmes"][0]["qualification_type"] == "degree"
    assert data["programmes"][0]["duration_years"] == 5


def test_recommendations_sort_order_qualifies_borderline_not_yet():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.recommendations.service.get_recommendations"
    ) as mock_fn:
        _mock_auth(mock_decode)
        mock_fn.return_value = _make_recommendations_response()

        response = client.get(
            f"/recommendations?university_id={UNIVERSITY_ID}",
            headers=_auth_headers(),
        )

    app.dependency_overrides.clear()

    statuses = [p["status"] for p in response.json()["programmes"]]
    assert statuses == ["qualifies", "borderline", "not_yet"]


def test_recommendations_unmet_rules_shape():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.recommendations.service.get_recommendations"
    ) as mock_fn:
        _mock_auth(mock_decode)
        mock_fn.return_value = _make_recommendations_response()

        response = client.get(
            f"/recommendations?university_id={UNIVERSITY_ID}",
            headers=_auth_headers(),
        )

    app.dependency_overrides.clear()

    programmes = response.json()["programmes"]
    # qualifies — no unmet rules
    assert programmes[0]["unmet_rules"] == []
    # borderline — one APS rule
    borderline_rules = programmes[1]["unmet_rules"]
    assert len(borderline_rules) == 1
    assert borderline_rules[0] == {
        "requirement": "APS 35",
        "have": "APS 34",
        "shortfall": "1 point",
    }
    # not_yet — two rules
    assert len(programmes[2]["unmet_rules"]) == 2


# ---------------------------------------------------------------------------
# GET /recommendations — 409 when no academic record
# ---------------------------------------------------------------------------


def test_recommendations_409_no_academic_record():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.recommendations.service.get_recommendations"
    ) as mock_fn:
        _mock_auth(mock_decode)
        mock_fn.side_effect = HTTPException(
            status_code=409, detail={"code": "no_academic_record"}
        )

        response = client.get(
            f"/recommendations?university_id={UNIVERSITY_ID}",
            headers=_auth_headers(),
        )

    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "no_academic_record"


# ---------------------------------------------------------------------------
# GET /recommendations — auth required
# ---------------------------------------------------------------------------


def test_recommendations_requires_auth():
    response = client.get(f"/recommendations?university_id={UNIVERSITY_ID}")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /universities/{id}/programmes — catalogue
# ---------------------------------------------------------------------------


def _make_catalogue_response():
    from app.api.recommendations.schemas import (
        FacultyGroup,
        ProgrammeCatalogueItem,
        ProgrammesCatalogueResponse,
    )

    return ProgrammesCatalogueResponse(
        university_id=UNIVERSITY_ID,
        intake_year=2027,
        faculties=[
            FacultyGroup(
                faculty_id=str(uuid.uuid4()),
                faculty_name="Engineering, Built Environment and IT",
                close_date=None,
                programmes=[
                    ProgrammeCatalogueItem(
                        id=PROGRAMME_ID_1,
                        name="BEng (Civil Engineering) ENGAGE",
                        qualification_code="12136017",
                        qualification_type="degree",
                        duration_years=5,
                        min_aps=33,
                        notes=None,
                    ),
                    ProgrammeCatalogueItem(
                        id=PROGRAMME_ID_2,
                        name="Diploma in Architecture",
                        qualification_code="D8AT1Q",
                        qualification_type="diploma",
                        duration_years=3,
                        min_aps=35,
                        notes=None,
                    ),
                ],
            )
        ],
    )


def test_catalogue_happy_path():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode"), patch(
        "app.api.recommendations.service.list_university_programmes"
    ) as mock_fn:
        mock_fn.return_value = _make_catalogue_response()

        # Public endpoint — no auth header needed
        response = client.get(f"/universities/{UNIVERSITY_ID}/programmes")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["university_id"] == UNIVERSITY_ID
    assert data["intake_year"] == 2027
    assert len(data["faculties"]) == 1
    faculty = data["faculties"][0]
    assert faculty["faculty_name"] == "Engineering, Built Environment and IT"
    assert len(faculty["programmes"]) == 2
    # qualification_type / duration_years exposed in the catalogue
    assert faculty["programmes"][0]["qualification_type"] == "degree"
    assert faculty["programmes"][0]["duration_years"] == 5
    assert faculty["programmes"][1]["qualification_type"] == "diploma"


def test_catalogue_404_unknown_university():
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.middleware.auth.jwt.decode"), patch(
        "app.api.recommendations.service.list_university_programmes"
    ) as mock_fn:
        mock_fn.side_effect = HTTPException(
            status_code=404, detail="university_not_found"
        )
        response = client.get(f"/universities/{UNIVERSITY_ID}/programmes")

    app.dependency_overrides.clear()

    assert response.status_code == 404
