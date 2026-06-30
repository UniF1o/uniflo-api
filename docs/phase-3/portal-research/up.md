# UP — Portal Research

> **Status: v3 — LIVE-VERIFIED (2026-06-11).** Full no-pay/no-apply walkthrough on the live portal with the synthetic Jane Doe applicant (Application ID `T3989883`): new-application form + captcha, emailed Application-ID login, password change, every section filled, **Verify passed ("No errors")**, stopped at Payment (Not Paid). See **Live spike findings** below for element ids and verified behaviours. Still not captured: the page after clicking "Apply" (needs a real submission) and the third-party card-payment gateway.
>
> Previous: Draft v2 rebuilt from `up.mp4` (20:39) frame-by-frame. Sample data shown in the video is intentionally omitted (PII).
>
> **Drive mechanism: accessibility-tree primary (approach C).** "Control / target" names the visible label + control type, not a CSS selector.

## Portal URL
- Login / apply: `upnet.up.ac.za/psc/upapply/EMPLOYEE/SA/c/UP_OAP_MENU.UP_OAP_LOGIN_FL.GBL`
- Engine: **PeopleSoft-based UP Online Application Portal (OAP)** (`UP_UG_MENU` / `UP_OAP`). Left-nav with named sections; a per-page toolbar of icons (first / prev / next / **save** / email / help / cancel). Header on every page: *Name (Application ID) · 2027 Undergraduate · Overall Application Status: Must still verify & apply*.

### Interaction pattern (for the adapter — approach C)
Mostly **native `<select>` dropdowns** (target by label). Several modal/search pickers:
- **Select Postcode** modal (Contact Details): type city/suburb/postcode → Search → results grid (name · town · postcode · province · Street Code) → **Select** row.
- **Select school** modal (Secondary Education): type school → search; or **"Enter School Manually"** link. (Shows "No matches have been found" if absent.)
- **Select your study choice** modal: "Open Plans only?" toggle + Study programme keyword → Search → results grid (programme name · code · Open) → click row. **Row is unselectable if its closing date has passed.**
- **Disability Detail** modal: Category → Type → Require assistance? → Done.
- **File Attachment** modal (Documentation/Payment): My Device → file → Uploading… → Upload Complete → Done.

## Application window
- **Corrected 2026-06-10 (verified on up.ac.za/online-application/important-dates):** opens 1 April 2026; closes **31 May 2026 for Veterinary Science only**; **all other undergraduate programmes close 30 June 2026**. (The earlier "closes 31 May" note over-generalised the Vet Science date.) Video applied for the **2027** intake.

## Account / login
- Credentials live in **Bitwarden** per Phase 3 plan §3 — _TBD: link entry._
- UP **emails a system-generated Application ID + password** after the first form; applicant then confirms email + sets a new password.

## Anti-automation measures ⚠️
- **Security Code (case-sensitive 6-char image captcha)** on the new-application form. **LIVE FINDING (2026-06-11): trivially solvable from the DOM — no vision needed.** The captcha is six separate `<img>` tags whose **filenames encode the characters**: `UP_L_R_1.JPG` = lowercase `r`, i.e. `/cs/upapply/cache/UP_{case}_{char}_{seq}.JPG` (`L` = lowercase observed; presume `U`/digit variants for upper/numerals — the video showed `g6bzyh` mixing digits). Adapter: read the six `src` values in order and type the decoded string; keep the vision solver (`app/automation/captcha.py`) as fallback if UP ever switches to a real image.
- **Email delivery of Application ID + password** — automation needs inbox access (EmailChallengeSource with `expected_fields=("application_id","password")`).
- A **Data privacy notice modal** (ptModFrame iframe, OK button) now precedes the new-application form (not in the 2026-06-02 video). Notes under-18s need parent/guardian permission — relevant for matric applicants.
- No other captcha in the application steps.

## Pre-application: new application → emailed login → set password
1. **"I want to"** dropdown → **start new application**.
2. **New study application:** Career of Study (Undergraduate) · First Year of Study (dropdown, 2027) · Student Number (if previously studied at UP — blank) · Last Name · First Name · Middle Name(s) · Email Address · Confirm Email Address · Date of Birth (date picker, `mm/dd/yyyy`) · **Identify me by** (dropdown: SA ID Number / Passport Number) → reveals **South African National ID** field · **Security Code (case sensitive)** image. → submit; login details emailed.
3. **"I want to"** → **login to continue / view study application** → Application ID (e.g. `T…`) + Password.
4. **Confirm email and change password** modal: Email · Application ID (read-only) · Password (supplied) · New Password · Confirm New Password → **OK**.

