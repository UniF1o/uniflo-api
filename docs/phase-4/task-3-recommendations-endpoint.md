# Task 3 — `/recommendations` endpoint (+ catalogue)

**Branch:** `feature/recommendations-endpoint` · **PR:** #55 (merged)

## What was built
`app/api/recommendations/{router,service,schemas}.py`, registered in `app/main.py`.

- `GET /recommendations?university_id=<uuid>&record_type=<...>&intake_year=<...>` (authenticated, rate-limited):
  - Resolves the profile from `request.state.user["sub"]`.
  - Loads the requested `record_type`, else **best available** (`grade_12_june` > `grade_12_april` > `grade_11_final`); returns **`409 {"code": "no_academic_record"}`** if none.
  - Loads the university's **active programmes for the active intake year**, computes APS once via `compute_aps(subjects, university.scoring_method)`, runs `evaluate` per programme.
  - Sorts **qualifies → borderline → not_yet**, then ascending by APS gap.
- `GET /universities/{id}/programmes` (public) — the faculty→programme **catalogue** (no matching), grouped by faculty; the Phase 5 picker's data source.
- `schemas.py` matches the locked **Appendix A** so the OpenAPI spec is the contract Partner A regenerates from.
- `tests/test_recommendations_endpoint.py` — `TestClient` + mocked service: happy path (three buckets + sort order), `409`, auth required.

## Key decisions
- `status` enum strings locked: `qualifies | borderline | not_yet`.
- `aps` + `aps_max` returned for a progress display (`aps_max` per scoring method).
- Catalogue and recommendations share one service module.

## Deviations from plan
- The active-intake-year default was later centralised into `app/intake.py` (`active_intake_year()`) by the Task 4 freshness pipeline; the service imports it.
- `ProgrammeMatch` and `ProgrammeCatalogueItem` gained additive optional fields **`qualification_type`** and **`duration_years`** in the UJ task (`task-5-uj.md`) — backward-compatible OpenAPI change.

## How to verify
- `pytest tests/test_recommendations_endpoint.py` green.
- Live (post-deploy): `GET /recommendations?university_id=<UP>` as the test student returns the three buckets; a profile with no records returns `409`.
