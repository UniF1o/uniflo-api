# Task 6 — Completed-Matric Automation: Wits

**Branch:** `feature/inclusivity-automation-wits`
**Status:** complete (mapping-layer + adapter radio click; live DOM specifics flagged for first-run verification)

---

## What was built

Extends the shared completed-matric plumbing from Task 5 (`_applicant_branch`,
`_guard_applicant_type`, `_COMPLETED_MATRIC_SLUGS`) and the UJ work to Wits.
Required both a mapping change and a small adapter change (the Current School Status
radio, which was previously left at its default and never set programmatically).

### Guard
- Added `"wits"` to `_COMPLETED_MATRIC_SLUGS` in `app/automation/mapping.py`, so the
  apply guard now permits completed-matric / gap-year applicants for Wits. At-university,
  upgrader and postgrad stay blocked for all portals (unchanged). UCT is the only portal
  still requiring a current Grade-12 applicant.

### Wits mapping (`_wits_mapping`) — branch-aware
| Field (Wits step) | current_learner | completed_matric |
|---|---|---|
| `school_status` key | absent (default radio) | `"Completed Grd 12 OR Upgrading"` |
| `current_activity` (Step 3) | `"School"` | `"Gap Year"` (gap) / `"Employment Or Occupation"` (employed) |
| subjects + school | from `grade_11_final` record | from `grade_12_final` record (fallback to gr11) |
| `examination_year` (Step 4) | intake − 1 / gr11 year | `grade_12_final` year (via `_matric_year`, already prefers it) |

Added `_wits_activity(profile)` — maps the profile `current_activity` to the exact
Wits Step-3 LOV options (`"Gap Year"` / `"Employment Or Occupation"` / `"School"`)
rather than relying on fuzzy matching for the completed-matric values whose wording
differs from the profile free text.

When `school_status` is absent from the mapping, `_step_secondary` is unchanged —
the Wits portal's "Current Grd 12" radio remains the default.

### Adapter change (`wits.py`) — `_step_secondary`
Added a conditional radio click at the start of `_step_secondary`:
```python
if mapping.get("school_status"):
    await fluid.js_click(page, _SCHOOL_STATUS_COMPLETED)
    await fluid.settle(page, 600)
```
The constant `_SCHOOL_STATUS_COMPLETED = '[id="VC_OA_STG_SEDH_VC_OA_SCHL_TYPE$1"]'`
targets the second radio option (PeopleSoft `$1` = index 1). Uses `fluid.js_click`
— same pattern as all other PeopleSoft controls that sit behind the `ps_indicator`
pointer-intercept overlay.

The document upload for Wits already handled `MATRIC_RESULTS` in `_UPLOAD_ROWS` (row 1 =
`MATRIC_RESULTS` OR `GRADE11_RESULTS`), so no upload-row change was needed.

### Tests
- `tests/test_mapping_completed_matric.py` — flipped the two Wits guard tests (now
  permits gap-year / employed) and added 9 Wits mapping tests: `school_status` key
  present/absent, subjects/school from the correct record, activity values for gap-year /
  employed / current-learner, and at-university still blocked.
- `tests/test_mapping_cross_portal.py` — `test_non_school_activity_fails_fast_*` now
  loops only `("uct",)`; added `test_gap_year_permitted_for_wits`.
- Full suite: **461 passed**; `ruff` clean.

---

## Decisions
- **`school_status` key as the adapter signal** — the mapping emits
  `"Completed Grd 12 OR Upgrading"` when the branch is completed-matric and omits the key
  for current-learners. `_step_secondary` checks `mapping.get("school_status")` — clean,
  explicit, and testable without running a browser.
- **Gr11 subject grid still holds the final marks** — Wits uses the Gr12 subject list
  (populated via "Copy Grade 11 Subjects") for eligibility checking. For a completed-matric
  applicant we feed the `grade_12_final` subjects into the Gr11 grid and let "Copy" populate
  the Gr12 grid with the same marks. The label says "Final Grade 11 Results" but the marks
  are the real Grade 12 finals — Wits checks eligibility against the Gr12 copy, so the
  right marks land where they matter.
- **`_wits_activity()` helper** — explicit LOV mapping rather than trusting fuzzy matching
  for "Gap Year" (exact match but let's be safe) and "Employment Or Occupation" (would need
  fuzzy to match "Working"). Consistent with the helper pattern in UP (`_up_tell_us_more_completed`)
  and UJ (`_uj_present_activity_completed`).

## Known limitations (verify at first live completed-matric run) ⚠️
- **`_SCHOOL_STATUS_COMPLETED` radio selector** — `$1` (PeopleSoft second-option suffix)
  was inferred from the naming convention; the Current School Status radio was never walked
  live for a completed-matric applicant. Confirm `VC_OA_STG_SEDH_VC_OA_SCHL_TYPE$1`
  targets "Completed Grd 12 OR Upgrading" on first supervised run. If the ordering is
  reversed, swap to `$0`.
- **Document row 1 label for completed-matric** — live research confirmed row 1 = "Final
  GR11 Results" for Current-Grd-12 applicants. The label likely changes to "Matric
  Certificate" or similar for "Completed Grd 12 OR Upgrading"; the row index (`$1`) is
  expected to remain the same, but verify at first run.
- **Gr11 grid with only a `grade_12_final` record** — the Gr11 grid is filled with the
  final marks (label mismatch accepted). If Wits portal validates the Gr11 grid separately
  from the Gr12 copy (e.g. a Gr11 average check), this may require a separate Gr11 entry.
  Not observed in live testing but unverified for the completed-matric radio state.

## How to verify (non-live)
```bash
pytest tests/test_mapping_completed_matric.py tests/test_mapping_cross_portal.py -v
pytest -q          # full suite (461 pass)
ruff check .       # clean
```
Inspect the Wits field mapping for a `grade_12_final` student: expect
`school_status == "Completed Grd 12 OR Upgrading"`, `current_activity == "Gap Year"` or
`"Employment Or Occupation"`, and subjects sourced from the final record.
