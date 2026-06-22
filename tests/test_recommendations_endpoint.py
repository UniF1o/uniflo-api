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
        ProgrammeCombination,
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
                        combination=ProgrammeCombination(
                            majors_min=1, majors_max=2, rule="Take with a second major."
                        ),
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
    # combination round-trips
    combo = faculty["programmes"][0]["combination"]
    assert combo["majors_min"] == 1 and combo["majors_max"] == 2
    assert faculty["programmes"][1]["combination"] is None


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


# Task 3 confirming tests — catalogue picker-readiness
# No backend changes required; these document the existing guarantees.


# Task 4 confirming tests — grade_12_final record type + best-available ordering


def test_best_available_prefers_grade_12_final_when_present():
    """_best_available_record returns grade_12_final first when the student has one."""
    import uuid as _uuid

    from app.api.recommendations import service as rec_service

    profile_id = _uuid.uuid4()
    final_record = MagicMock()
    final_record.record_type = "grade_12_final"

    session = MagicMock()
    # First exec call (grade_12_final) returns the record; function stops there.
    session.exec.return_value.first.return_value = final_record

    result = rec_service._best_available_record(session, profile_id, record_type=None)
    assert result is final_record


def test_best_available_falls_back_to_june_when_final_absent():
    """When grade_12_final is absent, grade_12_june is the next choice."""
    import uuid as _uuid

    from app.api.recommendations import service as rec_service

    profile_id = _uuid.uuid4()
    june_record = MagicMock()
    june_record.record_type = "grade_12_june"

    session = MagicMock()
    # First call (grade_12_final) → None; second call (grade_12_june) → june_record.
    session.exec.return_value.first.side_effect = [None, june_record]

    result = rec_service._best_available_record(session, profile_id, record_type=None)
    assert result is june_record


def test_best_available_grade_12_final_beats_june_and_april():
    """grade_12_final is returned even when june and april records also exist."""
    import uuid as _uuid

    from app.api.recommendations import service as rec_service

    profile_id = _uuid.uuid4()
    final_record = MagicMock()
    final_record.record_type = "grade_12_final"

    session = MagicMock()
    # Only one exec call needed — grade_12_final found immediately.
    session.exec.return_value.first.return_value = final_record

    result = rec_service._best_available_record(session, profile_id, record_type=None)
    assert result.record_type == "grade_12_final"
    # Confirm only one DB query was made (found on first preference).
    assert session.exec.call_count == 1


def test_recommendations_record_type_used_echoes_grade_12_final():
    """`record_type_used` in the recommendations response echoes grade_12_final."""
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    from app.api.recommendations.schemas import RecommendationsResponse

    response_obj = RecommendationsResponse(
        university_id=UNIVERSITY_ID,
        intake_year=2027,
        record_type_used="grade_12_final",
        aps=36,
        aps_max=42,
        programmes=[],
    )

    with patch("app.api.middleware.auth.jwt.decode") as mock_decode, patch(
        "app.api.recommendations.service.get_recommendations"
    ) as mock_fn:
        _mock_auth(mock_decode)
        mock_fn.return_value = response_obj
        response = client.get(
            f"/recommendations?university_id={UNIVERSITY_ID}",
            headers=_auth_headers(),
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["record_type_used"] == "grade_12_final"


def test_catalogue_is_public_no_auth_required():
    """GET /universities/{id}/programmes is in the public-route list — no JWT needed."""
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.recommendations.service.list_university_programmes") as mock_fn:
        mock_fn.return_value = _make_catalogue_response()
        # Deliberately omit any Authorization header
        response = client.get(f"/universities/{UNIVERSITY_ID}/programmes")

    app.dependency_overrides.clear()
    assert response.status_code == 200


def test_catalogue_close_date_per_faculty_round_trips():
    """Faculty close_date is exposed in the response so the frontend can compute open/closed."""
    from datetime import date

    from app.api.recommendations.schemas import (
        FacultyGroup,
        ProgrammeCatalogueItem,
        ProgrammesCatalogueResponse,
    )

    catalogue = ProgrammesCatalogueResponse(
        university_id=UNIVERSITY_ID,
        intake_year=2027,
        faculties=[
            FacultyGroup(
                faculty_id=str(uuid.uuid4()),
                faculty_name="Engineering",
                close_date=date(2026, 9, 30),
                programmes=[
                    ProgrammeCatalogueItem(
                        id=PROGRAMME_ID_1,
                        name="BEng Civil",
                        qualification_code="X",
                        min_aps=30,
                        notes=None,
                    )
                ],
            )
        ],
    )

    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("app.api.recommendations.service.list_university_programmes") as mock_fn:
        mock_fn.return_value = catalogue
        response = client.get(f"/universities/{UNIVERSITY_ID}/programmes")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["faculties"][0]["close_date"] == "2026-09-30"
