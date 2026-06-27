# Wits — Portal Research

> **Status: v3 — LIVE-VERIFIED 2026-06-11.** Full walkthrough on the live portal (synthetic Jane Doe, Temporary ID `T1867394`, application instance `UW_OA_UGFT4338265`, parked at **Step 17 — Submit never clicked**). See **Live spike findings** below for verified element ids and behaviour corrections; earlier sections kept as the original video-derived research.
>
> Previously: **Draft v2 — verified from screen recording.** Rebuilt from `wits.mp4` (11:50) frame-by-frame. Temp-ID creation, the security-code captcha, the email-verify + temp-ID login, and all 17 wizard steps are confirmed from video. **Not** captured: the post-submit confirmation page (recording ends at the Step 17 Submit screen). Sample data shown in the video is intentionally omitted (PII).
>
> **Drive mechanism: accessibility-tree primary (approach C).** "Control / target" names the visible label + control type, not a CSS selector.

## Portal URL
- Login / apply: `self-service.wits.ac.za/psc/csprodonl/...VC_OA_LOGIN_FL.GBL`
- Engine: **PeopleSoft Fluid** (same family as UCT/UP). 17-step left-nav wizard; each step has a status (Not Started / Visited / Complete). **Save** · **Next/Previous** · **Validate Application** top-right.

### Interaction pattern (for the adapter — approach C)
Mostly **native `<select>` dropdowns** (target by label). A few modal/link pickers:
- **Select School** → modal: type school name → Search → pick.
- **Address Search** (a link, not a button) on each address: type Suburb → resolves City + Postal Code + Province automatically.
- Subjects are **native dropdown + text mark** rows (10-row tables), not LOV popups.
- **Validate Application** must be run after Study Choices — the first 6 pages must validate before the rest unlock.

## Application window
- **30 June 2026:** Faculty of Health Sciences (all programmes), Bachelor of Architectural Studies, Bachelor of Audiology, Bachelor of Speech-Language Pathology, BA Film & TV.
- **30 September 2026:** all other undergraduate programmes + Residence.
- The video applied for **Academic Year 2027, Undergraduate Full-Time, January** calendar.

## Test account / login
- Credentials live in **Bitwarden** per Phase 3 plan §3 — _TBD: link entry._
- Wits emails a **system-generated Temporary ID + random password**; applicant then sets a permanent password (see flow).

## Anti-automation measures ⚠️
- **Security Code (6-character image captcha)** on the "Create Application ID" page — must read the characters and type them. Requires OCR/vision to solve headlessly. **Kept in MVP (2026-06-03)** — the runtime must ship image OCR; not a drop candidate.
- **Email delivery of Temp ID + temp password** — automation needs inbox access.
- No captcha at the application steps themselves (only at temp-ID creation).

## Pre-application: Create Application ID → verify → login
1. **Create Application ID** page (note: SA Permanent Residents w/o SA ID may complete two of PR Certificate Number / SA National ID / Passport Number; current Matric applicants must attach proof of SA ID application).
   - **National ID:** Nationality (dropdown, default South Africa) · National ID Type (auto "South African ID") · National ID (text).
   - **Applicant Details:** Name Title (dropdown) · First Name* · Middle Name(s) · Surname* · DOB Day (dropdown) · DOB Month (dropdown) · DOB Year (text) · Gender* (dropdown) · Email* · Country Code/Mobile Phone (+27 prefilled + number).
   - **Security Check:** 6-char image → Security Code (text). → **Continue**.
2. **Confirmation of Email** → "an email has been sent … note your Temporary ID" → **OK**.
3. **User Details** (login): Email Address* · Temporary ID · Password (the temp password) → **OK**.
4. **Enter a new password** → Password + Confirm → **OK** → "password successfully changed".
5. Log in → **Apply for Admission**: Application Action (Begin New Application) · Applicant ID (auto, e.g. `T…`) · Application Type (Undergraduate Full-Time) · Academic Year (2027) · Academic Calendar (January) → **Continue**.

## Page flow — Online Application, 17 steps
| # | Step | Notes |
|---|---|---|
| 1 | Welcome | info; 30-min estimate; auto-saves |
| 2 | Personal Details | mostly prefilled |
| 3 | Current Activities | matriculants → School; + sport |
| 4 | Secondary Education | school search + Gr11/Gr12 subjects |
| 5 | Tertiary Education | "No" for matriculants |
| 6 | Study Choices | up to 3 programmes → **Validate** |
| 7 | Domicilium Address | legal-notices address |
| 8 | Residential Address | "same as" option |
| 9 | Postal Address | "same as" option |
| 10 | Contact Details | |
| 11 | Demographic Details | incl. disability toggles |
| 12 | Next of Kin | NOK email/mobile must differ from applicant |
| 13 | Emergency Contact | "same as NOK" option |
| 14 | Indemnity and Undertaking | accept |
| 15 | Payment | R100, **after** submission |
| 16 | Documents | ID + matric cert |
| 17 | Submit | final; no edits after |

