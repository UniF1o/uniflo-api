# Task 4 — UJ adapter (first adapter)

`app/automation/adapters/uj.py` + `uj.fields.json`. UJ (ITS Integrator) is the
simplest target: no captcha, and a new applicant doesn't log in — the entry/POPI
gate leads straight into the form; a student number + 5-digit PIN are issued at
submit.

> **Before live-probing a page, watch it first.** Walkthrough video + frames:
> `C:\Users\fulum\Videos\Uniflo\uj.mp4` / `uj_frames\` (see this file's
> "Screenshots / video" section in `portal-research/uj.md` for landmark frames),
> plus the dictation appendix there. Going in blind wastes tokens + creates PROD
> footprints.

Status (2026-06-06, verify-only — **never submitted**): **the entire flow A→G is
mapped and driven end-to-end.** Pages A (Biographical), B (Next of Kin +
Account), C (Matric/Results), D (Previous Studies) and E (Qualifications) are
SOLVED — fills + Save advance all the way to **F (summary)** → **G (Rules and
Agreement)**, which was reached and inspected but **not** submitted. `login()` +
`run_application(do_submit=False)` drives the **whole** walk with the real adapter
(live-verified 2026-06-06 — lands on Page G, Submit untouched). The LOV handler is
verified for every list type (citizenship, postal, endorsement, subjects, school,
faculty, programme [code-keyed], study period). Remaining: AI mapping, end-to-end
runtime wiring, and the one real supervised submit.

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
`label` (which drives the AI mapping). Pages A–D selectors + option lists are
verified; pages E–G have `selector: null` until walked. Fields needing
reveal-ordering or loop logic (all of Pages C/D) are flagged `"manual": true` so
the generic `fill_form` skips them — they're driven by the dedicated
`fill_matric_page` / `fill_previous_studies_page` methods instead.

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

## Page C — SOLVED ✅ (Matric / Results → advances to Page D)

Reached after the Page B save. The page reveals its fields **progressively** via
ITS's event model and has one nasty gotcha — all pinned down live 2026-06-06 and
encoded in `fill_matric_page()`:

1. **Matric year first.** `#oapMatYear`'s `onchange="eventRun(5.4,this)"` reveals
   the hidden `#UGDiv` block (everything below). Nothing else is reachable until
   this fires, so the adapter fills it then dispatches change/blur (`_fire`).
2. **UG/PG auto-resolves.** After matric year, the choice control `#oapUGPG`
   **hides** and a UG-only select `#oapUGPGUGOnly` (pre-set to "Undergraduate")
   is shown — drive that one, not `#oapUGPG`.
3. `#oapStudUpgrade` (Yes/No) and `#oapTypeMatric` (SA/International Matric).
4. **Endorsement LOV** `#oapMatType` → "CURRENTLY IN GR.12". This *gates* (reveals)
   the subject-capture LOVs — **and its re-render silently resets `#oapTypeMatric`
   back to the placeholder.** So the adapter **re-asserts matric-type** right
   after the endorsement and again before each Add Subject.
5. **Subject loop** (`add_subject`): per subject pick `#oapMSubj` (LOV; names are
   qualifier-tagged, e.g. `MATHEMATICS (NSC/NCV/ISC)`, `ENGLISH HOME LANG.
   (NSC/NCV)`), `#oapMGrade` (LOV → "NSC"), and `#oapsymbGr11` (LOV → the Gr11
   **percentage** — the "symbol" field actually holds percentages; `#oapmarkGr11`
   is `mandatory=N` and skipped), then click **`#oapAddMatric`**. Rows accumulate.

Verified live: all 7 of Jane Doe's subjects added cleanly (table 1→7) and Save
(`#oapNextBtn3`) advanced to Page D.

## Page D — SOLVED ✅ (Previous Studies → advances to Page E)

`#oapSchool` (LOV — full SA school list, search e.g. "SOSHANGUVE" →
`SOSHANGUVE SECONDARY SCHOOL`), `#oapPact` (present-activity LOV — single option
`GRADE 12 PUPIL`), `#oapPrevQualInd` (select Yes/No — "No" for school leavers).
Nav `#oapBackBtn4` / `#oapNextBtn4`. Encoded in `fill_previous_studies_page()`.

## Page E — SOLVED ✅ (Qualifications → advances to Page F)