## Page flow — 12 sections
Personal Information → Contact Details → Demographic Details → Tertiary Education → Secondary Education → Study Choice → General Details → Documentation → Declaration → Verify → Payment → Apply.

## Form fields

### Personal Information
Title · Preferred first name (→ **app gap**) · Citizenship (SA citizen) · SA National ID. _(Detail per dictation; not all shown on video.)_

### Contact Details
| Field | Control | Req | Notes | Uniflo mapping |
|---|---|---|---|---|
| Country | dropdown | * | South Africa | country |
| Address Line 1 | text | * | | address line 1 |
| Address Line 2–4 | text | _TBD_ | (likely optional) **[VERIFY]** | address lines 2–4 |
| City / Suburb | **Select Postcode modal** | * | search → grid (name·town·postcode·province·Street Code) → Select; auto-fills Postal Code + Province | city/suburb |
| Postal Code | auto | * | from postcode lookup | postal code |
| Province / State | auto | * | from postcode lookup | province |
| Mobile Number | text | * | | phone |

### Demographic Details
| Field | Control | Options | Uniflo mapping |
|---|---|---|---|
| Gender | dropdown | Male / Female **[VERIFY restricted set]** | gender |
| Home Language | dropdown | (Setswana, …) | home language |
| Population Group | dropdown | (African, …) | population group |
| Tell us more | dropdown | "I am currently still in high school" / … | app: current status |
| Do you have a disability? | toggle | No / Yes | disability |
| ↳ Disability Detail (modal) | Category + Type + Require assistance? | Category: Hearing / Medical / Neurodevelopmental / Neurological / Physical / Psychological-Psychiatric / Visual Disability (Type depends on category, e.g. Neurological → Epilepsy / Traumatic Brain Injury) | **app gap: disability + required assistance** |

### Tertiary Education
"Were you prev enrolled at a University, a Univ of Technology or a Post School Technical College?" — dropdown **No / Yes** (No for matriculants; falsely answering No → admission cancelled).

### Secondary Education
| Field | Control | Notes | Uniflo mapping |
|---|---|---|---|
| Final School Year | dropdown | (e.g. 2026) | matric year |
| Examining Authority | dropdown | Limpopo DoE, … | — |
| School Name | search ("Select school" modal) | or "Enter School Manually" | school |
| School Grades Type | dropdown | Nat Senior Cert or IEB | — |
| Highest grade completed | dropdown | Grade 11 (for current matric) | — |
| Examination Number | text | | exam number |
| Exemption Type | dropdown | Currently busy with schooling | — |

**Completed School Grades** — ⚠️ *"IMPORTANT: Grades must be entered in the same order as your school report."* (**UP-specific constraint**). Per subject row:
| Column | Control | Notes |
|---|---|---|
| Subject | dropdown (name + **code**) | e.g. `Xitsonga Home Language 13810`, `Accounting 03410`, `English 1st Add Language 01310`, `Physical Science 02610`, `Life Orientation 90510`, `Life Sciences 02710`, `Mathematics 02510`, `Mathematics Paper 3 34310`, … |
| Mark | dropdown | **NSC achievement level 1–7** |
| Percent | dropdown | **actual percentage** |
| − | remove | |

→ store both the **NSC level (1–7)** and the **percentage** per subject; preserve **subject order**.

### Study Choice
First Choice + Second Choice (each via the **Select your study choice** modal: "Open Plans only?" toggle + Study programme keyword → Search → results grid with programme name · code · Open status; e.g. `BEng in Computer Engineering 12136019 Open`, `BEng in Electrical Engineering 12136013 Open`, …).
- ⚠️ **Real-time minimum-admission check:** selecting a programme you don't qualify for pops *"Minimum admissions requirements not met — You do not meet the minimum admission requirements for this study choice"* (links to up.ac.za/programmes). So the entered marks gate which programmes can be chosen — **the AI must pick programmes the student actually qualifies for** (e.g. BEng requires English 65% / Maths 65% / Physical Sciences 65% / APS 33).