> **Step 1 Welcome** notes: details auto-save as you move through; you may log out and resume; "you are encouraged to upload supporting documentation before you submit"; application fee is non-refundable.

## Form fields

### Step 2 — Personal Details
Title (dropdown) · Gender (dropdown) are editable; First/Middle/Last Name, DOB, Country, National ID/Passport are **prefilled read-only** from Create Application ID. Note: name/ID changes require submitting documents to the Student Enrolment Centre after submission.

### Step 3 — Current Activities
| Field | Control | Options | Uniflo mapping |
|---|---|---|---|
| Main Activity During Current Year | dropdown | Currently upgrading matric · Employment Or Occupation · Gap Year · **School** · University | app: current activity |
| Sport | "Add Sport" | optional | app: sport (optional) |

### Step 4 — Secondary Education
| Field | Control | Notes | Uniflo mapping |
|---|---|---|---|
| Secondary education type | radio | South African / International | — |
| Current School Status | radio | Current Grd 12 / Completed Grd 12 OR Upgrading | — |
| School | **Select School** modal | type name → Search → pick | school |
| Examining Authority | dropdown | (province, e.g. Limpopo) | — |
| Examination Year | text | (e.g. 2026) | matric year |
| Examination Month | dropdown | June / November | — |
| Examination Number (if available) | text | | exam number |
| Final Grade 11 Results | 10-row table | Subject (dropdown) + **Mark** (text %) + Clear | academic_records (Gr11 marks) |
| Grade 12 Subjects | 10-row table | **"Copy Grade 11 Subjects"** button; Subject rows | academic_records (Gr12 subjects) |

Subject dropdown is a large native list (Accounting, Mathematics, Mathematical Literacy, Physical Sciences, Life Sciences, Life Orientation, English First Additional Language, Xitsonga Home Language, Mechanical Technology (Auto/F&M/W&M), Marine Sciences, Maritime Economics, Music, Nautical Science, …).

### Step 5 — Tertiary Education
"Do you have any previous or current tertiary studies, including at Wits?" — toggle → **No** for matriculants.

### Step 6 — Study Choices
Up to **3 programmes** (Programme 1 + Programme 2 Optional + Programme 3 Optional). Order doesn't matter; can't repeat a programme code; only open programmes display.
| Field | Control | Notes |
|---|---|---|
| Academic Program | dropdown (code + name) | e.g. `EFA00 - Bachelor of Science in Engineering (Chemical)`, `CBA14 - Bachelor of Commerce (Accounting)`, `LFA14 - Bachelor of Laws (4 Year)`, `MFA00 - Bachelor of Medicine and Bachelor of Surgery`, `ABA00 - Bachelor of Arts`, … |
| Academic Plan | dropdown | auto-derived from the program |
| Mode of Attendance | (auto) | Full-Time |
| Year of Study | (auto) | Year of Study 1 |

→ **Then click "Validate Application"** — the first 6 pages must validate before the remaining steps unlock.

### Steps 7–9 — Addresses
- **Domicilium Address** (legal-notices address): Country (dropdown) · Address Line 1 · Address Line 2 · Suburb + **Address Search** (link) → auto-fills City · Postal Code · Province.
- **Residential** and **Postal** addresses: same pattern, each with a "same as other address" option.

### Step 10 — Contact Details
Email Address (prefilled) · Country Code/Mobile Phone (+27 + number) · Home Phone (optional) · Work Phone (optional).

### Step 11 — Demographic Details
Marital Status (dropdown) · Population Group (dropdown) · Home Language (dropdown — large) · Religious Affiliation (dropdown) · **Do you have a Disability?** (dropdown Yes/No).
- If yes → long list of disability **toggles**: Chronic (Hypertension/Asthma/Cancer/Doctor-Diagnosed/Other Illness) · Blind – No Functional Vision · Temp (Accident or Surgery/Broken bones/Concussions/Whiplash/Back injuries/Other) · Partial Sight (Albinism/Moderate Impair/Blind Right Eye/Blind Left Eye) · Neurodev (ADHD/ADD/Dyslexia/Other Learning) · Psychosocial (Depression/Schizophrenia/Bipolar/Dementia/Anxiety/Other) · Physical (Loss of Limb/Use of Crutches/Wheelchair User/Spinal Cord Injury/Cerebral Palsy/Short Stature/…). → **app gap: detailed disability capture.**

