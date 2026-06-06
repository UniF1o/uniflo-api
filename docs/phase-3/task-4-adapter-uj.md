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

## LOV (List of Values) — wired ✅ (verified for citizenship)

Each coded field is a **readonly** code input (`#oapCitzCode`) + a `_desc` mirror,
with a sibling anchor `a[href*=<fieldId>]` whose href calls
`runWizardLov('frmOne', '<fieldId>', …)`. That opens a **popup window**
(`…/gen.gw1pkg.gw1lovbind?…&x_item_name=<fieldId>…`) titled "List of Values:
…", containing:
- a filter text box `input[name=x_thefilter]` (default `%`),
- a **Search** button (`Find_OnClick()`),
- result rows as `<a onclick="resetDependant(<fieldId>)…">` links whose text is
  the value; clicking one sets the code + `_desc` and closes the popup.

`select_from_lov()` drives this via `page.expect_popup()`. Short lists (the
country list) load in full → it clicks the row by name directly
(**verified: "South Africa" → `oapCitzCode_desc` = "South Africa"`, 2026-06-05**).
Long lists set `lov_search` in the schema → it filters first.

**Open:** the **postal-code** LOV (`#oapStreetAddrPCodeRq`) — searching the raw
code `"0152"` returned no results, so its filter matches a different column
(area name? code prefix?). Format **[VERIFY LIVE]**. Later-page LOVs (endorsement
/ school / faculty / programme / year / mode) reuse the same mechanism.

## Page A — clean SAVE not yet achieved (next live walk)

Individual fields fill in-page and the citizenship LOV works, but clicking **Save
and Continue** (`#oapNextBtn2`) re-renders Page A with validation errors rather
than advancing — ITS leans on `onchange`/`onblur`/`eventRun` handlers and
conditional show/hide that need the right ordering. Open blockers found
2026-06-05:
- **DOB** (`#oapBirthdate`) is a **calendar-widget** field (readonly text +
  `showCalendar(...)`); `fill` doesn't stick → age unknown → the form then
  demands the **Parent/Guardian** block (`#oapGuardName/Cell/Email` + an under-age
  I-Accept). Need to set the date via the calendar (or a value+event that ITS
  accepts).
- **Gender** (`#oapGender`) is a **hidden** select (not auto-derived from the ID,
  as first assumed) — find what reveals it.
- **Citizenship "Yes"** isn't suppressing the passport / study-permit fields, so
  `oapCitizenType`'s onchange/eventRun conditional isn't firing as the form
  expects — sequence: set citizenship → let it settle → then dependent fields.
- **Postal LOV** filter format (above).
Until Page A saves, pages B–G can't be reached to harvest their ids.

## Not done yet (next iterations)
- **Page A save** — the conditional/event-ordering work above.
- **Pages B–G** (Next of Kin + Account, Matric + subjects loop, Previous
  Studies, Qualifications, Check, Agreement) — ids + the **Save and Continue**
  page transitions and the repeating Add-Subject rows (gated behind Page A save).
- **Submit page (G)** ids: PIN field, I Accept, Submit Application (never Quit).
- **verify_submission** success marker — only on the one real submit (we agreed:
  build/verify up to submit only, never fake-submit).
- **AI mapping integration** — run Jane Doe + the field schema through `AIClient`
  to produce the `FieldMapping` (currently tested with hand-built mappings).
- **End-to-end wiring** (plan Task 4): replace the Phase 2 `process_application`
  stub, persist `SubmissionResult` → `application_jobs`, screenshot upload to
  Storage, the `field_mappings` table (Partner-A decision taken: a separate
  table), and the `POST /applications/{id}/retry` endpoint.

## Tests
`tests/test_uj_adapter.py` (15) drives a faked `Page`: identity/schema shape,
each id helper, the gate login sequence, submit (PIN required; never Quit),
upload no-op, fill_form dispatch, skip-without-selector, conditional-skip, and
LOV-not-wired. No real browser. Live verification is manual (gated), per the plan.