### General Details
| Field | Control | Notes |
|---|---|---|
| Do you wish to be considered for a residence place? | dropdown | Yes / No |
| Preferred Residence | dropdown | (e.g. TuksVillage M) |
| Have you / will you apply for NSFAS? | toggle | Yes / No (+ NSFAS Application link) |
| Will you apply for UP Funding? | toggle | Yes / No (+ UP Financial Aid link) |

### Documentation
Two mandatory groups, each with **[+] / [−]** + File Attachment modal (My Device):
- **Mandatory: Identity Document** — SA ID.
- **Mandatory: School Results** — *"upload either your Grade 12 certificate or copy of your Grade 11 final results"* (Grade 11 Results / Gr 12 Results rows).
→ Confirms required uploads: **SA ID + (Grade 11 final results OR Grade 12 certificate)**. (Matriculants → Grade 11 results.)

### Declaration
Accept the declaration. → **Decision (2026-06-03): surface to the student — show the declaration and record explicit acceptance before the bot accepts it.** _(Exact wording not shown on video.)_

### Verify
**Verify application** button — checks every page; lists outstanding items in a *Page · Error Message* table (e.g. "You must upload at least 1 document(s) in the 'Mandatory: Identity Document' group"). Must pass (all sections show a ✓ in the left nav) before completing.

### Payment
- **Amount Due: R300** (non-refundable). Payment Status: Not Paid · Reference · Confirmed Date.
- **UP Bank Account:** Standard Bank · Hatfield Branch (011545) · Swift (international) SBZAZAJJ · Account 012602604.
- **Methods (tabs):** **Online Credit Card Payment** · **Upload My Proof of Payment** ("I have already paid using a different channel… upload my proof of payment") · **Upload My Parent's Payslip**.
- **Online Credit Card Payment:** "Make Online Payment" → transfers to a **third-party payment gateway** → on success a printable **receipt** → click **RETURN** to come back to the application.
- → Payment sits **inside** the flow (before Apply), unlike Wits (post-submission). We don't process payments — relay the R300 + EFT details to the student, or have them pay via card; capture proof-of-payment upload.

### Apply (final submit)
*"Please confirm that you wish to complete your application. Once you apply, further changes are not possible. Your application will first be verified. If errors or omissions are found, you must address them before continuing. If no errors are found, your application will be submitted to the University."* → **Apply** button.

## File uploads
| Field | Required | Notes |
|---|---|---|
| SA Identity Document | yes | "Mandatory: Identity Document" group |
| Grade 11 final results **or** Grade 12 certificate | yes (one of) | "Mandatory: School Results" group |

_TBD: accepted formats + size limits (not stated on the upload modal)._

## Submission confirmation
- Sequence: Verify (all ✓) → Payment → **Apply** → confirm (Apply screen captured via screenshot — "Once you apply, further changes to your application are not possible… your application will be submitted to the University").
- Post-submit **success** page (URL + markers): still **[VERIFY]** — the **Apply** *screen* is captured but not the page shown after clicking Apply. Reliable success signal: the "Overall Application Status" flips from **"Must still verify & apply"**.

## Uniflo mapping & app gaps — schema-checked 2026-06-03
Full schema cross-check + status: **[data-model-gaps.md](data-model-gaps.md)** (gaps now implemented in migration `e7f6a5b4c3d2`). UP-specific portal fields & where they live:
- **Title, preferred first name** — not stored (ask the student for the preferred name).
- **Marks (key gap):** UP wants **NSC level 1–7 AND percentage** per subject, but `subjects[].mark` holds **one int** — extend the subject shape to carry both.
- **Subject order** — UP requires school-report order; `subjects` is a JSONB list, so preserve write order.
- **Disability detail** (category + type + required assistance) — we store a single `disability` enum value.
- **Residence interest** (+ preferred residence) + **funding (NSFAS / UP) intent** — not stored.
- **Exam number** — not stored. **Grade 11 results document** — UP accepts Gr11 results OR Gr12 cert, but `documents` has no Gr11-results type (ID_COPY covers the SA ID).
- **Eligibility enforced at selection** — feed real marks so the AI only picks qualifying programmes; needs **multi-choice applications** (we store one `programme` string).
- **Payment** — R300 inside the flow; card or EFT+proof; relay to student.
- Maps cleanly: names, `id_number`, `date_of_birth`, `phone`, address block, `gender` (Male/Female ✓), `home_language`, population group → `ethnicity`; school → `academic_records.institution`.

