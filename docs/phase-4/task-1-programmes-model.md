# Task 1 — `programmes` data model + migration

**Branch:** `feature/programmes-model` · **PR:** #53 (merged)

## What was built
The catalogue spine that every later task reads.

- `app/models/faculty.py` — `faculties` table: `id`, `university_id` FK (indexed), `name`, nullable `close_date` (per-faculty deadline, e.g. UP Veterinary Science closes 31 May while the rest close 30 June).
- `app/models/programme.py` — `programmes` table: `id`, `university_id` FK, `faculty_id` FK, `name`, `qualification_code` (nullable), `intake_year`, `min_aps` (nullable), `requirements` JSONB, `notes`, `is_active` (default false), `source_page`, `created_at`/`updated_at`.
- `app/models/university.py` — added `scoring_method` (str, nullable) to dispatch the APS function per university.
- Both registered in `app/models/__init__.py`.
- Migration `7bd16112db5c` — additive, reversible (two tables + the column).
- `tests/test_programmes_model.py` — model-import smoke test.

## Key decisions
- **Faculty is a table, not a string** — it's a selectable level (Phase 5 picker) and carries metadata (deadlines).
- **Canonical identity `(university_id, qualification_code, intake_year)`** — the key the seed upserts on and the portal walkthroughs reconcile against.
- **`requirements` JSONB** holds `subject_rules`; subject names come from the frozen NSC list. `min_mark` (%) or `min_level` (NSC 1–7).
- `is_active` gates what the matcher returns.

## Deviations from plan
- A later additive migration **`e2a1c4b6d8f0`** (in the UJ task) added `qualification_type` and `duration_years` to `programmes` — see `task-5-uj.md`.

## How to verify
- `alembic current` → head includes `7bd16112db5c` (now `e2a1c4b6d8f0`).
- `pytest tests/test_programmes_model.py` green.