### Step 12 — Next of Kin
Name Title (dropdown) · Initial · Surname · Country Code/Mobile Phone (+27) · Home Phone (optional) · Relationship to Applicant (dropdown) · Email Address (optional).
- **NOK Address:** "Use same address as Applicant" (dropdown, e.g. Domicilium) · else Country + Address Lines + Suburb + Address Search → City/Postal/Province. → **app gap: NOK address.**
- **Validation enforced:** *"Next of Kin Email Address must not be the same as the applicant"* (and the NOK mobile must differ from the applicant's).

### Step 13 — Emergency Contact
"Use same details as Next of Kin" (toggle) · Relationship to Applicant (dropdown: Adult Child, Aunt, Brother, Brother-in-Law, Child, Cousin, Daughter, …, Father, Friend, …) · Contact Name · Country Code/Mobile Phone · Additional Emergency Contact Phone. → **app gap: emergency contact distinct from NOK.**

### Step 14 — Indemnity and Undertaking
Accept the indemnity/undertaking. → **Decision (2026-06-03): surface to the student — show the indemnity and record explicit acceptance before the bot ticks it (don't auto-accept).**

### Step 15 — Payment
- **Application Fee Payable: R100.** Paid **after** the application is submitted and a person/student number is issued. Currently registered Wits students are exempt.
- **Options:** (a) Self-Service Portal → Campus Finances tile → Make a Payment → Application Fee; or (b) **EFT** — Bank: First National Bank · Swift: FIRNZAJJ · Account: 63075484302 · Branch: 251905. Use the person/student number as the Payment Reference; upload proof of payment via the self-service portal.
- → **Key nuance: submission is NOT payment-gated** — the bot can submit, then the student pays afterward. Capture + relay the R100 + EFT details to the student.

### Step 16 — Documents
Upload supporting documents — **Copy of ID Document/Passport** and **Matric Certificate** (per portal note, must be **duly certified, < 3 months old**). _(Upload UI not shown in detail — TBD formats/limits.)_

### Step 17 — Submit
"Your application is complete. Click **Submit Application to the University** to confirm… Once you click Submit, you will be unable to make any further changes. Your application will not be evaluated until you click Submit." → final submit.

## File uploads
| Field | Required | Notes |
|---|---|---|
| ID Document / Passport copy | yes | **certified < 3 months** |
| Matric Certificate | yes* | or grade 11 results if no matric yet |

_TBD: accepted formats + size limits (upload UI not shown in detail)._

## Submission confirmation
- Final step is **Step 17 → "Submit Application to the University"** (confirmed via screenshot — single button, "Please see instructions below"). After submit, no further edits.
- Post-submit **success** page (URL + markers): still **[VERIFY]** — the submit *screen* is captured but not the page shown after the button click. Reliable success signal: submission yields a **person/student number** (used as the payment reference) and the no-further-changes lock.

## Uniflo mapping & app gaps — schema-checked 2026-06-03
Full schema cross-check + status: **[data-model-gaps.md](data-model-gaps.md)** (gaps now implemented in migration `e7f6a5b4c3d2`). Wits-specific portal fields & where they live:
- **Title** — not stored. **Next of kin** (name, mobile, relationship, email, address) + **emergency contact** (distinct from NOK) — no contacts table; Wits **enforces NOK email & mobile ≠ applicant**.
- **Domicilium (legal-notices) address** + a **postal address differing** from residential — we store one address block only.
- **Disability** — Wits wants a detailed toggle list; we store a single `disability` enum value.
- **Current-year activity** (School/Gap Year/Upgrading/Employed/University) + **sport** + **residence interest** + **funding (NSFAS) intent** — not stored.
- **Exam number** — not stored. School → `academic_records.institution`; Gr11 marks → `subjects[].mark`; Gr12 subjects via "Copy Grade 11 Subjects".
- **Indemnity** — consent gate; **surface to the student (decision 2026-06-03)**, don't auto-accept.
- **Payment** — R100, post-submission; not a submission blocker; relay EFT details.
- Maps cleanly: names, `id_number`, `date_of_birth`, `phone`, address block, `gender`, `home_language`, `marital_status`, `ethnicity`; ID + matric uploads → `documents`.

## Screenshots
- Frames extracted from `wits.mp4` (1 per ~16s) to a local scratch folder — **not committed**. TODO: export key page shots to `screenshots/wits/`.

## Open questions / to verify
- [x] Submit screen (Step 17) — **captured** ("Submit Application to the University").
- [~] Post-submit **success** page — **on hold (2026-06-03): can't capture without a real submission**; confirm at first live adapter run (use the issued person/student number meanwhile).
- [~] Document-upload formats + size limits (Step 16) and Steps 8/9 "same as" behaviour — **login-gated; deferred until test-account access** (checked live 2026-06-03: portal returns "not authorized" without a session).
- [x] Indemnity acceptance approach — **decided (2026-06-03): surface to the student, don't auto-accept.**
- [x] Captcha — **kept in MVP (2026-06-03)**; runtime must ship OCR for the 6-char security code (no longer a drop candidate).

---

## Live spike findings (2026-06-11)

Full walkthrough on the live portal, synthetic Jane Doe, Temporary ID `T1867394`, application `UW_OA_UGFT4338265`, **parked at Step 17 (Submit never clicked)**. All ids below verified live.

### Entry + engine
- Entry: `https://www.wits.ac.za/applications/` → redirects to `https://self-service.wits.ac.za/psc/csprodonl/UW_SELF_SERVICE/SA/c/VC_OA_LOGIN_MENU.VC_OA_LOGIN_FL.GBL` (the doc's elided URL resolved — menu is `VC_OA_LOGIN_MENU`, portal `UW_SELF_SERVICE`, instance `csprodonl`).
- The wizard is a PeopleSoft **Activity Guide** (`NUI_FRAMEWORK.PT_AGSTARTPAGE_NUI.GBL`, `TEMPLATE_ID:UW_OA_UGFT`, `INSTANCE_ID:UW_OA_UGFT<digits>` = the application instance). Step pages are inline in the main document (no per-step iframe); modals are `ptModFrame_N` iframes; `[role=alertdialog]` dialogs carry message codes — the shared `fluid.py` patterns all apply.

### Anti-automation — both gates fall
- **Captcha decodes from the DOM, same scheme as UP with a `VC_` prefix**: six `<img alt="Image1..6">` whose filenames spell the answer — `VC_L_Y_1.JPG → y`, `VC_N_7_1.JPG → 7` (`L`=lower, `U`=upper, `N`/digit = verbatim glyph). No vision call needed; solver stays as fallback.
- **Emailed Temporary ID + password**: body markers are literal `TEMPORARY ACCESS ID:`/`PASSWORD:` on their own lines (`T1867394` / `080312`). ⚠️ The temp password was **the applicant's DOB as yymmdd** — DOB-derived, not random. Mail also carries a confirm link to `?Page=VC_OA_PWD_CNFRM_FL`.

### Pre-application (Create Application ID → confirm → login) — ids
- Login page: `VC_OA_LOGIN_WRK_OPRID` / `VC_OA_LOGIN_WRK_PASSWORD` / Login `VC_OA_LOGIN_WRK_VC_LOGIN_PB`; Create Temporary ID `VC_OA_LOGIN_WRK_REGISTER`; Confirm Temporary Password `VC_OA_LOGIN_WRK_VC_CONFIRM_PWD_PB`.
- Create form (all `VC_OA_LOGIN_WRK_*`): Nationality `COUNTRY` (defaults South Africa) · National ID `NATIONAL_ID` · Name Title `NAME_PREFIX` (live list richer than the video: Admiral…Mx…Sister) · First `FIRST_NAME` · Middle `MIDDLE_NAME` · Surname `LAST_NAME` · DOB Day `CUB_BEGINDAY` (zero-padded "12") · DOB Month `MONTH_XLAT` (format **"03 - March"**) · DOB Year `VC_YEAR` · Gender `SEX` (Female / Gender Neutral / Male) · Email `EMAIL_ADDR` · country code `VC_COUNTRY_PHONE` (prefilled +27) + **unlabelled** mobile-number input `VC_PHONE_CELL_SS` · Security Code `VC_SEC_CODE` · Continue `CONTINUE_PB` / Cancel `CANCEL_BTN`.
- **NEW (not in the video): a "Confirm Application Details" review page** sits between the create form and the email — second Continue click required.
- "Confirmation of Email" page → OK → **User Details** (same ids: `EMAIL_ADDR` + `OPRID` + `PASSWORD`, OK = `CONTINUE_PB`) → forced "Enter a new password" (Password + Confirm Password) → "password successfully changed" → OK → login with Temporary ID + new password.
- Apply for Admission (`VC_OA_STD_MENU.VC_OA_APPL_STRT_FL.GBL`): Application Action `VC_OA_APPLY_WRK_VC_OA_APPL_ACTN` (Begin New Application / Continue Existing Application) → Application Type `VC_OA_APPLY_WRK_VC_OA_APP_TYPE` (9 live options; **Undergraduate Full-Time**) → Academic Year `VC_OA_APPLY_WRK_ADMIT_TERM` ("Academic Year 2027" sole option) → Academic Calendar `VC_OA_APPLY_WRK_WITS_ADMISSIONCALE` ("January" sole option) → Continue.

### Wizard mechanics
- Header: Next/Previous `PTGP_GPLT_WRK_PTGP_NEXT_PB`/`_PREVIOUS_PB`; Save `VC_AGA_ACTNS_WK_SAVE_BTN`; Validate Application `VC_AGA_ACTNS_WK_VALIDATE_BTN` (all clickable by visible text too).
- Left-nav items are Activity Guide steps (`PTGP_STEP_DVW_PTGP_STEP_LABEL$n`); **clicking the `li` does NOT navigate** — drive with Next/Previous. (Each step also has a direct `csprodonl_newwin … VC_OA_FL.GBL?PAGE=VC_OA_XXXX_DTL_FL` URL — untested for in-place navigation.)
- ⚠️ **One field per server round-trip**: setting Examining Authority + Exam Year + Exam Month in one JS pass silently lost the year/month (the select's AJAX re-render discarded unsynced sibling values). Settle after every change-dispatch.
- **The Next button is hidden on Step 6 until Validate Application passes** (steps 7+ locked). Validate failure → alert *"Errors found on multiple pages. (32030, 346)"* → **Validation Messages modal** (`ptModFrame`): rows of Page | Message | View Details.
- **Eligibility is enforced at Validate, not at selection** (unlike UP): *"You do not meet the subject requirements for EFA01"* + a View Details modal listing the required subjects ("…must have completed at least one of: **Mathematics HG**"). The check keys off the **Grade 12** subject list — it cleared once Gr12 subjects (incl. Mathematics) were present.

### Steps 2–13 — ids (prefix `VC_OA_STG_`)
- **2 Personal:** Title + Gender selects editable (prefilled from create); names/DOB/ID read-only.
- **3 Activities:** `GENL_VC_MAIN_ACTIVITY` (Currently upgrading matric / Employment Or Occupation / Gap Year / **School** / University); Add Sport optional.
- **4 Secondary Education:** radios `SEDH_VC_OA_SCED_OPT` (South African — default ✓) and `SEDH_VC_OA_SCHL_TYPE` (Current Grd 12 — default ✓). **Select School** button → modal `VC_OA_WRK_SEARCH_KEY` + `VC_OA_WRK_SEARCH_BTN`, result rows `VC_OA_WRK_SELECT$n`. Examining Authority `SEDH_WITS_EXM_AUT_CD` — **plain province names** (Gauteng, Limpopo, … + I.E.B. / NCV / SACAI), not "<province> DoE". Exam Year `SEDH_VC_FINAL_SCHL_YEAR` (text) · Exam Month `SEDH_UW_EXAM_MONTH` (June/November) · Exam Number `SEDH_WITS_EXAMNUM`. **Gr11 grid** (10 rows): subject `SEDG_SCHOOL_CRSE_NBR$n` (156 options, names truncated ~30 chars: "Afrikaans First Additional Lan") + mark `SEDG_VC_GRADE$n`. **Gr12 grid** `SEDT_SCHOOL_CRSE_NBR$n` + **Copy Grade 11 Subjects `VC_OA_WRK_VC_COPY_GR11_SUBJ`**. ⚠️ Research correction: **Gr12 subjects (min 5) ARE required for Current-Grd-12 applicants** — validation msgs: "Exam Year (Grade 12) must be entered", "Exam Month (Grade 12) must be entered", "At least 5 subjects must be entered (Grade 12 Subjects)".
- **5 Tertiary:** single checkbox `GENL_VC_OA_TERT_FLG` (unchecked = No — default right for matriculants).
- **6 Study Choices:** `VC_OA_WRK_VC_ACAD_PROG1/2/3` + `VC_OA_WRK_VC_ACAD_PLAN1/2/3` (plan = single non-blank option, must be explicitly selected). ⚠️ **On first render only PROG3 is visible** — all three blocks render after the first server round-trip; target PROG1 explicitly (a value set on the lone visible select lands in Programme 3). 62 open programmes (code + name, e.g. `EFA01 - Bachelor of Science in Engineering (Civil)`).
- **7 Domicilium:** Country `ADD1_COUNTRY` (defaults South Africa) · `ADD1_ADDRESS1/2` · Suburb `ADD1_ADDRESS3` · **Address Search link `VC_OA_WRK_ADDRESS_LOOKUP`** → modal rows `VC_OA_WRK_SELECT$n` (Suburb | City | Postal | Province) → selection fills the read-only City/Postal Code/Province.
- **8 Residential / 9 Postal:** `ADD2_VC_USE_ADDRESS` / `ADD3_VC_USE_ADDRESS` — "Same as Other Address" selects, options `["", "Domicilium"]` (Domicilium only; the video's "same as residential" doesn't exist).
- **10 Contact:** email + mobile prefilled from registration (`CNTC_VC_PHONE_CELL_SS`); home/work optional.
- **11 Demographics:** Marital `DEMO_MAR_STATUS` (Divorced/Married/Separated/Single/Widowed) · Population Group `DEMO_ETHNIC_GRP_CD` — **Asian / Black / Coloured / Indian / White** (⚠️ "Black", not "African") · Home Language `DEMO_LANG_CD` (large list) · Religious Affiliation `DEMO_RELIGIOUS_PREF` (**"Nil Declared"** = safe non-answer) · Disability `DEMO_DISABLED` (No/Yes).
- **12 Next of Kin** (`NKIN_*`): `NAME_PREFIX` · Initial `FIRST_NAME` · Surname `LAST_NAME` · mobile `VC_PHONE_CELL_SS` · `EMAIL_ADDR` · Relationship `PEOPLE_RELATION` · address same-as `VC_USE_ADDRESS` (`["", "Domicilium"]`) or manual `ADDRESS1/2/3` + `COUNTRY`.
- **13 Emergency:** checkbox `GENL_VC_OA_EMERG_FLG` "Use same details as Next of Kin" — ticking it **hides** the name/phone inputs (copied server-side); Relationship `EMER_RELATIONSHIP` still needs a value.

### Steps 14–17
- **14 Indemnity:** an **Accept link `SCC_TM_ADM_WRK_SCC_TM_ACCEPT`** (SCC agreement framework — same id family as UCT's submit) + Printable Page. Accept → step flips to Complete, page stays. Sits **before** Documents in Next order, so reaching uploads requires acceptance (consent ordering handled adapter-side via the agreement-consent flag).
- **15 Payment:** *"Application Fee Payable: R100"*, paid **after** submission — Self-Service Portal (Campus Finances → Make a Payment → Application Fee) or **EFT: FNB, acct 63075484302, branch 251905, Swift FIRNZAJJ**, person/student number as reference. Confirms: submission is NOT payment-gated. (The Welcome page also lists Standard Bank branch payments as an option.)
- **16 Documents:** two rows for a Current-Grd-12 applicant — **"Copy of ID Document/Passport"** and **"Final GR11 Results"** (not the matric certificate). Add buttons `VC_OA_WRK_FILE_CREATE1_LBL$0/$1`; PeopleSoft File Attachment modal: **My Device = `PT_ATTACH_BUTTON_DEF`** (⚠️ differs from UP's `PT_ATTACH_MYDEVICE`) → chooser → Upload `[id="#ICUpload"]` → "Upload Complete" → Done `[id="#ICOK"]`. A 344-byte dummy PDF uploads fine.
- **17 Submit:** *"Your application is complete. Please click 'Submit' below…"* — **Submit button = `VC_OA_WRK_SUBMIT_PB`** ("Submit Application to the University"). **Never clicked**; post-submit page remains [VERIFY] at the first supervised submit.

---

## Branch mapping (2026-06-27)

> Live-driven via Playwright with the Jane Doe synthetic applicant — Temporary ID `T1872394`, application instance `UW_OA_UGFT4356839`, **parked and unsubmitted** (indemnity not accepted, Submit never clicked). Covers all five applicant-type tracks for Wits: Completed matric, Repeating/upgrading, Gap year, Employed, International. The portal was left in its original parked state (Main Activity = School, Current Grd 12, Grade 11 marks intact).
>
> **Navigation note (supersedes the older plan note):** left-nav `li` clicks do NOT navigate; the live spike used Next/Previous. This session instead used the per-step **direct detail URLs** exposed in the left-nav (`.../psc/csprodonl_newwin/UW_SELF_SERVICE/SA/c/VC_OA_MENU.VC_OA_FL.GBL?PAGE=VC_OA_<STEP>_DTL_FL&...&PTAI_LIST_ID=<instance>&PTAI_ITEM_ID=UW_OA_UGFT<n>_<instance>`). Navigating the **main** window to one of these loads a standalone, fully-editable detail page for that step (own Save + Validate Application), which saves to the same application instance — a faster way to jump straight to Step 3 / Step 4 than clicking Previous ~10×. Step 3 page = `VC_OA_ACTV_DTL_FL` (item `UW_OA_UGFT11`), Step 4 = `VC_OA_SCED_DTL_FL` (item `UW_OA_UGFT13`).

### Master trigger: Step 3 "Main Activity" drives Step 4 "Current School Status"

The single most important finding: the **Step 4 "Current School Status" radio (`SEDH_VC_OA_SCHL_TYPE`: Current Grd 12 / Completed Grd 12 OR Upgrading) is NOT user-selectable** — both radios are rendered **`disabled`**. Its value is **derived server-side from the Step 3 "Main Activity" dropdown** (`GENL_VC_MAIN_ACTIVITY`):

| Step 3 Main Activity | → Step 4 Current School Status |
|---|---|
| `School` | `Current Grd 12` |
| `Currently upgrading matric` | `Completed Grd 12 OR Upgrading` |
| `Gap Year` / `Employment Or Occupation` / `University` | `Completed Grd 12 OR Upgrading` (same — any non-School activity) |

Verified live: saving Main Activity = `Currently upgrading matric` flipped Step 4 to `Completed Grd 12 OR Upgrading [checked][disabled]`; reverting to `School` flipped it back to `Current Grd 12` and **the Grade 11 marks were retained** (not wiped). **Adapter implication:** to set a Wits applicant's school status, the adapter sets **Step 3 Main Activity** — it must never try to click the Step 4 status radios (they're disabled).

### Track: Completed matric (prior year) & Repeating / upgrading

**Trigger:** Step 3 Main Activity → a non-`School` value (`Currently upgrading matric` for upgraders; any of Gap Year / Employment / University also yields the completed-status layout). Both tracks resolve to the **same** Step 4 state: `Current School Status = Completed Grd 12 OR Upgrading`.
**Step 4 layout change vs the Current-Grd-12 default:**
- **Fields hidden:** the entire **"Final Grade 11 Results"** 10-row table is removed, **and** the **"Copy Grade 11 Subjects"** button is removed.
- **Fields remaining:** only the **"Grade 12 Subjects"** table (the applicant enters final Grade 12 marks directly), plus Grade 12 Particulars (Examining Authority, Examination Year, Examination Month, Examination Number *(if available)*).
- **Validation changes:** none newly forced by label (Examination Number stays "if available"); the page instruction reminds upgraders to "enter ALL matric attempts". Per the 2026-06-11 spike, ≥5 Grade 12 subjects are required at Validate.
**Notes:** there is no separate "completed prior year" vs "repeating" control on Wits — both are the same `Completed Grd 12 OR Upgrading` status; the distinction (which year, multiple attempts) is conveyed via the Examination Year + the Grade 12 subject marks, not a dedicated field.
**Screenshots:** `screenshots/wits/branch-completed-upgrading/` (`step4-completed-upgrading.png`; base = `step4-secondary-base.png`).

### Track: Gap year

**Trigger:** Step 3 Main Activity = `Gap Year`.
**Fields revealed on Step 3:** none — the page stays Main Activity dropdown + optional "Add Sport". No gap-year date-range or description fields.
**Cross-step effect:** sets Step 4 Current School Status → `Completed Grd 12 OR Upgrading` (same layout change as above: no Grade 11 table / Copy button).
**Notes:** Wits captures no gap-year detail beyond the activity category itself.

### Track: Employed

**Trigger:** Step 3 Main Activity = `Employment Or Occupation`.
**Fields revealed on Step 3:** no input fields, but an **informational note** appears: *"Your Main Activity is Employment or Occupation. Note that you might be required to submit a CV or other supporting documents."*
**Cross-step effect:** sets Step 4 Current School Status → `Completed Grd 12 OR Upgrading`.
**Notes:** no employer-name / job-title / description fields — the only employment-specific behaviour is the CV-upload hint (Step 16 Documents). **Adapter implication:** nothing to map from the profile's employment fields here; surface the CV-document requirement to the student.

### Track: International applicant

**Trigger field:** Step 4 "Secondary Education Type" radio (`SEDH_VC_OA_SCED_OPT`: South African / International) — this radio **is** enabled/selectable (unlike Current School Status). Switch to `International`.
**Fields hidden:** the **"Grade 12 Particulars"** block (SA province Examining Authority list) **and** the **"Current School Status"** radios disappear entirely.
**Fields revealed:** an **"International Particulars"** section:
  - **Country** — native `<select>`, full ~250-country list.
  - **Examining Authority** — native `<select>`, **8 options**: `Assessment & Qualifications Alliance`, `Cambridge International Examination`, `Edexcel`, `Foreign School Leaving Certificate`, `International Baccalaureate`, `Namibian Senior Secondary Certificate`, `Scottish Examining Board`, `Zimbabwe Secondary Education Certificate`.
  - **Examination Year** — text.
  - **Examination Number (if available)** — text.
  - **Subject Level** — native `<select>`, **9 options** (NEW): `A Level`, `AS Level`, `Foreign School Leaving`, `German Abitur`, `HIGCSE`, `IGCSE`, `International Baccalaureate`, `Namibian Senior Secondary`, `Ordinary Level`.
  - **Enter Additional Exam Sittings** — native `<select>` (NEW): `1 Extra Sitting` / `2 Extra Sittings` / `3 Extra Sittings`.
**Notes:** confirms the original walkthrough's "8 exam authorities / 9 qualification types" counts (8 Examining Authorities, 9 Subject Levels). The Grade 11/Grade 12 subject tables still follow below for the marks. Reset back to `South African` before leaving (done).
**Screenshots:** `screenshots/wits/branch-international/` (`step4-international.png`; base = `step4-secondary-base.png`).

### University transfer — note only (out of scope)

Step 3 Main Activity = `University` adds **no sub-fields or note** on Step 3 itself, but (like the other non-School activities) sets Step 4 to `Completed Grd 12 OR Upgrading`. The tertiary-transfer detail lives in **Step 5 "Tertiary Education"** (toggle `GENL_VC_OA_TERT_FLG`, which matriculants leave "No"); per the hard rule, the transfer sub-fields were not mapped further.

### Session notes / state left behind (2026-06-27)

- **No submission, no payment, indemnity not accepted.** The application `UW_OA_UGFT4356839` remains parked at the indemnity step (where the parked session resumed), unsubmitted.
- **Restored to original:** Step 3 Main Activity saved back to `School`; Step 4 confirmed back to `Current Grd 12` with Grade 11 marks intact (e.g. row 1 = English Home Language 85). The International toggle on Step 4 was reverted to `South African` and never saved.
- **Population Group** reminder (from the 2026-06-11 spike, unchanged): Wits uses `Asian / Black / Coloured / Indian / White` — "Black", not "African".

## Appendix — raw dictated walkthrough
> Original unedited notes, kept as the source for anything the video doesn't show.

First thing on the portal ⇒ press "create temporary id"

So click the drop down for nationality. If choosing South African, national ID type will just already be chosen for you, and then all you have to do is write your ID number under national ID. If you choose anything besides South Africa, you're gonna have to specify whether or not your South African permanent residence and input in your passport number. For nonpermanent or for people who aren't from South Africa, they are gonna have other fields to fill in afterwards, such as PR certificate and BRSA national ID, etcetera, etcetera.

After that, now you put in applicant details. We're just gonna be the name, title. There's a drop down where Basically, they're just filling in miss the missus. They're gonna put in your first name, middle names, surname, date of birth, date of birth the month, and then date of birthday. Yes. We will separate it. Do you have the day, you have the month, then you have the year. Day and month are drop downs, and then, yeah, you have to fill in yourself. Then you have to fill in your gender. Options for gender are female, gender neutral, or male. After that you're gonna fill in your email address and then country code and mobile number. So you're gonna put in whatever country code you're using, and then the rest of the digits. After that, there's gonna be a security check where essentially you're gonna have to use computer vision to see what digits are being displayed there. Put the security code, whatever it is, into the security code field, and then you can press continue.

After that, Become a regional play, you can at least confirm temporary password. When you click that, you're gonna be prompted into your place with user details, filling the email address, filling whatever temporary ID was received, and then you fill in the password, which is the temporary password you received. And then after that, you're gonna click okay. After that you will be redirected to a new page where you will actually make a password, and then from now on you will use that password you've actually made. after saving it and whatnot.

After that, they came back to the main page where there's gonna be some temporary ID and the password you've actually made now. So you're gonna fill in your temporary ID and the password, and then click the login button. Moving on to the Apply for admission page, there's going to be a drop down application action where it's going to be begin your application or continue existing application. As of now, we're just going to be beginning a new application. After that, after we select beginner, pick new application, our application ID will be displayed. Application type, that's when we're gonna choose undergraduate full time. Academic care is whatever year we're applying to be in. then just leave academic calendar as january

So now after all of that, we're gonna come to step one or seventeen. Welcome to wits online application. Next button on the top right of every one of these, this is built off Oracle's application service that wits uses, much like UCT. After that, there's gonna be... when you do click next, however, it summarizes back... instead of seventeen pages, it'll only show you, like, six of them. The next page to fill will be personal details, the fields in personal details are title, first name, middle name, last name, date of birth, and gender. All of this is gonna be processed from beforehand, so that can be skipped. And then moving on to current activities since we are mainly gonna be dealing with matric students, We should just click school. The options are currently upgrading matric, employed, gap year, school, or university. There is also an additional sports button. The next step becomes secondary education. When you press the school button, you type in whatever school you attended and then click it from the options. Grade twelve particulars, examining authority, you're gonna click whatever province the student has. The examination year, examination month, and exam number if available. And then you're gonna fill in the final grade eleven results. There's gonna be a drop down for subjects and then a place to type in the marks. Current school status, whether you are currently grade twelve or complete grade twelve or upgrading. Step five, ask if you have any previous or current tertiary studies. You're just gonna leave it as no. So next step would be study choices, allows you to choose three, one compulsory two optional. Academic plan is basically the faculty. And then the domicilium address: country, address line one, address line two, then suburb. press address search button and then it automatically puts city, postal code, and province for you. Residential address, just keep it the same. and then do the same for postal address. For contact details, you still have your email address from before, and your mobile phone number. Now moving on to demographic details. Marital status, population group, home language, religious affiliation, and whether or not you have a disability. The next step is next of kin: name, title, initial, surname, phone numbers, relationship to applicant, and email address, and the next of kin's address. After that, emergency contact details. There's a button to use same details as next of kin.

The next part is an indemnity, where the student will have to accept. After that there's gonna be payment where there's a hundred rand application fee. they show you how much an application fee is, which is hundred rand, and then they give you details on how to pay. After this, there's going to be document uploads — a copy of their ID document and final grade eleven results.

Make sure to press validate applicant to make sure no errors were done in the application
