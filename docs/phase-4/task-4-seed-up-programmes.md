# Task 4 — UP prospectus → `up.json` + seed + freshness pipeline

**Branch:** `feature/seed-up-programmes` · **PR:** #56 (merged) · **Seeded to prod**

## What was built
- `data/programmes/up.json` — **120 programmes across all 9 UP faculties**, intake_year 2027. Top-level `intake_year`, `default_close_date` (2026-06-30), `faculty_overrides` (Veterinary Science 2026-05-31), `programmes`. Each entry: `qualification_code` (null where none printed), `name`, `faculty`, `duration_years`, `min_aps`, `requirements.subject_rules`, `notes`, `source_page`, `is_active`.
- `scripts/seed_programmes.py` — plain SQLAlchemy, no AI; resolves UP by name, upserts faculties + programmes on `(university_id, qualification_code, intake_year)` (fallback `name`+`intake_year`), sets `scoring_method = "up_aps"`. Idempotent.
- **Freshness pipeline** (beyond the original plan): `app/intake.py` (`active_intake_year()`), `app/programme_data.py` (classifies each `data/programmes/*.json` as current/stale/ahead), `scripts/check_prospectus_year.py` (CI step, exit 1 on stale), seed refuses stale data unless `--allow-stale`; tests + a live tripwire.

## Key decisions
- **Storage: only the reviewed JSON is committed.** Raw prospectus PDFs + transcription scratch stay in gitignored `uni_data/`; provenance via per-entry `source_page`.
- Transcription is in-session (Read tool over the PDF), human-reviewed in the PR diff — admissions data that's wrong actively misleads students.
- Built university-scoped so later universities are data + (maybe) a scoring function.

## Deviations from plan
- Added the freshness pipeline (not in the original task scope).
- Seeded **all 9 faculties** in one pass rather than one faculty first.

## Status / verify
- Prod: **UP = `up_aps`, 9 faculties, 120 active programmes** (Vet Science close 2026-05-31 applied).
- `python scripts/check_prospectus_year.py` → up.json current for 2027.
- Reviewer flag (resolved at merge): the Built Environment trio (Construction Management, Real Estate, Quantity Surveying) had an ambiguous Physical Sciences requirement, noted in their `notes`.
