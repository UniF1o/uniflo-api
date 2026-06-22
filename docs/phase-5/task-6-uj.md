# Task 6 — Completed-Matric Automation: UJ

**Branch:** `feature/inclusivity-automation-uj`
**Status:** complete (mapping-layer; live DOM specifics flagged for first-run verification)

---

## What was built

Extends the shared completed-matric plumbing from Task 5 (`_applicant_branch`,
`_guard_applicant_type`, `_COMPLETED_MATRIC_SLUGS`) to UJ. No new shared code — UJ joins
the allowed set and its mapping becomes branch-aware.

### Guard
- Added `"uj"` to `_COMPLETED_MATRIC_SLUGS` in `app/automation/mapping.py`, so the apply
  guard now permits completed-matric / gap-year applicants for UJ. At-university,
  upgrader and postgrad stay blocked for all portals (unchanged).

### UJ mapping (`_uj_mapping`) — branch-aware
| Field (UJ page) | current_learner | completed_matric |
|---|---|---|
| `endorsement` (Page C) | `CURRENTLY IN GR.12` | `BACHELORS DEGREE` |
| `present_activity` (Page D) | `current_activity` or `GRADE 12 PUPIL` | `EMPLOYED` (working) / `UNEMPLOYED` (gap-year, default) |
| subjects + school | from `grade_11_final` record | from `grade_12_final` record (fallback to gr11) |
| `matric_year` (Page C) | intake − 1 / gr11 year | `grade_12_final` year (via `_matric_year`, which already prefers it) |

Added `_uj_present_activity_completed(profile)` deriving the Page-D activity from
`current_activity`. The UJ adapter resolves both `endorsement` and `present_activity`
through its fuzzy `select_from_lov`, so the new option text matches the live LOV rows at
fill time — **no adapter DOM change was required** (same approach as UP Task 5, whose
fields go through `_select_label_best`).

### Tests
- `tests/test_mapping_completed_matric.py` — flipped the two UJ guard tests (now permits
  gap-year / employed) and added 8 UJ mapping tests (endorsement, present_activity for
  gap-year vs working, subjects/school from the final record, current-learner unchanged,
  at-university still blocked).
- `tests/test_mapping_cross_portal.py` — `test_non_school_activity_fails_fast_*` now loops
  only `("uct", "wits")`; added `test_gap_year_permitted_for_uj`.
- Full suite: **450 passed**; `ruff` clean.

---

## Decisions
- **Endorsement defaults to `BACHELORS DEGREE`** for a completed-matric *degree* applicant.
  The profile doesn't store the student's actual NSC pass level, and they are applying for
  degrees, so the Bachelor's-degree endorsement is the safe default — consistent with UP's
  `exemption_type = "Admit to Bachelor Studies"` (Task 5). The adapter fuzzy-matches it
  against the live endorsement LOV.
- **present_activity** maps working/employed → `EMPLOYED`, everything else → `UNEMPLOYED`
  (gap-year, unspecified). UJ's Page-D LOV is fuzzy-matched.
- **No adapter change** — UJ already drives endorsement/activity via `select_from_lov` and
  subjects via the LOV loop, all text-matched, so branch values flow through unchanged.

## Known limitations (verify at first live completed-matric run) ⚠️
- **Endorsement + Page-D activity LOV text** — only the *current-Gr12* options were walked
  live (`docs/phase-3/portal-research/uj.md`). `BACHELORS DEGREE` / `EMPLOYED` /
  `UNEMPLOYED` are best-guess option labels matched fuzzily; confirm the exact LOV rows on
  the first supervised completed-matric run and adjust the constants if UJ uses different
  wording.
- **Gr11 vs Gr12 mark column** — the UJ adapter writes the percentage into the Gr11 column
  (`#oapsymbGr11`, the mislabelled "symbol" field); the Gr12-final columns were never
  walked live. A completed-matric applicant's **final** marks are therefore entered, and
  are correct, but land in the Gr11 column. Placing them in the dedicated Gr12-final
  columns is a later, live-verified adapter extension — not built here. The marks UJ uses
  for its eligibility tag are still the student's real final marks.

## How to verify (non-live)
```bash
pytest tests/test_mapping_completed_matric.py tests/test_mapping_cross_portal.py -v
pytest -q          # full suite (450 pass)
ruff check .       # clean
```
Inspect the UJ field mapping for a `grade_12_final` student: expect
`endorsement == "BACHELORS DEGREE"`, `present_activity` of `EMPLOYED`/`UNEMPLOYED`, and
subjects sourced from the final record.
