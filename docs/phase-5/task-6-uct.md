# Task 6 — Completed-Matric Automation: UCT

**Branch:** `feature/inclusivity-automation-uct`
**Status:** complete (mapping-layer; Step 7 Post School Activity fields for completed-matric are unverified — see ⚠️ below)

---

## What was built

Extends the shared completed-matric plumbing from Task 5 (`_applicant_branch`,
`_guard_applicant_type`, `_COMPLETED_MATRIC_SLUGS`) and Task 6 (UJ, Wits) to UCT.
UCT is the most complex of the four portals for the completed-matric branch because
its subject scheme carries two mark columns (Gr11 final % + April %) and because Step 7
(Post School Activity) was only verified live for current-Grade-12 applicants.

No adapter code change was needed — the mapping-layer changes are sufficient for the
fields that were live-verified.

### Guard
- Added `"uct"` to `_COMPLETED_MATRIC_SLUGS` in `app/automation/mapping.py`. All four
  portals now permit completed-matric / gap-year applicants; at-university, upgrader, and
  postgrad remain universally blocked.

### UCT mapping (`_uct_mapping`) — branch-aware
| Aspect | current_learner | completed_matric |
|---|---|---|
| Subject base (Gr11 % column) | `grade_11_final` subjects | `grade_12_final` subjects (fallback to Gr11) |
| April column | from `grade_12_april` record | from `grade_12_april` if present; otherwise **final marks proxy** |
| School (Step 5) | `grade_11_final` institution | `grade_12_final` institution (fallback to Gr11) |
| `matric_year` (Step 5) | already preferred `grade_12_final` year via `_matric_year` | unchanged — same helper |
| Step 7 Post School Activity | zero fields; just Save | ⚠️ unverified — see below |

**April proxy logic:** when a completed-matric student has `grade_12_final` but no
`grade_12_april` record, the final marks fill the April column. This is the best
approximation available: UCT uses both Gr11 and April marks to compute its Weighted
Points Score. If the student later uploads a `grade_12_april` record, the mapping will
prefer the actual April marks. The proxy produces a consistent subject list where every
subject has an April value, which prevents UCT's subject modal from rejecting the entry.

### No adapter change
`_step7_post_school` currently just calls `fluid.save_step`. For current-Grade-12
applicants Step 7 has zero fields. For completed-matric applicants the portal may
render Post School Activity fields — those are unverified and flagged below. The Save
still proceeds; if UCT raises a validation error for missing required Step-7 fields, the
run will park at Step 7 and require manual completion on first supervised run.

### Tests
- `tests/test_mapping_completed_matric.py` — replaced the two UCT guard tests (now
  permit gap-year / employed) and added 6 UCT mapping tests: subjects from `grade_12_final`,
  final marks proxying for April, school from the final record, current-learner unchanged,
  no April key for current-learner without a `grade_12_april` record, at-university blocked.
- `tests/test_mapping_cross_portal.py` — replaced `test_non_school_activity_fails_fast_*`
  with `test_at_university_fails_fast_for_all_portals` (loops all four portals, blocking
  at-university for all); added `test_gap_year_permitted_for_uct`.
- Full suite: **469 passed**; `ruff` clean.

---

## Decisions
- **April proxy** — preferred over leaving the April column empty. UCT's subject modal
  requires an April % (it's marked required in the field catalog); leaving it empty would
  cause a portal-level validation failure. The final marks are the highest-quality data
  available and are at least as informative as any proxy could be.
- **No adapter change** — the UCT adapter's Step 7 implementation already calls Save; if
  Step 7 has no required fields for completed-matric (or has optional ones), the run will
  continue. Only if required fields appear will the run fail, at which point a targeted
  adapter extension can be added.

## Known limitations (verify at first live completed-matric run) ⚠️
- **Step 7 Post School Activity fields** — live research was conducted with a
  current-Grade-12 applicant; Step 7 showed zero fields and just required Save. A
  completed-matric applicant may see additional fields (e.g. employer name, gap-year
  activity, year ranges). If UCT marks any as required, the Save will fail and the run
  will park at Step 7. At first supervised run: inspect Step 7, identify any required
  fields, then add a `post_school_activity_*` block to both `_uct_mapping` and
  `_step7_post_school` to handle them.
- **April proxy when both `grade_12_final` AND `grade_12_april` exist** — the logic
  correctly prefers the real `grade_12_april` record. Verify that the subject-name
  matching (upper-case key) aligns for all subject names when both records are present.
- **Subject slot semantics** — the UCT Gr11 subject grid is slot-semantic (row 0 = Home
  Language only, row 2 = Maths variants, etc.; see `uct.md` live-spike findings). The
  completed-matric subjects are still processed by the same slot-aware adapter code,
  which fuzzy-matches by slot constraints. If a `grade_12_final` subject list differs
  from the Gr11 list (e.g. the student dropped a subject), the slot assignment should
  still work — but verify at first run.

## How to verify (non-live)
```bash
pytest tests/test_mapping_completed_matric.py tests/test_mapping_cross_portal.py -v
pytest -q          # full suite (469 pass)
ruff check .       # clean
```
Inspect the UCT field mapping for a `grade_12_final` student: expect subjects from the
final record with each subject carrying both `percentage` (base) and `april` (proxy from
the same record), and `school` from the `grade_12_final` institution.
