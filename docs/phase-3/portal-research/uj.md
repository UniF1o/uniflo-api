# UJ — Portal Research

> **Status: Draft v2 — verified from screen recording.** Rebuilt from `uj.mp4` (14:34) frame-by-frame, not just dictation. Field labels, control types, required flags, dropdown/LOV option lists, the page order, and the review/agreement pages are now confirmed from video. **Not** in the video: the applicant-type choice + login screen (recording starts already logged in — taken from dictation) and the post-submit confirmation page (recording ends at the agreement step). Sample data shown in the video is intentionally omitted (PII).
>
> **Drive mechanism: accessibility-tree primary (approach C).** The "Control / target" column names the visible label + control type the agent acts on, not a CSS selector.
>
> ⚠️ **Update (2026-06-05, from building the adapter):** approach C **does not work on this ITS portal** — its inputs have **no accessible names**, so the adapter targets by **stable element id** (`#oapSurname`, `#oapTitle`, `#oapNextBtn1`, …) instead. The labels below are still correct for AI mapping; the live-verified element ids live in `app/automation/adapters/uj.fields.json`. See `docs/phase-3/task-4-adapter-uj.md`.

## Portal URL
- Login: <https://registration.uj.ac.za/pls/prodi41/gen.gw1pkg.gw1startup?x_processcode=ITS_OAP>
- Page title throughout: **"Comprehensive Web Application Process"**. Engine: **ITS Integrator**.

### ⭐ Interaction pattern — the key automation detail
Almost every coded field is an **ITS "List of Values" (LOV) search popup**, not a native `<select>`:
1. Click the 🔍 (magnifier) next to the field.
2. A modal opens titled **"List of Values: &lt;field&gt;"** with a Search box (defaults to `%`), Search/Close buttons, and a results table.
3. Optionally type a filter (e.g. `%EPP%`) + Search, then **click the matching row** to select.

The adapter should have one generic helper — `select_from_lov(field_label, target_text)` — driven off the **row text** (accessible link/cell), not CSS. Fields using LOV: Citizenship Code, Postal Code, school-leaving endorsement, School Leaving Subject, Grade, Final Gr11 Symbol, school attended, Faculty/College, Programme, Year of study, Mode of study. Plain text / native dropdown / checkbox fields are targeted by their visible label.

## Application window
- Opens: **1 April** · Closes: **31 October @ 12:00**

## Entry points & account model
- **Public landing page:** <https://www.uj.ac.za/admission-aid/new/> ("Undergraduate"). Not part of the automated flow, but it's where the **New Applicant** vs **Returning/Internal** choice actually lives — two separate "Apply Here" buttons:
  - **New Applicant** → the portal entry URL above (`gw1startup?x_processcode=ITS_OAP`).
  - **Returning OR Internal Applicant (existing UJ student number)** → a login page (`w99pkg.mi_login`).
  - → The dictation's "new / returning / internal" choice is **this page's buttons**, not an in-portal dropdown.
  - Useful rules stated here: applying online is **free**; **two study choices** per academic year and **no changes once submitted**; pre-application references are the **APS Calculator** (gostudy.net) and the **UJ Undergraduate Prospectus** (PDF) — both feed UJ's portal-side eligibility tagging (see Page E). Window restated as **1 April → 31 October @ 12:00**.
- **No separate login for new applicants.** The New-Applicant button goes straight to the entry/POPI gate (Page 0), then into the biographical form. UJ issues the **student number** and the applicant sets a **5-digit PIN** only at the end (see Page G). Test-account credentials live in **Bitwarden** per Phase 3 plan §3 — _TBD: link entry._

## Anti-automation measures ✅
- **None observed across the entire 14-minute recording — no captcha, no OTP, no image challenge.** The entry/POPI gate is likewise captcha-free (re-checked live, 2026-06-03). Confirms UJ as the strongest **first-adapter** candidate (Task 4).

## Page flow
Breadcrumb ("Quick Link") builds up as: **Biographical → Next of Kin → Matric → Previous Studies → Qualifications → (Check application details) → Accept Agreement (Submit).** Each data page ends with **Back / Save and Continue**.

---

### Page 0 — Entry / POPI gate (verified live, 2026-06-03)
The New-Applicant URL lands on a short gate page (heading "Comprehensive Web Application Process" → "Academic Application Process"). Fields appear progressively as each is answered:

| Field (label) | Control | Req | Options / behaviour | Notes |
|---|---|---|---|---|
| Do you already have a student number? | dropdown | * | --- Please select --- / Yes / No | New applicants → **No**. ("Yes" is the existing-student route — handled via the `w99pkg.mi_login` page, not here.) |
| Are you returning to finalise an incomplete application? | dropdown | * | Yes / No | Revealed after Q1. New application → **No**; "Yes" resumes a saved application. |
| Enter qualification token (if applicable)? | dropdown | * | No (default) / Yes | Leave **No** for the standard undergraduate flow. |
| POPI Act acceptance | **Download Rules** link + two checkboxes | * | **Download Rules** → `/itsdocs/UJ_POPI_Act.pdf`; tick **I Accept** or **I do not Accept** | **Next stays disabled until "I Accept" is ticked.** |

- **Next** (enabled only after I Accept) proceeds into the biographical form (Page A). _Stopped at the gate on the live walk — did not submit — so the exact transition into Page A isn't re-screenshotted, but there is no login step in between for new applicants._
- **POPI is gated up-front**, separate from the final Application Agreement (Page G). So a UJ application has **two consent surfaces** to relay to the student: the POPI Act PDF here and the Application Agreement PDF at submit.
- Screenshots (live, 2026-06-03): [`entry-1-student-number.png`](screenshots/uj/entry-1-student-number.png) (first dropdown) · [`entry-2-popi-gate.png`](screenshots/uj/entry-2-popi-gate.png) (all three dropdowns + POPI accept + the disabled **Next**). These are the only visual record of the entry gate — it isn't in the video.

---

### Page A — Biographical details
One page, six sections. (`*` = required, i.e. red asterisk in the UI.)

| Field (label) | Control / target | Req | Options / validation | Uniflo mapping |
|---|---|---|---|---|
| **Nationality** | | | | |
| Are you a SA Citizen in possession of a valid SA ID/Birth Certificate? | dropdown | * | Yes / No | citizenship |
| ID Number | text | * | Hint: UJ-student-number holders enter ID then click "CLICK HERE" in the pop-up | national ID |
| Citizenship Code | LOV search | * | e.g. "South Africa" | citizenship / country |
| **Personal Information** | | | | |
| Date of birth (DD-MON-YYYY) | text + calendar | * | Format `DD-MON-YYYY`; validates ("Invalid Date of Birth" on a future/invalid date) | DOB |
| Title | dropdown | * | MR, … | title |
| Initials | text | * | | initials |
| Surname | text | * | | last name |
| First names | text | * | | first names |
| Maiden name | text | optional | "surname prior to marriage…" | maiden name |
| Marital status | dropdown | * | | marital status |
| Home language | dropdown | * | Large list: AFRIKAANS/ENGLISH, ENGLISH, NDEBELE, NORTHERN SOTHO, NAMA, FRENCH, GERMAN, HINDI, … | home language |
| Ethnic group | dropdown | * | AFRICAN, … | population group |
| **Address Information** (note: international applicants search "INTERNATIONAL" as the postal code) | | | | |
| Street Address Line 1 (e.g. Street Name) | text | * | | address line 1 |
| Street Address Line 2 (e.g. Suburb Name) | text | * | | suburb |
| Street Address Line 3 (e.g. Town Name) | text | **optional** | (no asterisk — corrects the dictation) | town/city |
| Street Address Line 4 (e.g. Province Name) | text | **optional** | (no asterisk) | province |
| Postal Code | code box + LOV search | * | LOV "Postal Codes" returns code + description (e.g. code ↔ area). **Searched, not typed.** | postal code |
| Tick if Postal Address differs from Street Address | checkbox | — | reveals separate postal address | — |
| **Contact Information** (hints: SA cell = 10 digits; international = 13 digits; all official comms by email) | | | | |
| Do you have a South African Cell Phone Number? | dropdown | * | Yes / No | — |
| South African Cell Phone Number | text | * | 10 digits | phone |
| Work Telephone Number | text | optional | | — |
| Home Telephone Number | text | optional | | — |
| Email | text | * | | email |
| Verify email | text | * | must match Email | email |
| **Residence Information** | | | | |
| Do you want to apply for residence? | dropdown | * | Yes / No | app: residence interest |
| **Disability Information** | | | | |
| Do you have a disability or impairment? | checkbox | optional | if ticked → disability LOV + remarks (per dictation) | app: disability + remarks |