## Screenshots
- Frames extracted from `up.mp4` (1 per ~25s) to a local scratch folder — **not committed**. TODO: export key page shots to `screenshots/up/`.

## Open questions / to verify
- [x] Apply (submit) screen + full Payment methods — **captured; live-verified 2026-06-11** (Apply button id `UP_FAE_WRK_APPLY`, enabled even while unpaid — see Live spike findings).
- [~] Post-"Apply" **success** page — **on hold: can't capture without a real submission**; confirm at first live adapter run (use the "Must still verify & apply" status flip meanwhile).
- [x] Address lines 2–4 — **optional (live-verified 2026-06-11**: saved with only Line 1).
- [x] Gender set — **live-verified 2026-06-11: Female / Male / Unspecified-Non-Binary** (wider than our M/F enum; map Unspecified to an explicit ask if we ever store it).
- [x] Captcha — **live-verified 2026-06-11: decodable from the img filenames, no OCR needed** (vision solver kept as fallback). See Anti-automation.
- [ ] Document formats/size limits — upload modal still states none; dummy PDF accepted; probe limits at adapter build if needed.

---

## Live spike findings (2026-06-11)

Full walkthrough on the live portal, synthetic Jane Doe, Application ID `T3989883`, parked at **Payment: Not Paid** (no payment, Apply never clicked). All ids below verified live.

### Engine behaviours (shared with the adapter design)
- Same PeopleSoft AJAX model as Fluid: every `<select>`/switch change posts `submitAction_win0`; handles go stale after each change → re-locate, fill sequentially, re-assert.
- Modals render in `ptModFrame_N` iframes; in-modal buttons are intercepted by the `pt_modalMask` overlay → **JS-click element ids directly** (or call `submitAction_win0(doc.win0, '<ID>')` in the iframe window).
- **Alert dialogs surface in the PARENT document** (`[role=alertdialog]`, OK id `#ICOK`) even when triggered from a modal — and the alert can close the underlying modal, so dismiss then re-open. Stable message codes: `(31200, 8)` postcode >300 matches; `(31100, 501)` minimum admissions not met; `(31100, 388)` Verify passed.
- Toolbar ids (every page): `UP_FAE_WRK_PREV_PB` / `UP_FAE_WRK_NEXT_PB` / `UP_FAE_WRK_SAVE_PB` / `UP_OAP_FL_WRK_APP_EMAIL_BTN` / `UP_FAE_WRK_UP_HELP` / `UP_OAP_WRK_PTGP_EXIT_PB`; nav items get a ✓ "Valid" icon once complete.

### Pre-application (new study application)
- "Data privacy notice" modal first → OK.
- `Career of Study` → cascades `First Year of Study` (sole option **2027** in June 2026). Career options: Distance / Postgraduate / UPOnline PG / UPOnline UG / Undergraduate.
- **Date of Birth is a native `<input type="date">`** (`#UP_OAP_WRK_BIRTHDATE`) — fill ISO `yyyy-mm-dd`, not `mm/dd/yyyy`.
- `Identify me by` = SA ID Number → reveals `South African National ID` input.
- Captcha: imgs decode from filenames (see Anti-automation). Submit = **Go** button; success alert: *"Please login to continue with your application using the details sent to your email address"*.
- Login form: `Application ID` + `Password` + Go. Then **"Confirm email and change password"** modal (ptModFrame): Email prefilled, App ID disabled, old Password prefilled, fill New + Confirm → OK. Lands on `UP_UG_MENU.UP_OAP.GBL?Page=UP_OAP_MAIN_SS&...&EMPLID=T…`.

