# Task 2 — Application contract accepts and returns `programme_id`
# (Task 3 — Catalogue picker-readiness folded in)

**Branch:** `feature/application-programme-id`
**Migration head unchanged:** `c1856b74cc36` (Task 1 added the columns; no migration here)

## What was built

### Schemas (`app/api/applications/schemas.py`)

- `ApplicationCreate` gains optional `programme_id: Optional[uuid.UUID]` and
  `additional_programme_ids: Optional[list[uuid.UUID]]`, both capped at
  `MAX_ADDITIONAL_PROGRAMMES = 2`. A model-level validator enforces equal length
  when both `additional_programmes` and `additional_programme_ids` are present.
- `ApplicationRead.programme_id` — nullable UUID, returned alongside `programme`.
- `ApplicationChoiceRead.programme_id` — nullable UUID, returned per choice.

### Service (`app/api/applications/service.py`)

- `_resolve_programme(session, programme_id, university_id)` — loads a programme,
  asserts `is_active` and `university_id` match; raises HTTP 422
  `"programme_not_found_or_invalid"` otherwise.
- `create_application` — when `programme_id` is supplied, calls `_resolve_programme`
  and **overwrites `programme` with the catalogue name** (id is authoritative; the
  client-sent name is ignored for that slot). When no id is supplied the free-text
  path is unchanged and `programme_id` stays `NULL`. Per-choice `programme_id` is
  persisted on `ApplicationChoice` rows.

### Back-compat

Existing free-text applications continue to work unmodified. All new fields are
optional with `None` defaults; old rows surface `programme_id = null`.

## Task 3 — Catalogue endpoint picker-readiness (no backend change)

`GET /universities/{id}/programmes` already satisfies all picker requirements:

- Filters `is_active == True` and by intake year in `_load_active_programmes`.
- Listed under `/universities/*` in the public-route bypass — no JWT required.
- Returns `id`, `name`, `qualification_code`, `qualification_type`, `duration_years`,
  `min_aps`, `notes`, `combination` per programme and `close_date` per faculty.
  The frontend derives "closed" from `close_date`; no per-programme flag is needed.

No backend changes. Two confirming tests added to `test_recommendations_endpoint.py`.

## Decisions

- **422 not 404** for invalid/wrong-university/inactive `programme_id` — it is a
  request-body validation error, not a resource lookup failure.
- **Single error code** `"programme_not_found_or_invalid"` for all three rejection
  reasons (not found, inactive, wrong university) to avoid leaking enumeration info.
- **`programme` string stays required** in `ApplicationCreate` for display and
  back-compat. The service overwrites it with the catalogue name when `programme_id`
  is supplied.
- **Parallel length enforced** when both `additional_programmes` and
  `additional_programme_ids` are provided; either alone is valid.

## How to verify

```bash
# 1. Free-text create — programme_id null in response
curl -X POST /applications \
  -d '{"university_id":"<id>","programme":"BSc CS","application_year":2027}'

# 2. programme_id create — name derived from catalogue
curl -X POST /applications \
  -d '{"university_id":"<id>","programme":"ignored","programme_id":"<prog_id>","application_year":2027}'

# 3. Wrong university — 422
curl -X POST /applications \
  -d '{"university_id":"<uni_a>","programme":"x","programme_id":"<prog_from_uni_b>","application_year":2027}'

# 4. Catalogue public (no auth)
curl /universities/<id>/programmes
```

## Tests

6 new service-level tests in `test_applications_endpoints.py`:
- `test_create_application_programme_id_derives_name`
- `test_create_application_free_text_programme_id_null`
- `test_create_application_programme_id_wrong_university`
- `test_create_application_inactive_programme_rejected`
- `test_create_application_with_additional_programme_ids`
- `test_create_application_mismatched_additional_lengths_rejected`

2 confirming tests in `test_recommendations_endpoint.py` (Task 3):
- `test_catalogue_is_public_no_auth_required`
- `test_catalogue_close_date_per_faculty_round_trips`
