# Task 5 — UJ programmes (+ diplomas, qualification_type)

**Branch:** `feature/programmes-uj` · **PR:** #57 (merged) · **Seeded to prod**

## What was built
- `data/programmes/uj.json` — **177 programmes across all 8 faculties**: 149 bachelor + extended degrees and **28 diplomas + extended diplomas**. intake_year 2027, close 2026-10-31. Reuses **`up_aps`** (UJ's APS bands match UP's — no `uj_aps` needed).
- **Engine extensions** (additive, in `scoring.py`): per-option subject levels (`requirements.subject_rules[].options`, e.g. *Maths 60% OR Maths Lit 50%*) and **conditional APS** (`requirements.aps_rule`, e.g. *25 with Maths / 26 with Maths Lit*).
- **New columns `qualification_type` + `duration_years`** on `programmes` (migration **`e2a1c4b6d8f0`**), persisted by the seed, exposed on `ProgrammeCatalogueItem` and `ProgrammeMatch` (additive OpenAPI change → Partner A `npm run types:api`).
- **Generalised seed** — `scripts/seed_programmes.py` now takes a filename + a `REGISTRY` (file → university, scoring_method); idempotent across universities.
- Tests for the new shapes + endpoint field round-trip.

## Key decisions
- **`qualification_type`** = `degree | diploma | higher_certificate`; extended programmes are not a separate type (captured by `duration_years`).
- Diplomas added on the same PR at the user's request; scope = diplomas + extended diplomas (online + NCV/NASCA/SC(a) deferred).
- **Year catch:** UJ's first PDF was the 2026 prospectus; the authoritative **2027** guide was sourced and used.

## How to verify
- Prod: **UJ = `up_aps`, 8 faculties, 177 active** (149 degree / 28 diploma); UP re-seeded to populate the new columns (120; 117 degree / 2 higher_certificate / 1 diploma).
- `pytest` green incl. new scoring + endpoint tests; `check_prospectus_year.py` current.
