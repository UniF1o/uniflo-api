# Task 4 — UJ adapter (first adapter)

`app/automation/adapters/uj.py` + `uj.fields.json`. UJ (ITS Integrator) is the
simplest target: no captcha, and a new applicant doesn't log in — the entry/POPI
gate leads straight into the form; a student number + 5-digit PIN are issued at
submit.

Status (2026-06-05, verify-only — no submit): **Pages A (Biographical) and B
(Next of Kin + Account) are verified end-to-end — fills + Save advance A→B→C.**
The LOV popup handler is verified (citizenship + postal). **Page C (Matric /
Results) ids harvested** (subject loop pending). Pages D–G + the submit page are
pending the next walk.

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

**Postal-code LOV — solved (2026-06-05).** It *is* populated (all SA codes), but
its result rows are **plain `<a>` with the code as text** (e.g. `0152`) — no
`resetDependant` onclick, unlike the country list. So search the code and click
the row by text (`get_by_role("link", name="0152")`), which `select_from_lov`
already does with `lov_search: true`. Verified: `0152` → `oapStreetAddrPCodeRq_desc`
= "SOSHANGUVE". Town (addr line 3) + province (line 4) are **typed** directly
(the hidden "Find your Town" helper is ignored). Later-page LOVs (endorsement /
school / faculty / programme / year / mode) reuse the same mechanism.

## Page A — SOLVED end-to-end ✅ (2026-06-05)

Filling Page A with the Jane Doe data and clicking **Save and Continue**
(`#oapNextBtn2`) **advances to Page B** — verified live. The earlier blockers all
resolved:
- **DOB** (`#oapBirthdate`) is a **readonly calendar** field — `fill` won't
  stick. `_set_date()` sets the value + fires change/blur via JS (format
  `12-MAR-2008`). With DOB set, the form computes age 18 and the **guardian block
  hides** — the earlier guardian/passport/study-permit errors were a *cascade*
  from the missing DOB + unset citizenship, not separate requirements.
- **Gender** (`#oapGender`) is hidden and **not required** (the server never
  flagged it) — skip it (already `"conditional": true`).
- **Address:** town (line 3 `#oapStreetAddr3`) + province (line 4
  `#oapStreetAddr4`) are **typed**; postal via the LOV search (above).
- The save round-trip preserves values — the earlier "everything empty" was the
  validation re-render before these fixes.

## Page B — SOLVED ✅ (Next of Kin + Account → advances to Page C)

Filled and saved live (`#oapNextBtn2_1`). The catch: the **NOK block needs only
name + mobile** — its address/email fields are *hidden* (not required), matching
the dictation ("name of next of kin and then the phone number"). The **Account
contact (fee payer)** takes the full address: `#oapAcntName`, `#oapAcntMobileNr`
(optional/conditional — saved without it), `#oapAcntPostalAddr1-4` (town/province
typed), `#oapAcntPostalCode` (LOV search → "SOSHANGUVE"), `#oapAcntEmail`. Maps
from the `contacts` table (`next_of_kin`, `fee_payer`). In the schema.

## Page C — harvested (Matric / Results)

Reached after the Page B save. Scalars: `#oapMatYear`, `#oapUGPG`
(Undergraduate/Post-graduate), `#oapStudUpgrade` (Yes/No), `#oapTypeMatric` (SA /
International Matric), `#oapExamNum`. **Subject loop** (the repeating part):
per subject pick `#oapMSubj` (LOV), `#oapMGrade` (LOV → "NSC"), `#oapmarkGr11` +
`#oapsymbGr11` (LOVs) then click **`#oapAddMatric`** (Add Subject); rows
accumulate. Nav `#oapBackBtn3` / `#oapNextBtn3`. The subject loop needs dedicated
adapter logic (iterate `academic_records.subjects`) — **[VERIFY LIVE]**.

## Not done yet (next iterations)
- **Page C subject loop** — dedicated adapter logic to iterate the subjects
  (Subject/Grade/Gr11-mark LOVs + Add Subject), then harvest **Pages D–G**
  (Previous Studies, Qualifications, Check, Agreement) via the same method.
- **Page transitions** — each page's Save button is `#oapNextBtn2`, `#oapNextBtn2_1`, `#oapNextBtn3`, …
- **Submit page (G)** ids: PIN field, I Accept, Submit Application (never Quit).
- **verify_submission** success marker — only on the one real submit (agreed:
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
