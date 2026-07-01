"""Tests for GET /careers and GET /careers/{id}/programmes.

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

USER_ID = "a1b2c3d4-0000-0000-0000-ffeeddcc0001"
CAREER_ID_1 = str(uuid.uuid4())
CAREER_ID_2 = str(uuid.uuid4())
UNIVERSITY_ID = str(uuid.uuid4())
PROGRAMME_ID = str(uuid.uuid4())


def _auth_headers():
    return {"Authorization": "Bearer validtoken"}


def _mock_auth(mock_decode):
    mock_decode.return_value = {
        "sub": USER_ID,
        "email": "student@test.com",
        "role": "student",
    }


# ─── GET /careers ───────────────────────────────────────────────────────────

class TestListCareers:
    def _make_careers_response(self):
        from app.api.careers.schemas import (
            CareerRead,
            CareersListResponse,
            CompensationOut,
            EmployabilityOut,
        )

        return CareersListResponse(
            careers=[
                CareerRead(
                    id=CAREER_ID_1,
                    slug="civil-engineer",
                    title="Civil Engineer",
                    industry="Engineering & Built Environment",
                    description="Design and build infrastructure.",
                    compensation=CompensationOut(
                        entry=25000,
                        mid=45000,
                        senior=65000,
                        currency="ZAR",
                        period="month",
                        display="R25k – R65k+/mo",
                    ),
                    employability=EmployabilityOut(
                        demand="High",
                        outlook="Strong",
                        pathways=["BEng Civil Engineering (4 years)"],
                    ),
                    required_subjects=["Mathematics", "Physical Sciences"],
                ),
                CareerRead(
                    id=CAREER_ID_2,
                    slug="software-developer",
                    title="Software Developer",
                    industry="Information & Communication Technology",
                    description="Build software applications.",
                    compensation=CompensationOut(
                        entry=20000,
                        mid=55000,
                        senior=100000,
                        currency="ZAR",
                        period="month",
                        display="R20k – R100k/mo",
                    ),
                    employability=EmployabilityOut(
                        demand="Very high",
                        outlook="Exceptional",
                        pathways=["BSc Computer Science (3–4 years)"],
                    ),
                    recommended_subjects=[],
                ),
            ]
        )

    def test_returns_careers_for_authenticated_student(self):
        mock_session = MagicMock()
        app.dependency_overrides[get_session] = lambda: mock_session

        with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
             patch("app.api.careers.service.list_careers") as mock_service:
            _mock_auth(mock_decode)
            mock_service.return_value = self._make_careers_response()

            resp = client.get("/careers", headers=_auth_headers())

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        body = resp.json()
        assert "careers" in body
        assert len(body["careers"]) == 2
        assert body["careers"][0]["slug"] == "civil-engineer"
        assert body["careers"][1]["slug"] == "software-developer"

    def test_career_card_fields_present(self):
        mock_session = MagicMock()
        app.dependency_overrides[get_session] = lambda: mock_session

        with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
             patch("app.api.careers.service.list_careers") as mock_service:
            _mock_auth(mock_decode)
            mock_service.return_value = self._make_careers_response()

            resp = client.get("/careers", headers=_auth_headers())

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        career = resp.json()["careers"][0]
        assert career["compensation"]["period"] == "month"
        assert career["compensation"]["currency"] == "ZAR"
        assert "demand" in career["employability"]
        assert "pathways" in career["employability"]
        assert career["required_subjects"] == ["Mathematics", "Physical Sciences"]

    def test_returns_409_when_no_academic_record(self):
        mock_session = MagicMock()
        app.dependency_overrides[get_session] = lambda: mock_session

        with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
             patch("app.api.careers.service.list_careers") as mock_service:
            _mock_auth(mock_decode)
            mock_service.side_effect = HTTPException(
                status_code=409, detail={"code": "no_academic_record"}
            )

            resp = client.get("/careers", headers=_auth_headers())

        app.dependency_overrides.clear()
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "no_academic_record"

    def test_requires_authentication(self):
        resp = client.get("/careers")
        assert resp.status_code == 401

    def test_intake_year_query_param_is_forwarded(self):
        mock_session = MagicMock()
        app.dependency_overrides[get_session] = lambda: mock_session

        with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
             patch("app.api.careers.service.list_careers") as mock_service:
            _mock_auth(mock_decode)
            mock_service.return_value = self._make_careers_response()

            resp = client.get("/careers?intake_year=2027", headers=_auth_headers())

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        call_kwargs = mock_service.call_args
        assert call_kwargs.kwargs.get("intake_year") == 2027 or 2027 in call_kwargs.args


# ─── GET /careers/{id}/programmes ──────────────────────────────────────────

class TestListCareerProgrammes:
    def _make_programmes_response(self, tvet_only: bool = False):
        from app.api.careers.schemas import (
            CareerProgrammeMatch,
            CareerProgrammesResponse,
            CareerUniversityGroup,
        )

        universities = [] if tvet_only else [
            CareerUniversityGroup(
                university_id=UNIVERSITY_ID,
                university_name="University of Pretoria",
                scoring_method="up_aps",
                aps=34,
                aps_max=42,
                programmes=[
                    CareerProgrammeMatch(
                        id=PROGRAMME_ID,
                        name="BEng (Civil Engineering)",
                        faculty="Engineering, Built Environment and IT",
                        qualification_type="degree",
                        duration_years=4,
                        min_aps=33,
                        status="qualifies",
                        unmet_rules=[],
                        notes=None,
                    )
                ],
            )
        ]

        return CareerProgrammesResponse(
            career_id=CAREER_ID_1,
            career_title="Civil Engineer",
            universities=universities,
            tvet_only=tvet_only,
        )

    def test_returns_university_grouped_programmes(self):
        mock_session = MagicMock()
        app.dependency_overrides[get_session] = lambda: mock_session

        with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
             patch("app.api.careers.service.list_career_programmes") as mock_service:
            _mock_auth(mock_decode)
            mock_service.return_value = self._make_programmes_response()

            resp = client.get(f"/careers/{CAREER_ID_1}/programmes", headers=_auth_headers())

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        body = resp.json()
        assert body["career_id"] == CAREER_ID_1
        assert body["career_title"] == "Civil Engineer"
        assert len(body["universities"]) == 1
        assert body["universities"][0]["university_name"] == "University of Pretoria"
        assert len(body["universities"][0]["programmes"]) == 1
        assert body["universities"][0]["programmes"][0]["status"] == "qualifies"

    def test_programme_fields_present(self):
        mock_session = MagicMock()
        app.dependency_overrides[get_session] = lambda: mock_session

        with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
             patch("app.api.careers.service.list_career_programmes") as mock_service:
            _mock_auth(mock_decode)
            mock_service.return_value = self._make_programmes_response()

            resp = client.get(f"/careers/{CAREER_ID_1}/programmes", headers=_auth_headers())

        app.dependency_overrides.clear()
        body = resp.json()
        prog = body["universities"][0]["programmes"][0]
        assert "min_aps" in prog
        assert "duration_years" in prog
        assert "faculty" in prog
        assert prog["unmet_rules"] == []

    def test_tvet_only_flag_when_no_university_matches(self):
        mock_session = MagicMock()
        app.dependency_overrides[get_session] = lambda: mock_session

        with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
             patch("app.api.careers.service.list_career_programmes") as mock_service:
            _mock_auth(mock_decode)
            mock_service.return_value = self._make_programmes_response(tvet_only=True)

            resp = client.get(f"/careers/{CAREER_ID_1}/programmes", headers=_auth_headers())

        app.dependency_overrides.clear()
        body = resp.json()
        assert body["tvet_only"] is True
        assert body["universities"] == []

    def test_returns_404_for_unknown_career(self):
        mock_session = MagicMock()
        app.dependency_overrides[get_session] = lambda: mock_session
        unknown_id = str(uuid.uuid4())

        with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
             patch("app.api.careers.service.list_career_programmes") as mock_service:
            _mock_auth(mock_decode)
            mock_service.side_effect = HTTPException(
                status_code=404, detail={"code": "career_not_found"}
            )

            resp = client.get(f"/careers/{unknown_id}/programmes", headers=_auth_headers())

        app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_requires_authentication(self):
        resp = client.get(f"/careers/{CAREER_ID_1}/programmes")
        assert resp.status_code == 401
