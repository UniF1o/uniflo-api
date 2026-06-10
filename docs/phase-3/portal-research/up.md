# UP — Portal Research

> **Status: Draft v2 — verified from screen recording.** Rebuilt from `up.mp4` (20:39) frame-by-frame. New-application creation, the case-sensitive captcha, the emailed Application-ID login, and all 12 sections (through the "Apply" confirmation) are confirmed from video. **Not** captured: the page shown *after* clicking "Apply" (post-submit confirmation). Sample data shown in the video is intentionally omitted (PII).
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
- **Security Code (case-sensitive 6-char image captcha)** on the new-application form — requires OCR/vision (case-sensitive, so the OCR must preserve case). **Kept in MVP (2026-06-03)** — the runtime must ship image OCR; not a drop candidate.
- **Email delivery of Application ID + password** — automation needs inbox access.
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
- [x] Apply (submit) screen + full Payment methods — **captured**.
- [~] Post-"Apply" **success** page — **on hold (2026-06-03): can't capture without a real submission**; confirm at first live adapter run (use the "Must still verify & apply" status flip meanwhile).
- [~] Whether address lines 2–4 are required + document formats/size limits — **login-gated; deferred until test-account access** (the wizard sits behind the emailed Application-ID login; only the public "I want to" landing is reachable, confirmed live 2026-06-03).
- [x] Gender set — Male/Female on the portal; matches our Male/Female-only enum (HEMIS).
- [x] Captcha — **kept in MVP (2026-06-03)**; runtime must ship case-preserving OCR for the security code (no longer a drop candidate).

---

## Appendix — raw dictated walkthrough
> Original unedited notes, kept as the source for anything the video doesn't show.

First thing that'll happen is she'll be prompted with an I want to, then I'll be a drop down, and we're gonna select a new application. After that, new shows will pop up. We're gonna have to enter career of study and first year of study. These will be drop downs. Currently, you're gonna choose undergraduate, first year of studies can be whatever year we are applying to. Student number, first year applied to a UP is gonna be last blank if they don't have it. Last name, first name, middle names. Then you put in your email address, then you repeat on confirm email address, and then date of birth, which you're gonna click the button to actually select the date of birth. There is a show called Identify Me by: Gonna Choose Between SAID Number or Password Number and then you're gonna put in the actual value in the next step. And then much like the one in UCT, there's going to be a security code put in, and you have to enter it in order to continue. So you have to use computer vision for that for you to see the code, recognize it, and then enter. After that, login details will be sent to the supplied email. You can go back to the i one two, and instead now, we're going to log in to continue or view study application. We're gonna input whatever application ID was sent along with the password that was supplied. After entering all that, you'll be prompted to confirm your email and change your password. So you're gonna put here whatever old positive or supplied, the new positive, and then confirm the new positive and then click okay. Okay. Cool. After all of that, we'll move on to personal information. Let's select the title. We're gonna enter a preferred first name, which we should ask the student for in the app so to make note of that. Citizenship should be a safe citizen, and then African national ID should still be there. previous contact details, gonna put in the address. So countries are drop down address... this address line, one two three four. You only have to fill in address one, I assume. And then for city server, we actually have to click a button to actually search for the city. After a few chews around a city or suburbia, the postal code in the province will automatically be put in for you. You then have to enter your mobile number and an alternative mobile number, if applicable. Email address should already be there from previous steps. Moving on to demographic details, the gender which will be a drop down, home language is also going to be a drop down, population group which is basically just your ethnicity group, and then there's gonna be a tell us more part with a drop down. Options, I'm currently still in a high school. I am or was post school, technical, college student, university of technology student. I am or was a university student. I'm repeating. I am unemployed and haven't studied before at a tertiary institution. I am working and haven't studied before at a tertiary institution. Also be prompted to see if you have a disability or not. If you do, just click the slider and click the plus button to add your disabilities by category, then there'll be a part where they ask you for your required assistance. We should ensure we cover this in good detail in our app so we can map it to the degree required.

Move on to tertiary education. They ask if you were previously enrolled in anything tertiary related. We are going to say no. Why is that? Because you're dealing with high school students. They're gonna move on to secondary education, and they ask for the final school year, which will be a drop down. Examining authority is going to depend on whether student was Options include Limpopo DOE, etcetera. And then gonna be asked for your school name, click the search button, and actually search for it. school grade types, looking for a national senior certificate or IEB. your highest completed grade. If you completed grade twelve, you'll have to put in your examination number. If not, leave it blank. And then on exemption type, you'd say that currently busy with schooling, which will be a drop down option. Here, we're adding in the actual subjects. They specifically say that they must be ordered the same way in which they are in their school report. So maybe we can make that a constraint in the app. it's gonna be a drop down where you choose the subject, drop down for the mark, and then you fill it in the percent. mark is basically the ranking — seven in the South African learning system is usually eighty percent plus. Subject is just a full subject name. Mark refers to those values, and then percent is the actual percentage mark. So you have two choices. The first choice and the second choice. you click search button to actually start viewing the choices they offer. The UP system in the back end will verify whether or not you qualify for the specific qualification you choose using the marks in the previous section. there's an open plant only, so it allows you to sort out programs that are still open or not. Move on to general details, that asks you whether you want to be considered for a residence place. It's a drop down of no and yes, and then preferred residence. And then they ask you if you are going to apply for Nasfas and if you want to apply for UP financial aid. After that, your SAID, and then your grade twelve, grade eleven final results, and grade twelve results. the required are the grade eleven final or the grade twelve certificate, which can only be submitted by people after their final exam. So it's either one of the two and not both. since we dealing with matric students, then you don't have to upload your academic transcript. Additionally, there's also a place to upload your sporting accomplishments if applicable. After that there will be a declaration, and then you can verify your application. Then you can move on to payments. Seeing as how we do not process payments, we have to set up the link up until here so that we can handle the payment, either upload the proof of payment or do an online credit card payment.
