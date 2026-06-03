# Wits — Portal Research

> **Status: Draft v2 — verified from screen recording.** Rebuilt from `wits.mp4` (11:50) frame-by-frame. Temp-ID creation, the security-code captcha, the email-verify + temp-ID login, and all 17 wizard steps are confirmed from video. **Not** captured: the post-submit confirmation page (recording ends at the Step 17 Submit screen). Sample data shown in the video is intentionally omitted (PII).
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
- **Security Code (6-character image captcha)** on the "Create Application ID" page — must read the characters and type them. Requires OCR/vision to solve headlessly. **Blocker candidate** — raise in the Sunday sync before week 10.
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
Accept the indemnity/undertaking. → **app gap / open design question: surface the indemnity to the student for transparency vs auto-accept (decide with Partner A; same question as UJ's POPIA).**

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

## Uniflo mapping & app gaps (confirmed/added from video)
- **Current-year activity** (School/Gap Year/Upgrading/Employed/University) + **sport**.
- **Next-of-kin address** + **emergency contact distinct from NOK**; NOK email & mobile must differ from the applicant's.
- **Disability** — detailed category capture (large toggle list).
- **Indemnity/undertaking** — consent gate; surface to student (decide with Partner A).
- **Payment** — R100, post-submission; not a submission blocker; relay EFT details to student.
- **Marks** — Gr11 final marks now; Gr12 subjects via "Copy Grade 11 Subjects" (trial/none for current Gr12).
- Cross-check every mapping against `student_profiles` / `academic_records`. **[VERIFY against schema]**

## Screenshots
- Frames extracted from `wits.mp4` (1 per ~16s) to a local scratch folder — **not committed**. TODO: export key page shots to `screenshots/wits/`.

## Open questions / to verify
- [x] Submit screen (Step 17) — **captured** ("Submit Application to the University").
- [ ] Post-submit **success** page (URL + markers) shown after the button click.
- [ ] Document-upload step formats + size limits (Step 16).
- [ ] Steps 8/9 (Residential/Postal) exact "same as" behaviour.
- [ ] Indemnity acceptance approach (decide with Partner A).
- [ ] OCR reliability on the 6-char security code — **blocker check**.

---

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