Filled live + Saved → Page F (2026-06-06), in `fill_qualifications_page()`. Two
gotchas:
1. **The faculty LOV is empty until the gate is set.** `#oapECSLP` ("Are you
   applying for") must = "Curricular Courses" first — the faculty list's server
   query filters on it (open it earlier and the popup says *"No data could be
   found"*). Then `#oapFaculty` (LOV, e.g. `ENGINEERING&BUILT ENVIRONMENT`)
   populates.
2. **The programme LOV is code-keyed.** `#oapQualification` rows show an opaque
   code (`B6CS0Q`) as the link; the readable name + an `(ELIGIBLE TO APPLY-Y/N)`
   tag live in the description cell. So pick by **row text**
   (`select_from_lov_row`), choosing an `…-Y` (eligible) row — UJ precomputes
   eligibility from the captured marks.

`#oapAcademicYear` (2027), then study period `#oapStudyPeriod` ("FIRST YEAR")
**auto-populates** offering type `#oapOfferingType` ("APK CAMPUS FULL-TIME") +
`#oapBlock` ("YEAR BLOCK"). `#oapApplType/Desc` + `#oapNumAppl` (= 2 choices,
`#oapAddQual` adds the 2nd) are read-only. Save = `#oapNextBtn6`.
**[VERIFY]** in a headless walk `#oapECSLP` rendered hidden and `#oapNextBtn6`
stayed disabled until force-enabled (server then accepted) — re-confirm a real
visible selection fires ITS's enable routine on the live run.

## Page F — mapped (Check / summary)

Read-only summary (title flips to "Wizard application process", `gw1view`-style).
No form controls; an **id-less `Continue`** button (+ "Printer Friendly Format")
advances to Page G — click it by text/role, not id.

## Page G — INSPECTED ✅ (Rules and Agreement) — never submitted

`#oapLoginPin` (create a 5-digit PIN), `#oapAcceptApplRAR` ("I Accept") /
`#oapNotAcceptApplRAR` ("I do not Accept"), `#oapNextBtn8` ("Submit
Application"), `#oapExitBtn8` ("Quit Application" — **never click**, deletes all),
`#oapBackBtn8`. `submit()` now uses these real ids (earlier `#oapAcceptAgreement`
/`#oapSubmitBtn` placeholders were wrong). The page was reached but **Submit was
not clicked** (verify-only).

## Orchestration ✅ (live end-to-end, verify-only)

The runtime (`runtime.py`) calls the five contract steps in order —
`login → fill_form → upload_documents → submit → verify_submission`. Because UJ
is multi-page, **`fill_form` drives the whole walk** after login: `_fill_simple`
Page A → Save (`#oapNextBtn2`) → Page B → Save (`#oapNextBtn2_1`) →
`fill_matric_page` → `#oapNextBtn3` → `fill_previous_studies_page` → `#oapNextBtn4`
→ `fill_qualifications_page` → `#oapNextBtn6` (force-enabled) → F "Continue" →
**Page G**. `fill_form` never submits — the runtime's next step (`submit()`) does
Page G. `run_application(page, mapping, *, do_submit=False)` is a standalone
convenience (`fill_form` + `upload` + optional `submit`/`verify`) for smoke runs;
the runtime uses the individual steps.

**Verified live 2026-06-06** with the real adapter (not the scratch walker) +
Jane Doe data: `login → fill_form → … → gw1view (agreement)`, with `oapLoginPin` /
`oapAcceptApplRAR` / `oapNextBtn8` all present and **Submit not clicked**.
Helpers added: `_fill_simple` (page-scoped generic fill, skips hidden conditional
fields), `_select_label_or_js` (JS fallback for the hidden `#oapECSLP`),
`_save_and_continue` (optional `force` for Page E's disabled Save),
`_continue_summary` (id-less Page-F Continue).

## Runtime wiring ✅ (submit-gated dispatch)

`POST /applications` → `process_application` now routes to the **real runtime**
when `FAKE_AUTOMATION=false` (else the Phase-2 simulation, the dev default):
resolve the adapter by `university_id` (`adapters.get_adapter_for_university`),
build the `FieldMapping` from the profile/contacts/academic-record/application
(`automation.mapping.build_field_mapping`), generate a UJ-valid 5-digit PIN, and
call `runtime.run_job(..., allow_submit=settings.AUTOMATION_ALLOW_SUBMIT)`. The
`SubmissionResult` is persisted to `application_jobs` / `applications` (status +
canonical `last_error`). **Safety gate:** `AUTOMATION_ALLOW_SUBMIT` defaults
**False** → the runtime fills the whole form and stops before Submit
(`RunOutcome.FILLED` → application stays `processing`); it can never submit until
the flag is flipped for the supervised first live run.

## Subject-name resolution ✅ (live-verified)

`app.automation.subjects` resolves a student's free-form subject name to the UJ
LOV entry: it canonicalises both sides to token lists (expanding UJ's
abbreviations — `1ST AD LAN` → first/additional/language, `MATHS` → mathematics —
and dropping the `(NSC/NCV/ISC/DR)` qualifier) and scores candidates, so it
tolerates the portal's spelling. The adapter's `select_subject_from_lov` filters
the LOV by the name's first word, reads the live rows, and clicks the best match
(or raises for review if none is confident — never guesses). **Verified live
2026-06-06:** plain names (`"Mathematics"`, `"Afrikaans First Additional
Language"`, …) all resolved correctly and the run reached Page G.

## Faculty / programme resolution ✅ (live-verified)

`app.automation.adapters.uj_programmes` resolves a free-text
`application.programme` → a UJ faculty + an eligible LOV programme:
`resolve_faculty` keyword-maps to one of the 8 harvested faculties (word-boundary
matches so "ba"/"law" don't fire inside other words); the adapter selects it,
then `select_programme_from_lov` reads the live programme rows
(`CODE (ELIGIBLE TO APPLY-Y/N) - DESCRIPTION`) and `best_programme_match` scores
the request against the **eligible** descriptions — preferring an exact
token-set, then the tightest superset, and **never** an `-N` row (raises for
review instead). **Verified live 2026-06-06:** free-text "Civil Engineering"
(no faculty given) → ENGINEERING&BUILT ENVIRONMENT + the eligible "B ENG IN CIVIL
ENGINEERING", run reached Page G. The mapping is now complete A→E from real
profile data.

## Screenshots → Storage ✅ + retry endpoint ✅

`run_job`'s per-step PNGs are uploaded to the **private** documents bucket under
`automation/<application_id>/<job_id>/NN-step.png` (`app.automation.screenshots`);
the primary (final/failure) one's storage **path** is kept on
`application_jobs.screenshot_url` and minted into a short-lived **signed URL on
read** in the applications service (screenshots show the filled form = PII, so
never public — mirrors the documents pattern). `POST /applications/{id}/retry`
now creates a fresh `ApplicationJob` (preserving the failed one), resets the
application to `pending`, and re-enqueues `process_application`; it 409s a
submitted or in-flight application.

## Consent gate ✅ + PIN persistence ✅

- **PIN** — `derive_portal_pin(application_id)` HMACs the application id with a
  server secret into a UJ-valid 5-digit PIN: deterministic, so retries/resumes
  reuse the same PIN (it's the student's portal login after submit) without
  storing it in the DB.
- **Consent** — `applications.popi_consent_at` / `agreement_consent_at`
  timestamps (migration `f8a7b6c5d4e3`); `POST /applications/{id}/consent`
  records them. The dispatch `_consent_gate` refuses to run (POPI is ticked
  during fill) without POPI consent → job `last_error="consent_required"`, and
  only allows the final submit when the agreement consent is also recorded **and**
  `AUTOMATION_ALLOW_SUBMIT` is on. The adapter still just ticks what it's told —
  the gate lives at the orchestration boundary (adapters never touch the DB).

## Not done yet (next iterations)
- **`field_mappings` table** (Partner-A's review screen reads it).
- **The one real supervised submit** — record consent, flip
  `AUTOMATION_ALLOW_SUBMIT=true`; confirms the Page-E Save-enable without force
  and pins the `verify_submission` success marker.
- **The one real supervised submit** — flip `AUTOMATION_ALLOW_SUBMIT=true` for a
  consenting student; confirms the Page-E Save-enable without force and pins the
  `verify_submission` success marker.
- **Screenshots → Storage** — `run_job` captures per-step PNGs; upload them and
  set `application_jobs.screenshot_url` (currently a TODO in `background.py`).
- **`field_mappings` table** (Partner-A) + the `POST /applications/{id}/retry`
  endpoint (still `501`); persist + reuse the generated PIN as a portal secret.
- **The one real supervised submit** — flip `AUTOMATION_ALLOW_SUBMIT=true` for a
  consenting student; confirms the Page-E Save-enable without force and pins the
  `verify_submission` success marker.
- **AI mapping integration** — run Jane Doe + the field schema through `AIClient`
  to produce the `FieldMapping` (currently tested with hand-built mappings).
- **End-to-end wiring** (plan Task 4): replace the Phase 2 `process_application`
  stub, persist `SubmissionResult` → `application_jobs`, screenshot upload to
  Storage, the `field_mappings` table (Partner-A decision taken: a separate
  table), and the `POST /applications/{id}/retry` endpoint.

## Tests
`tests/test_uj_adapter.py` (29) drives a faked `Page`: identity/schema shape,
each id helper, the gate login sequence, submit (PIN required; real Page-G ids;
never Quit), upload no-op, fill_form dispatch, skip-without-selector, skip-manual,
conditional-skip, the LOV popup (direct + search), the Page-C reveal + subject
loop (`fill_matric_page`/`add_subject`), the Page-D flow
(`fill_previous_studies_page`), the Page-E flow (`fill_qualifications_page` +
the code-keyed `select_from_lov_row`), and the full `run_application` walk
(reaches Page G without submitting; submits only when `do_submit=True`). No real
browser — live verification is manual
(gated), per the plan.