### Page B — Next of Kin (+ Account Contact)
| Field | Control | Req | Notes | Uniflo mapping |
|---|---|---|---|---|
| Next of kin's name(s) | text | * | | NOK name |
| Next of kin's mobile/cellular phone number | text | * | | NOK phone |
| **Account Contact** — "person responsible for any payments… can be yourself or any other party" | | | | |
| Account Contact's name(s) | text | * | | payer name |
| Postal address Line 1 (e.g. Street Name and Number) | text | * | | payer address 1 |
| Postal address Line 2 (e.g. Suburb Name) | text | * | | payer suburb |
| Postal address Line 3 (e.g. Town Name) | text | optional | | payer town |
| Postal address Line 4 (e.g. Province Name) | text | optional | | payer province |
| Postal Code | code + LOV search | * | | payer postal code |
| Email address | text | * | | payer email |

→ **App gap (confirmed on video): no "same as student" option for the payer address — UJ requires the payer's full address + email re-entered.**

### Page C — Matric / Results Details
| Field | Control | Req | Options / validation | Uniflo mapping |
|---|---|---|---|---|
| Matric/Grade 12 Year (YYYY) | text | * | | matric year |
| Are you applying for Undergraduate or Post-graduate? | dropdown | * | Undergraduate / Post-graduate | — |
| Are you Upgrading your Gr 12 Results? | dropdown | * | Yes / No | — |
| Are you completing or have completed a SA or International Matric | dropdown | * | SA Matric / International | — |
| Indicate your endorsement from your school leaving certificate | LOV search | * | e.g. "CURRENTLY IN GR.12" | app: current status |

**Subject details** — enter one subject, click **Add Subject**, repeat; rows accumulate in a table.
| Field | Control | Req | Options | Uniflo mapping |
|---|---|---|---|---|
| School Leaving Subject | LOV search | * | Large subject list, each tagged with qualifier `(NSC / NCV / ISC / DR)` — e.g. MATHEMATICS (NSC/NCV/ISC), LIFE ORIENTATION (NSC/NCV/DR) | academic_records: subject |
| Grade | LOV search | * | NSC (for SA matric) | qualification type |
| Final Gr11 Symbol | LOV search | * | **Values are percentages (66–99), despite "Symbol" label** | grade-11 mark |

Subjects table columns: Matric Year · Matric Date · Examination Number · Final School Leaving Certificate · School Leaving Subject · Grade · Final Gr11 Perc · Final Gr11 Symbol · Mid Year Gr12 Perc · Mid Year Gr12 Symbol · Final Gr12 Percentage · Final Gr12 Symbol · Remove. (For a current Gr12 applicant only the Gr11 mark is entered now; the Gr12 columns exist for later result updates.)

### Page D — Previous Studies / Educational Institutions
| Field | Control | Req | Notes | Uniflo mapping |
|---|---|---|---|---|
| Which school did you attend last | LOV search | * | "School Attend Codes" (search e.g. `%EPP%`) | school |
| What are you currently doing? | LOV/dropdown _TBD_ | * | e.g. "GRADE 12 PUPIL" | app: current activity |
| Have you studied at Another institution previously? | choice | * | No (for matriculants) | — |

### Page E — Qualifications
Context blocks shown: Curricular Course (UG full-time on-campus + APS-calculator link) · Non-Subsidised/Continuing Education (NSP/CEP) · Short Learning Programmes (SLP).
| Field | Control | Req | Options / notes | Uniflo mapping |
|---|---|---|---|---|
| Academic Year | dropdown | * | The intake year (video showed 2027) | application year |
| Are you applying for: | dropdown | * | Curricular Courses / NSP / CEP / SLP | — |
| Limit your selection to a specific Faculty / College | LOV search | * | e.g. ENGINEERING&BUILT ENVIRONMENT, FACULTY OF SCIENCE | faculty |
| Choose a programme | LOV search (code + description) | * | Entries pre-tagged **"(ELIGIBLE TO APPLY-Y)"** — UJ precomputes eligibility from the captured marks | programme |
| For which year of study are you applying? | LOV search | * | FIRST / SECOND / THIRD YEAR | year of study |
| How would you like to study for this programme? | LOV search | * | mode/campus, e.g. DFC FULL-TIME, APK CAMPUS FULL-TIME | mode of study |
| Application Type and Description | auto | — | e.g. "U — SA Undergrad Applicant currently in Gr12" | — |
| Number of applications allowed for this Application type | auto | — | **2** → UJ allows **two programme choices** | — |