### Section-by-section (verified ids)
- **Personal Information:** Title (A/Prof…Mx — Miss/Mr etc.), names prefilled from signup, `Preferred First Name`, `Maiden Last Name`, DOB read-only display, Citizenship Status auto **"1. SA Citizen"** + SA ID prefilled (derived from the signup ID).
- **Contact Details:** Country pre-selected South Africa. Address Line 1 only is required (saved with 2–4 empty — resolves the old [VERIFY]). City/Postal/Province inputs **disabled**; the postcode modal is mandatory: button aria "Select City / Postcode", modal input `UP_POSTSRCH_WRK_SEARCH_KEY`, search `UP_POSTSRCH_WRK_SEARCH_BTN`, result rows `SELECT_BTN$n` (suburb · town · postcode · province · Street/Box Code). **"Soshanguve" → ">300 matches, refine" alert; "Soshanguve East" → grid.** Prefer Street Code rows; selection auto-fills city+code+province. `Mobile Number`, `Alternative Number`; Email read-only.
- **Demographic Details:** Gender = **Female / Male / Unspecified-Non-Binary** (3 options — wider than our M/F enum; resolves the old [VERIFY]). Home Language full SA list; Population Group African/Coloured/Indian/White; `Tell us more` 7 options ("I am currently still in high school" for matrics); disability checkbox switch (+ Disability Detail modal, not exercised).
- **Tertiary Education:** one dropdown ("prev enrolled…?") → No.
- **Secondary Education:** cascade `Final School Year` → `Examining Authority` (26 boards) → `School Grades Type` (Nat Senior Cert or IEB | Non-NSC) + `Highest grade completed` (Grade 11/12) → `Exemption Type` (sole option "Currently busy with schooling" for Gr11/2026). School Name input `UP_FAE_STG_SEDH_SCHOOL_NAME` is disabled → search button `UP_FAE_WRK_CHANGE_CODE` → modal `UP_FAE_WRK_SEARCH_KEY` + `UP_FAE_WRK_SEARCH_BTN` + **"Enter School Manually"** link; rows `SELECT_BTN$n` ("Soshanguve" → 4 schools; picked *Soshanguve South Secondary* for cross-portal consistency).
  - **Subjects grid** (12 pre-rendered rows, no add button): subject `SCHOOL_CRSE_NBR$n` (157 options, "Name CODE" e.g. `Mathematics 02510`), NSC level `CRSE_GRADE_INPUT$n` (1–7), then **`CRSE_GRADE_OFF$n` (Percent) appears only after the level is chosen and offers ONLY that level's band** (level 6 → 70–79). So derive level from percent (7=80+, 6=70s, 5=60s, …) and select level before percent. Remove row = `CLEAR_FLDS_PB$n`. Order preserved top-down (school-report order).
- **Study Choice:** first choice opener `UP_FAE_WRK_CHANGE_CODE`, second `UP_FAE_WRK_CHANGE_CODE_ATP`, swap `UP_FAE_WRK_CHANGE_ORDER`, remove `UP_FAE_WRK_REMOVE_ALL_BTN`/`_EE_BTN`. Modal: `UP_FAE_WRK_UP_OPEN_ONLY` checkbox, keyword `UP_FAE_WRK_SEARCH_KEY`, search **`UP_OAP_WRK_SEARCH_BTN`** (different id from school search!), rows `SELECT_BTN$n` (code · career · name · Open · blurb). **Eligibility gate verified live:** selecting 4-yr BEng Civil `12130017` with Jane's marks (APS 34) → alert `(31100, 501)` and the choice is NOT set; 5-yr ENGAGE BEng Civil `12136017` accepted. Chosen codes land in `UP_FAE_WRK_UP_CHOICE1/2` (disabled inputs).
- **General Details:** residence `UP_FAE_STG_GENL_UP_HOUSING_OPT` (No ⇒ no Preferred Residence field), NSFAS `UP_FAE_STG_GENL_UP_NSFAS` (checkbox), UP Funding `UP_FAE_STG_GENL_UP_FIN_AID` (checkbox).
- **Documentation:** fixed row indices, add button `UP_FAE_WRK_FILE_CREATE1_LBL$n`, delete `UP_FAE_WRK_DELETE_BUTTON$n`: 0 SA National ID · 1 Passport · 2 **Grade 11 Results** · 3 Gr 12 Results · 4 Matric Extra Cert · 5 USAf · 6 Gr11 Extra marks · 7 SAT · 8 Certificate of Conduct · 9 Academic Record · 10 Sporting Accomplishments. File Attachment modal: My Device (`#PT_ATTACH_MYDEVICE` / `PT_ATTACH_BUTTON_DEF`) → OS chooser → `#ICUpload` → "Upload Complete" → Done `#ICOK`. Dummy 344-byte PDF accepted.
- **Declaration:** Yes/No switch `UP_FAE_STG_GENL_CONFIRMED`. Full wording captured (surface to the student per the consent decision); key line: *"I acknowledge that I have to click on 'verify' and 'apply' to finalise my application…"* — i.e. the declaration itself is NOT the submit.
- **Verify:** button `UP_FAE_WRK_VERIFY`; pass ⇒ alert `(31100, 388)` *"No errors — …make payment and click the 'Apply' link"*; sections get ✓.
- **Payment (STOPPED HERE):** Amount Due **300.00** (non-refundable), Payment Status **Not Paid**, Reference + Confirmed Date read-only; bank details Standard Bank · Hatfield (011545) · SBZAZAJJ · 012602604; method tabs Online Credit Card Payment / Upload My Proof of Payment / Upload My Parent's Payslip. Not exercised.
- **Apply (scanned read-only, button NOT clicked):** ⚠️ **the page is reachable and the Apply button is ENABLED with Payment still "Not Paid"** — payment does not gate the button client-side, so the adapter's no-submit protection must be on our side (`AUTOMATION_ALLOW_SUBMIT` + never targeting it), not the portal's. Single control: **`UP_FAE_WRK_APPLY`** (anchor button labelled "Apply"). Page text verbatim: *"Please confirm that you wish to complete your application. Once you apply, further changes to your application are not possible. Your application will first be verified. If errors or omissions are found, you must address them before continuing. If no errors are found, your application will be submitted to the University."* The toolbar Next is disabled here (last page); left-nav shows ✓ on everything except Payment. Whether clicking Apply while unpaid errors at the server-side verification pass is unknown — do not test.

