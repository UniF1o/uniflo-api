# Task 4 — UJ adapter (first adapter)

`app/automation/adapters/uj.py` + `uj.fields.json`. UJ (ITS Integrator) is the
simplest target: no captcha, and a new applicant doesn't log in — the entry/POPI
gate leads straight into the form; a student number + 5-digit PIN are issued at
submit.

Status: **login (entry/POPI gate) and the biographical page (Page A) are
live-verified (2026-06-05)**; LOV search popups, pages B–G, and the submit page
are scaffolded and marked **[VERIFY LIVE]** for the next supervised walk.

## ⚠️ Selector strategy — id, not the accessibility tree

The locked Phase 3 decision was "approach C: accessibility-tree primary". **That
does not hold for ITS Integrator.** Live inspection showed UJ's inputs carry
**no accessible names** — `get_by_role("combobox")` finds an unnamed control,
and the checkboxes/submit buttons aren't even exposed as `checkbox`/`button`
roles. So locating by role+label fails.

Every field *does* carry a **stable element id** (`oapSurname`, `oapTitle`,
`oapStreetAddr1`, …) with proper `<select>` option labels. **That's the reliable
handle for ITS**, and the adapter uses id/CSS selectors (`page.fill("#id", …)`,
`page.select_option("#id", label=…)`). The accessibility-first approach likely
still holds for the PeopleSoft portals (UCT/Wits/UP) — re-confirm per portal.

`uj.fields.json` therefore carries a `selector` (the id) per field alongside the
`label` (which drives the AI mapping). Page A selectors + option lists are
verified; pages B–G have `selector: null` until walked.

## Verified: entry/POPI gate (login)

`page.goto(ENTRY_URL)` → answer three dropdowns by **value** (`"N"` = No), tick
POPI, click Next. Ids: `#oapOldNew`, `#oapReturnYesNo`, `#oapTokenYesNo`,
`#oapAcceptPopi`, `#oapNextBtn1`. Each answer reveals the next control, so the
adapter waits between them. This lands on the biographical page
(`…/gen.gw1pkg.gw1proc`). No login, no captcha. ✅

## Verified: biographical page (Page A)

A dry fill of Jane Doe's data filled **16/19** fields and read back correctly
(`#oapSurname` = "Doe", `#itsEmail` confirmed). Verified ids include
`#oapCitizenType`, `#oapIDnumber`, `#oapBirthdate`, `#oapTitle`, `#oapInitials`,
`#oapSurname`, `#oapFirstNames`, `#oapMaritalStatus`, `#oapHomeLang`,
`#oapEthnic`, `#oapStreetAddr1-4`, `#oapSACell`, `#itsEmail`, `#verifyEmail`,
`#oapResReq`.

**Fields the research doc missed** (now in the schema): **Gender**
(`#oapGender`), **funding source** (`#oapSourcefund` — NSFAS / Self Paying /
Other), and a **Parent/Guardian** block for minors (`#oapGuardName/Cell/Email`
+ an under-age I-Accept).

**Three conditional fields** timed out on a blind fill — `#oapGender`,
`#oapSourcefund`, `#oapCellInd` — because they're conditionally shown or
auto-derived (gender + DOB auto-populate from a valid SA ID in ITS). They're
flagged `"conditional": true` in the schema; `fill_form` **skips** a conditional
field that isn't actionable rather than failing the whole run. The next walk
should pin the correct ordering (enter the ID first so gender/DOB populate).

## LOV (List of Values) — pending

ITS coded fields are a code input (`#oapCitzCode`) + a `<id>_desc` description +
a **search popup**. The popup's trigger id and modal structure aren't captured
yet, so `select_from_lov()` currently raises `PortalChangedError` and `fill_form`
surfaces it. LOV fields: `citizenship_code`, `postal_code` (Page A), plus
endorsement / school / faculty / programme / year / mode (later pages).

## Not done yet (next iterations)
- **LOV** trigger ids + modal flow → wire `select_from_lov`.
- **Pages B–G** (Next of Kin + Account, Matric + subjects loop, Previous
  Studies, Qualifications, Check, Agreement) — ids + the **Save and Continue**
  (`#oapNextBtn2`, …) page transitions, and the repeating Add-Subject rows.
- **Submit page (G)** ids: PIN field, I Accept, Submit Application (never Quit).
- **verify_submission** success marker (no fake submissions — pin during the one
  supervised live submit).
- **End-to-end wiring** (plan Task 4): replace the Phase 2 `process_application`
  stub, persist `SubmissionResult` → `application_jobs`, screenshot upload to
  Storage, the `field_mappings` table (Partner-A decision I'm taking: a separate
  table), and the `POST /applications/{id}/retry` endpoint.

## Tests
`tests/test_uj_adapter.py` (15) drives a faked `Page`: identity/schema shape,
each id helper, the gate login sequence, submit (PIN required; never Quit),
upload no-op, fill_form dispatch, skip-without-selector, conditional-skip, and
LOV-not-wired. No real browser. Live verification is manual (gated), per the plan.