- **Add Qualification** adds the 2nd choice. (Dictation warns it may wipe/reset the in-progress selection — _verify_; the video's summary shows two qualifications accepted.)
- **Eligibility is portal-computed** ("Eligible To Apply: YES"). The adapter/AI must not submit an ineligible programme.

### Page F — Check your application details (summary)
Read-only review of everything captured: personal/contact, subjects table, previous studies, and a Qualification table (Faculty · Qualification · Study Period · Mode of Study · Academic Period · Academic Year · Application Type · **Eligible To Apply**). Buttons: **Continue** / Printer Friendly Format.

### Page G — Rules and Agreement (Accept Agreement → Submit)
| Field | Control | Req | Validation | Uniflo mapping |
|---|---|---|---|---|
| Login Pin Number | text | * | **5-digit PIN: numeric only · cannot start with 0 · no repeating characters** | store as portal secret (not profile) |

- Agreement shown as an embedded PDF (**`Web_Application_Agreement.pdf`**, titled "APPLICATION AGREEMENT") with **I Accept** / **I do not Accept** checkboxes — must tick **I Accept**.
- Buttons: **Back** · **Submit Application** · **Quit Application**. **Submit Application stays disabled until the PIN is entered and I Accept is ticked.**
- **Quit Application deletes all captured information** — never click it in automation.
- Note: the test PIN `12123` was accepted, so "no repeating characters" appears to mean **no consecutive identical digits** (e.g. `11`), not globally-unique digits. **[VERIFY]**
- **Consent handling (decision 2026-06-03): surface both consent surfaces to the student** — the POPI Act PDF at the entry gate (Page 0) and this Application Agreement PDF — and record explicit acceptance before the bot ticks **I Accept** / clicks **Submit Application**.

## Submission confirmation
- Sequence: Page F summary → **Continue** → Page G agreement (enter 5-digit PIN + tick **I Accept**) → **Submit Application** (agreement screen captured via screenshot).
- Post-submit **success** page (URL + markers): still **[VERIFY]** — the agreement/submit *screen* is captured but not the page shown after clicking Submit Application.

## File uploads
- **None for the initial application — confirmed (2026-06-03).** No document-upload step appears anywhere in the flow (Qualifications → summary → agreement → submit), and ID/results are **not** required to submit the initial application. Any document submission, if needed, happens later/out of band.

## Uniflo mapping & app gaps — schema-checked 2026-06-03
Full schema cross-check + status: **[data-model-gaps.md](data-model-gaps.md)** (gaps now implemented in migration `e7f6a5b4c3d2`). UJ-specific portal fields & where they live:
- **Title, initials, maiden name** — not stored (initials derivable from names).
- **Next of kin** (name, mobile) + **account/fee payer** (name, address, email) — no contacts table; UJ requires the **payer's full address re-entered** (no "same as student").
- **5-digit PIN** — generated at submit; store as a per-applicant **portal secret** (Bitwarden/secrets), not in the profile DB.
- **Residence interest**, **disability + remarks**, **current activity** ("GRADE 12 PUPIL") — not stored.
- **Subject marks** — UJ takes the Gr11 final mark as a **percentage via LOV** (fits `subjects[].mark`); subject names must map to the LOV's `(NSC/NCV/ISC/DR)`-qualified entries (qualifier not stored).
- **Eligibility is portal-side** — feed real marks so the right programmes show "ELIGIBLE TO APPLY-Y"; needs **multi-choice applications** (UJ allows 2; we store one `programme` string).
- **Consent** — POPI (entry) + Agreement (submit) both **surfaced to the student** (decision 2026-06-03).
- Maps cleanly: names, `id_number`, `date_of_birth`, `phone`, street-address block, `postal_code`, `nationality`, `marital_status`, `home_language`, `ethnicity`; school → `academic_records.institution`.

## Screenshots / video — CONSULT BEFORE LIVE-PROBING
- **Committed:** the entry/POPI gate (`screenshots/uj/entry-1-student-number.png`, `entry-2-popi-gate.png`) — captured live, the only record of Page 0.
- **Walkthrough video + frames (local, not committed — too large):**
  `C:\Users\fulum\Videos\Uniflo\uj.mp4` and `…\uj_frames\t_001.jpg …` (≈1 frame/18s).
  Landmarks: subject LOV ≈ `t_034`; **Qualifications page** ≈ `t_041`–`t_044`
  (t_042 = faculty LOV "no data" before *Are you applying for* = Curricular
  Courses; t_043 = faculty `ENGINEERING&BUILT ENVIRONMENT`; t_044 = programme
  `(ELIGIBLE TO APPLY-Y) - B ENG TECH IN ELECTRICAL ENGINEERING`).
  Other portals: `uct.mp4`/`uct_frames`, `up.mp4`/`up_frames`,
  `wits.mp4`/`wits_frames` in the same folder. (The `IMG-…WA00xx.jpg` files there
  are **UCT** phone shots, not UJ.)
- **The dictation** is the appendix at the bottom of this file — read it for page
  ordering/gating the video doesn't show. **Read the frames + dictation before
  reverse-engineering a page live** (saves tokens + avoids PROD footprints).

## Open questions / to verify
- [x] Agreement/submit screen — **captured** (PIN + I Accept/I do not Accept + Submit Application/Quit Application).
- [~] Post-submit **success** page — **on hold (2026-06-03): can't capture without submitting a real application**; confirm at the first live adapter run.
- [x] Document uploads — **confirmed not required for the initial application** (2026-06-03).
- [x] "What are you currently doing?" — **`GRADE 12 PUPIL`** (Page D `#oapPact`, single option), confirmed in the 2026-06-06 test-account walk. "Add Qualification" (`#oapAddQual`) allows a 2nd choice (num allowed = 2); reset behaviour not re-tested.
- [x] **Full A→G flow driven live (verify-only, never submitted) 2026-06-06** with the Jane Doe test account — every page's element ids + LOV mechanics captured; see `docs/phase-3/task-4-adapter-uj.md`.
- [x] Applicant-type + entry/POPI gate first screen — **captured live (2026-06-03)**: see Page 0 (no separate login for new applicants; POPI accept gate up-front; landing-page entry points noted).

---

## Branch mapping (2026-06-27)

> Live-driven via Playwright with the synthetic Jane Doe identity, **never submitted** (UJ assigns no student number and persists nothing server-side until final submit). Entry gate → Page A → Page B → Page C → Page D traversed fresh this session. Bulk option lists for UJ's branch fields were already captured in [`uj-field-options.json`](uj-field-options.json) during the 2026-06-18/19/20 every-option walkthroughs; this section consolidates them into the per-track map and adds the one piece those walkthroughs left open — the **`oapPact` ("What are you currently doing?") options for a non-current-Gr12 applicant** (captured live here).
>
> **Drive method note:** ITS has no accessible names, so everything was driven by element id via `browser_evaluate` (JS `value` + dispatched `change`/`blur`). Key practical tricks, all confirmed live: select **values are codes** not labels (e.g. marital `S`, home-lang `E`, ethnic `24`); postal codes can be JS-set on both the code field **and** its `_desc` sibling to **skip the LOV popup entirely** (Bug 4); the SA-citizen citizenship group must be force-hidden + `oapCitzCode`/`_desc` set (Bug 2); disabled `Save` buttons (`oapNextBtn2`, `oapNextBtn3`) are force-enabled by clearing `disabled` (+ `eval(JSText_46.innerHTML)` for Page C — Bug 1); a LOV's full option list can be fetched directly from `gen.gw1pkg.gw1lovbind` using the `x_lovcode`/`x_chksum` hashes in its `LOVHref_n.href` (no popup needed).

### Applicant-type trigger architecture

UJ spreads the applicant-type branch across **four** fields — three on Page C (Matric/Results) and one on Page D (Previous Studies):

| Field | Page | Control | Role |
|---|---|---|---|
| `oapMatType` "Indicate your endorsement…" | C | LOV | **Primary applicant-type field.** Its option set is **gated by `(oapTypeMatric + oapMatYear)`** — the 18-option list is a superset; the *allowed* subset = function(matric-type, matric-year). |
| `oapStudUpgrade` "Are you upgrading your Gr 12 results?" | C | select Yes/No | Repeating/upgrading flag. |
| `oapTypeMatric` "SA or International Matric" | C | select `I`/`S` | International branch. |
| `oapPact` "What are you currently doing?" | D | LOV | **Gated by applicant type** (the endorsement). Current-Gr12 → one option; completed/past-year → the post-school activity set (captured below). |

**Endorsement (`oapMatType`) gated subsets** (codes = descriptions; full 18-option superset in `uj-field-options.json`):
- **SA, current year** (current Gr12 school-leaver): `10`=CURRENTLY IN GR.12, `VC`=Vocational Certificate.
- **SA, past year** (completed-matric / gap-year / upgrading): `B`=NSC/IEB/SACAI - Degree, `C`=…Certificate, `D`=…Dip/Cert, `BV`/`CV`/`DV`=Vocational admit Degree/Cert/Diploma, `VC`=Vocational Certificate.
- **International**: `CA`=Cambridge, `IB`=International Baccalaureate, `KC`=Kenyan, `CH`=Mozambique/Angolan, `SS`=NSSC (Namibian), `DR`=Republic of Congo Diplôme, `WA`=West Exam Council, `BA`=Gabonese/Congo-Brazzaville, `02`=Other International Matric.

**Mark-column behaviour differs by applicant type** (live-confirmed this session): for **current-Gr12** the visible/required subject mark is the **Final Gr11 symbol** (`oapsymbGr11`); for a **completed-matric** endorsement (`B`), `oapsymbGr11` is hidden and the **Final Gr12 symbol** (`oapsymbGr12_desc`) becomes the visible/required mark. (Upgraders additionally expose the mid-year + final Gr12 columns — `oapStudUpgrade=Yes`.)

### Track: Completed matric (prior year)

**Triggers:** Page C `oapMatYear` = a past year (e.g. 2024) + `oapTypeMatric` = `SA Matric` (`S`) + `oapStudUpgrade` = `No` + `oapMatType` endorsement ∈ {`B`,`C`,`D`,…} (the SA past-year subset).
**Effect:** the endorsement LOV filters to the past-year subset (no `CURRENTLY IN GR.12`); the subject grid requires the **Final Gr12 symbol** instead of the Gr11 symbol. Page D `oapPact` then offers post-school activities (below).
**Screenshots:** `screenshots/uj/branch-completed/` (`pageD-present-activity.png`).

### Track: Repeating / upgrading

**Trigger:** Page C `oapStudUpgrade` = `Yes` (with a past-year `oapMatYear` + SA matric + an endorsement).
**Effect:** flags an upgrade; the matric subject row exposes the hidden Gr12 mark columns (Mid-Year `oapsymbGr12j` and Final `oapsymbGr12`) in addition to the Gr11 symbol. Which columns are *required* is driven mainly by the **endorsement**, not the upgrade flag alone. Toggling the upgrade flag does not delete already-committed subject rows. (Per `uj-field-options.json`, re-confirmed structurally this session.)

### Track: Gap year

**Trigger:** Page D `oapPact` "What are you currently doing?" — available only once the applicant is a non-current-Gr12 type (completed/past-year endorsement on Page C).
**Value:** `09`=UNEMPLOYED (closest "gap year / not studying or working"), or `10`=OTHER.

### Track: Employed

**Trigger:** Page D `oapPact` = `07`=EMPLOYED.

**`oapPact` full option set, live-captured 2026-06-27** (LOV internal title "Activity last year", filter `%`), for a **completed-matric** applicant — supersedes the prior gap which only had the current-Gr12 value:

| Code | Description |
|---|---|
| `01` | UNIVERSITY STUDENT |
| `02` | TEACHER`S TRAINING COLLEGE |
| `03` | TECHNIKON STUDENT |
| `05` | TECHNICAL COLLEGE STUDENT |
| `06` | NATIONAL SERVICE |
| `07` | **EMPLOYED** |
| `09` | **UNEMPLOYED** |
| `10` | OTHER |

(For a **current-Gr12** applicant the same LOV returns only `08`=GRADE 12 PUPIL — confirming `oapPact` is gated by the Page-C applicant type. The tertiary-student codes `01`/`02`/`03`/`05` are the transfer-ish options; out of scope per the hard rule — note only.)

### Track: International applicant

**Two surfaces:**
1. **Page A — citizenship branch — LIVE-VERIFIED 2026-06-28.** Setting `oapCitizenType` = `No` (not an SA citizen) fires `eventRun(5.4)` and, confirmed live:
   - **Reveals** (all `mandatory=Y`, visible): `oapPPnumber` (**Passport Number**, text); `oapStudyPermit` (**Study Permit / visa type** — a native `<select>`, **not** a LOV, 17 options: `AS`=ASYLUM SEEKER PERMIT, `BP`=BUSINESS VISA WITH ENDORSEMENT, `EP`=CRITICAL SKILLS VISA, `DP`=DIPLOMATIC PERMIT, `EX`=EXCHANGE STUDENT, `EL`=EXPERIENTIAL LEARNING, `EC`=EXTRA CURRICULAR, `DE`=LIMITED CONTACT SESSIONS, `NA`=ONLINE PROGRAMME - NOT APPLICABLE, `OT`=OTHER, `PR`=PERMANT RESIDENCE STATUS *(sic)*, `QW`=QOUTA WORK VISA WITH ENDORSEMENT *(sic)*, `RP`=REFUGEES PERMIT, `RE`=RELATIVES VISA WITH ENDORSEMENT, `SP`=STUDY VISA, `VP`=VISITOR\`S VISA, `WE`=WORK VISA WITH ENDORSEMENT); explicit `oapGender` (**F Female / M Male**, since gender isn't derivable from an SA ID); manual `oapBirthdate`.
   - **Hides** `oapIDnumber` (SA ID) and the `oapCitzCode`/`oapCitzCodeGrp` (Citizenship-Code) group.
   - **Adapter implication:** for a non-SA applicant, fill Passport Number + Study Permit type + Gender + DOB; skip the SA-ID/citizenship-code path. Resetting `oapCitizenType` = `Yes` re-reveals the SA-ID block and re-hides the permit/gender block.
   - **Screenshot (local only):** `uj-pageA-citizenship-international.png`.
2. **Page C — matric branch (`oapTypeMatric` International vs SA) — LIVE-RETESTED 2026-06-28, finding corrected.** `oapTypeMatric` is a 3-option native `<select>` (`-1` / `I`=International Matric / `S`=SA Matric); selecting `I` switches the endorsement LOV (`oapMatType`) to the international subset (Cambridge/IB/Kenyan/…). **However, the prior every-option-capture claim that International Matric *reveals* an `Examination Number` field (`oapExamNum`) could NOT be reproduced live.** `oapExamNum` stayed **hidden** (label carries a literal `**hidden**` marker) across every combination tested via headless field-setting: (a) `I` + year 2026; (b) `I` + an international endorsement (`CA`=Cambridge); (c) `S` + a past year 2024 + a completed-matric endorsement (`B`) — even after firing `eventRun(16.999)` explicitly. **Conclusion:** the `oapExamNum` reveal is **not** driven by `oapTypeMatric` (or the endorsement) via JS value-setting + synthetic events — it depends on the **authentic ITS LOV PassBack/onchange chain** (a genuine endorsement-LOV row-click that runs the server-side `resetDependant`/`callDynBGproc`), which headless value-setting does not trigger. **Adapter implication:** to surface `oapExamNum` (and other endorsement-dependent reveals), the adapter must perform a real LOV selection on `oapMatType`, not a JS set; do not assume `oapTypeMatric=I` alone exposes the exam-number field.

### Session notes / state left behind (2026-06-27 / 2026-06-28)

- **No submission.** Reached Page D (`ITS_OAP04`) and stopped; never entered Page E/F/G or clicked Submit. UJ issues no student number and saves nothing between sessions, so the abandoned application leaves no recoverable record (consistent with the account model — there is no parked UJ account).
- Synthetic Page A/B data used placeholder address/contact values (Braamfontein / 2000 / `082…` / `john.payer@gmail.com`); only Jane's identity fields (name, ID `0805140001084`, DOB, email) are the canonical synthetic identity.
- **2026-06-28 follow-up run** (to finish the two items the 2026-06-27 pass left documented-but-unverified): a fresh entry-gate→A→B→C traversal that (1) **live-verified the Page A `oapCitizenType=No` international reveal** (passport / study-permit `<select>` / gender; SA-ID + citizenship-code hidden) and (2) **retested the Page C International-Matric `oapExamNum` reveal**, which did not reproduce under any International/completed combination via JS-setting — corrected above. Again nothing was submitted.

## Appendix — raw dictated walkthrough
> Original unedited notes, kept as the source for the parts the video doesn't show (login/applicant-type).

So I'm going into u j. There's going to be an option to choose from new applicant, a returning, or internal applicants, people already existing with the u j student number. For us, we're gonna go to new applicants. They are prompted later. They already have a student number. We're gonna click no. Are they referring to finalize an incomplete application for the first part to make it no if for continuing an application, make it yes. So there's a huge apoebi egg that people do have to accept? I don't know. You maybe may have to save the link, send it to the users so they can drink for themselves and then choose to accept. And then the AI can take over from there. no capcha for this one So now we'll move on to biographical details. As for nationality, whether you're a basic citizen or not, as for your ID number, citizenship code, it's going to be a search. So click the search button, and then just select South Africa. Your date of birth, you are going to have to click the button for date of birth and to actually choose the date of birth. Then you input your title, your initials, surname, and first names. maiden name too if applicable and maritial status. input in home language too. ethnic group too You just have to put in your skin and dress so they do give you some guidelines. Address line one, pick your social street name. Address line two, your suburb. Line three should be your town name, and line four should be your province. for postal code you do not type it in, you click the button that looks like search and search for it there We then move on to contact information where they ask you for your South African cell phone number. Um, your work phone... cell phone number optionally, and your home telephone number optionally. Then you have to put in your email address and then verify it by inputting it again.

Residents information, they ask you to choose if you want to apply for residence or not. Then there's also disability information. We have to tick whether or not you have a disability. And then much like we have been doing with this system, there's going to be a button that is like a search. We're gonna definitely look for whatever disability the person has and any remarks. The remarks here are not compulsory, but would be good to include. after this press save and continue

We now move on to the next of kin details, where they ask for the name of next of kin and then the next of kin's phone number. Account details, you're gonna enter the account, the name of the person who is responsible for making payments. So we're gonna use the information of the guardian, whatever guardian there is. So you're gonna put in the contact name, and then UJ requires you to write down the address information again. There's no option to just make it the same as the student applying. address in entered the same way as before. and also include email address of account payer. then press save and continue

next step is results details. input in your matric year and there will be a drop down wanting u to specify whether u are applying for post grad or under grad. After specifying that you are of undergrad, you're gonna be asked whether or not you are upgrading your credit or results, whether or not you have completed South African or international metric for most people with doing now will be South African. And then you're gonna be asked, most of this have been a drop down. Now much like you, Jay's infrastructure, there is going to be that button that will take a search button, which is essentially what you're gonna use to do for a majority of the things we'll be doing here. So indicate your endorsement from your school leave certificate. You're gonna put in... choose the currently in grade twelve. And then for school subjects, basically, everything is done the same way where with each subject, you click the search button thing to choose the school leaving subject. You choose the search button thing for the grade, which is will be NSC. then the final to eleven symbol, which you'll have to choose there. For the mark, you actually got. after all entered, press save and continue

The next step would be educational institutions and ask for school details, which school did you last attend, and what are you going to be doing? There'll also be a search button here to click. So for the first one, you're gonna search out whatever school the student put in. The second one, they could just specify that they are grade twelve people. Something else asked is if they've attended any other institution previously, which should be no because why they are high school students. going on to next section

The next section will ask you for your academic year that you wish to apply for. When I applied, the focus I have a bachelor's degree from short courses to extra long courses, the ones that most will be applying for will be curricular courses. And then you're gonna be asked for the specific faculty. So for you, Jay, just click the search button, and then have it there. And then you're gonna choose your program for which of study I applied. For most people, it would be first year. You're gonna click that option. After clicking Witcher of Study, how did you register for this program, and when would you like to study? You'll be automatically selected for you. You cannot lick add qualification into this another thing they wanna study for after the add qualification button, everything will just be wiped and they can reselect things for a different qualification. After going to the summary and accepting everything, you're gonna have to create a five digit PIN that can only consist of numerical values. You cannot start with a zero, and you cannot have repeating characters. after that you will accept the agreement. since this is another part that students have to see the agreement we can implement something for that