### Adapter notes
- Pure approach C is workable for plain fields, but modals/grids want the stable ids above (same conclusion as UCT).
- Login is **two-phase**: (1) create → EmailChallengeSource must deliver `application_id` + `password` from the email; (2) password change on first login → derive the permanent password via `derive_portal_credentials` and store nothing.
- The 12136017/12130017 distinction matters: programme choice must run the eligibility check reactively — catch `(31100, 501)` and fall back to the student's next choice rather than failing the run.

---

## Branch mapping (2026-06-27)

> Live-driven via Playwright on the parked test account (**Application ID `T4005778`** / `JaneDoe@UP2027`, 2027 Undergraduate, parked at Payment with all sections Verified ✓). Re-login uses Application ID + password — **no captcha** on re-login (the captcha is only on new-application creation). Covers all five applicant-type tracks. **Nothing saved, nothing submitted** — every edit was reverted and the parked state confirmed intact (see "state left behind").
>
> **Adapter-safety fact verified live:** UP's OAP holds edits in a **client/component buffer that is NOT committed until the Save button (`UP_FAE_WRK_SAVE_PB`)**. Switching left-nav sections does **not** persist edits — after thrashing the Secondary Education cascade, a fresh reload of the app URL restored the parked header **and all 7 saved subjects**. So the adapter (and this research) can probe fields freely as long as Save is never clicked.

### Applicant-type trigger architecture

UP splits the applicant-type branch across **three** fields on **three** sections:

| Field | Section | Control | Tracks it drives |
|---|---|---|---|
| **"Tell us more"** (`UP_FAE_STG_DEMO_*`, native `<select>`) | Demographic Details | dropdown, 7 options | Repeating, Gap year, Employed (+ the post-school/tertiary types) |
| **Highest grade completed** + **Final School Year** → **Exemption Type** | Secondary Education | cascading `<select>`s | Completed matric (prior year) |
| **Citizenship Status** (`UP_FAE_STG_PERS_UP_SA_CITZ_STAT`) | Personal Information | dropdown | SA Citizen ↔ SA Permanent Resident (the *foreign* branch is gated at signup, not here) |

### Track: Repeating / Gap year / Employed — Demographic "Tell us more"

**Trigger:** Demographic Details → **"Tell us more"** dropdown. Full **7-option list** (exact strings):
1. `I am currently still in high school` — *(the done / current-Gr12 path)*
2. `I am or was a Post School Technical College student`
3. `I am or was a University of Technology student`
4. `I am or was a University student`
5. **`I am repeating school /subjects`** → **Repeating** track
6. **`I am unemployed and haven't studied before at a tertiary institution`** → **Gap year** track
7. **`I am working/employed and haven't studied before at a tertiary institution`** → **Employed** track

**Fields revealed:** **none for any option.** Verified live (selected "repeating" and "employed"): the Demographic page stays Gender / Home Language / Population Group / Tell us more / Disability — no employer, occupation, gap-year-date, or institution sub-fields appear. "Tell us more" is a **flat applicant-type tag**.
**Notes:** options 2–4 are the post-school/tertiary-student types (transfer-ish — out of scope per the hard rule; the actual prior-tertiary detail is captured on the separate **Tertiary Education** section, whose "previously enrolled?" = No for school-leavers). **Adapter implication:** map the student's current activity to one of the 7 strings; there are no follow-on fields to fill on this page.
**Screenshots (local only, not committed):** `up-demographic-tellusmore-base.png`, `up-demographic-repeating.png`.

### Track: Completed matric (prior year) — Secondary Education

**Trigger:** the **Highest grade completed** (`UP_FAE_STG_SEDH_UP_GRADES_TYPE`: Grade 11 / Grade 12) + **Final School Year** (`…_UP_FINAL_SCHL_YEAR`) cascade, which drives the **Exemption Type** (`…_UP_EXEMPT_TYPE`) option set.
**Behaviour (verified live):**
- Current-Gr12 default (Grade 11, Final Year 2026): Exemption Type has the single option **`Currently busy with schooling`**.
- Completed-matric (Highest grade = **Grade 12** + a **past** Final School Year, e.g. 2024): Exemption Type changes to the **three completed-matric exemption levels** — **`Admit to Bachelor's Degree` / `Admit to Certificate Studies` / `Admit to Diploma Studies`**.
**Cascade order (each a server postback that clears the fields below it):** Final School Year → Examining Authority (`…_ORG_GRP_CD`, 26 boards) → School Grades Type (`…_UP_EXEMPT_LEVEL`: Nat Senior Cert or IEB / Non-NSC) → Highest grade → Exemption Type. The adapter must set them **top-down and re-assert** after each postback (changing Final School Year wipes Examining Authority/grade-type/Highest-grade/Exemption).
**Examination Number** (`UP_FAE_STG_SEDH_EXTERNAL_SYSTEM_ID`) is present in both states (not a branch reveal; optional for current-Gr12, relevant once matric is complete).
**Notes:** "Admit to Bachelor's Degree" is the matric-exemption level UP wants for degree applicants — the completed-matric exemption *is* the applicant's NSC pass level. **Adapter implication:** for a completed matriculant, set a past Final School Year + Grade 12 + the correct exemption level, and provide the Examination Number.
**Screenshots (local only):** `up-secondary-grade11-base.png`, `up-secondary-grade12-completed.png`.

### Track: International applicant — split (signup vs in-application)

**In-application (Personal Information → Citizenship Status):** for this account (created with an SA ID) the **Citizenship Status** dropdown offers only **`1. SA Citizen` / `2. SA Permanent Resident`** — there is **no foreign/non-citizen option in-application**. Selecting **`2. SA Permanent Resident`** reveals a **`Country of Citizenship`** dropdown (`UP_FAE_STG_PERS_COUNTRY`) while **keeping** the SA National ID field (a PR holder has an SA ID). Resetting to SA Citizen hides Country and retains the SA ID.
**At signup (the true foreign/passport branch):** the non-SA branch is gated at **account creation** by the **"Identify me by"** choice (`SA ID Number` / **`Passport Number`**) — choosing Passport replaces the South African National ID field with a Passport Number field (per the pre-application capture). A foreign applicant therefore creates the account as a passport-holder; their citizenship is not re-selectable to "foreign" inside the application.
**Adapter implication:** decide SA-ID vs passport **at signup** based on the student's nationality. For SA permanent residents, set Citizenship Status = "SA Permanent Resident" + Country of Citizenship in Personal Information.
**Screenshots (local only):** `up-personal-permanent-resident.png`.

### Session notes / state left behind (2026-06-27)

- **No save, no submit, no payment.** Application `T4005778` remains parked at Payment ("Must still verify & apply"), all sections Verified ✓.
- Every probed field was reverted to its parked value; a fresh reload confirmed the saved state intact (Secondary Education: 2026 / Gauteng DoE / Nat Senior Cert or IEB / Grade 11 / Currently busy with schooling, **7 subjects** — Mathematics, English Home Language, Physical Science, Life Sciences, Life Orientation, Afrikaans 1st Add Language, Geography; Personal Information: SA Citizen + SA ID `0805140001084`).

## Appendix — raw dictated walkthrough
> Original unedited notes, kept as the source for anything the video doesn't show.

First thing that'll happen is she'll be prompted with an I want to, then I'll be a drop down, and we're gonna select a new application. After that, new shows will pop up. We're gonna have to enter career of study and first year of study. These will be drop downs. Currently, you're gonna choose undergraduate, first year of studies can be whatever year we are applying to. Student number, first year applied to a UP is gonna be last blank if they don't have it. Last name, first name, middle names. Then you put in your email address, then you repeat on confirm email address, and then date of birth, which you're gonna click the button to actually select the date of birth. There is a show called Identify Me by: Gonna Choose Between SAID Number or Password Number and then you're gonna put in the actual value in the next step. And then much like the one in UCT, there's going to be a security code put in, and you have to enter it in order to continue. So you have to use computer vision for that for you to see the code, recognize it, and then enter. After that, login details will be sent to the supplied email. You can go back to the i one two, and instead now, we're going to log in to continue or view study application. We're gonna input whatever application ID was sent along with the password that was supplied. After entering all that, you'll be prompted to confirm your email and change your password. So you're gonna put here whatever old positive or supplied, the new positive, and then confirm the new positive and then click okay. Okay. Cool. After all of that, we'll move on to personal information. Let's select the title. We're gonna enter a preferred first name, which we should ask the student for in the app so to make note of that. Citizenship should be a safe citizen, and then African national ID should still be there. previous contact details, gonna put in the address. So countries are drop down address... this address line, one two three four. You only have to fill in address one, I assume. And then for city server, we actually have to click a button to actually search for the city. After a few chews around a city or suburbia, the postal code in the province will automatically be put in for you. You then have to enter your mobile number and an alternative mobile number, if applicable. Email address should already be there from previous steps. Moving on to demographic details, the gender which will be a drop down, home language is also going to be a drop down, population group which is basically just your ethnicity group, and then there's gonna be a tell us more part with a drop down. Options, I'm currently still in a high school. I am or was post school, technical, college student, university of technology student. I am or was a university student. I'm repeating. I am unemployed and haven't studied before at a tertiary institution. I am working and haven't studied before at a tertiary institution. Also be prompted to see if you have a disability or not. If you do, just click the slider and click the plus button to add your disabilities by category, then there'll be a part where they ask you for your required assistance. We should ensure we cover this in good detail in our app so we can map it to the degree required.

Move on to tertiary education. They ask if you were previously enrolled in anything tertiary related. We are going to say no. Why is that? Because you're dealing with high school students. They're gonna move on to secondary education, and they ask for the final school year, which will be a drop down. Examining authority is going to depend on whether student was Options include Limpopo DOE, etcetera. And then gonna be asked for your school name, click the search button, and actually search for it. school grade types, looking for a national senior certificate or IEB. your highest completed grade. If you completed grade twelve, you'll have to put in your examination number. If not, leave it blank. And then on exemption type, you'd say that currently busy with schooling, which will be a drop down option. Here, we're adding in the actual subjects. They specifically say that they must be ordered the same way in which they are in their school report. So maybe we can make that a constraint in the app. it's gonna be a drop down where you choose the subject, drop down for the mark, and then you fill it in the percent. mark is basically the ranking — seven in the South African learning system is usually eighty percent plus. Subject is just a full subject name. Mark refers to those values, and then percent is the actual percentage mark. So you have two choices. The first choice and the second choice. you click search button to actually start viewing the choices they offer. The UP system in the back end will verify whether or not you qualify for the specific qualification you choose using the marks in the previous section. there's an open plant only, so it allows you to sort out programs that are still open or not. Move on to general details, that asks you whether you want to be considered for a residence place. It's a drop down of no and yes, and then preferred residence. And then they ask you if you are going to apply for Nasfas and if you want to apply for UP financial aid. After that, your SAID, and then your grade twelve, grade eleven final results, and grade twelve results. the required are the grade eleven final or the grade twelve certificate, which can only be submitted by people after their final exam. So it's either one of the two and not both. since we dealing with matric students, then you don't have to upload your academic transcript. Additionally, there's also a place to upload your sporting accomplishments if applicable. After that there will be a declaration, and then you can verify your application. Then you can move on to payments. Seeing as how we do not process payments, we have to set up the link up until here so that we can handle the payment, either upload the proof of payment or do an online credit card payment.
