# UP — Portal Research

> **Status: Draft.** Reformatted from the dictated walkthrough + Notion screenshots (research dated 2026-05-25). DOM selectors, exact required/optional flags, validation rules, and the submission-confirmation markers still need a verification pass against the live portal. Unknowns are marked `_TBD_` or **[VERIFY]**. Raw dictation preserved in the appendix.

## Portal URL
- Login: <https://upnet.up.ac.za/psc/upapply/EMPLOYEE/SA/c/UP_OAP_MENU.UP_OAP_LOGIN_FL.GBL?&>
- Engine: PeopleSoft / Oracle (same family as UCT and Wits).

## Application window
- Opens: **1 April**
- Closes: **31 May** (earliest-closing of the four target portals — flag for scheduling)

## Test account
- Credentials live in **Bitwarden** per Phase 3 plan §3 — _TBD: link Bitwarden entry._ (Deliberately not committed.)
- UP issues a **system-generated application ID + password** by email after the first form; applicant then confirms email and sets a new password.

## Anti-automation measures ⚠️
- **Security code (image)** on the new-application form — requires OCR/computer vision to solve headlessly. Flag as a **blocker candidate** — raise in the Sunday sync before week 10 if vision solve is unreliable.
- **Email delivery of login credentials** — automation needs inbox access to read the application ID + password.

## Application flow (pages in order)

### Create application (pre-login)
1. **"I want to…"** dropdown → **New application**.
2. New window: Career of study (dropdown → Undergraduate) · First year of study (dropdown → year applying) · Student number (leave blank if none) · Last name · First name · Middle names · Email · Confirm email · Date of birth (date-picker button) · **Identify me by** (SAID number / Passport number) → value entered next step.
3. **Security code** (see anti-automation) → continue. Login details emailed.

### Log in & set password
1. **"I want to…"** → *Log in to continue / view study application* → enter emailed **application ID + password**.
2. Prompted to **confirm email + change password**: old/supplied password → new password → confirm new → OK.

### The application
| Step | Page | Notes |
|---|---|---|
| 1 | Personal information | see fields |
| 2 | Contact details | address + phones |
| 3 | Demographic details | see fields |
| 4 | Tertiary education | "Previously enrolled tertiary?" → **No** |
| 5 | Secondary education | see fields — **UP-specific subject-order constraint** |
| 6 | Programme choices | first + second choice; backend eligibility check |
| 7 | General details | residence / NSFAS / UP financial aid |
| 8 | School results uploads | grade 11 final **OR** grade 12 certificate |
| 9 | Declaration → Verify application → Payments | see confirmation |

## Form fields

### Step 1 — Personal information
| Field | Type | Required | Notes | Uniflo mapping |
|---|---|---|---|---|
| Title | dropdown | yes | — | profile title |
| Preferred first name | text | _TBD_ | → **app gap: ask the student** | **app gap** |
| Citizenship | — | yes | SA citizen | profile citizenship |
| SA national ID | text | yes | — | profile national ID |

### Step 2 — Contact details
| Field | Type | Required | Notes | Uniflo mapping |
|---|---|---|---|---|
| Country | dropdown | yes | — | profile country |
| Address line 1 | text | **yes (assumed)** | **[VERIFY — UP doesn't mark it]** | profile address line 1 |
| Address line 2–4 | text | _TBD_ | — | profile address lines 2–4 |
| City / suburb | search | yes | **Search button** → autofills postal code + province | profile city/suburb |
| Mobile number | text | yes | — | profile phone |
| Alternative mobile | text | optional | — | profile alt phone |
| Email | text | prefilled | from earlier step | profile email |

### Step 3 — Demographic details
Gender (dropdown) · Home language (dropdown) · Population group (dropdown) · **"Tell us about yourself"** status (dropdown) · Disability (slider → "+" to add by category → **required-assistance** field).
- Status options: currently in high school / post-school technical / college student / university-of-technology student / university student / repeating / unemployed & never studied tertiary / working & never studied tertiary.
- → **app gap: capture disability + required assistance** so it maps to the support the programme requires.
- Note (Notion): gender — **[VERIFY whether UP restricts to male/female like UJ]**.

### Step 5 — Secondary education
Final school year (dropdown) · Examining authority (dropdown: Limpopo DOE, …, IEB, IEB ISC / exam board for Christian Ed, Cambridge, foreign country, etc.) · School name (search button) · School grade type (NSC / IEB) · Highest completed grade · Examination number (if grade 12 completed, else blank) · Exemption type (→ "currently busy with schooling") · **Subjects**.
- **⚠️ UP-specific constraint:** subjects must be entered in the **same order as the school report**. No other target portal requires this. → **app gap / constraint: preserve subject order for UP.**
- Per subject: subject (dropdown) · mark (dropdown — NSC achievement level 1–7, e.g. 7 = 80%+) · percentage (actual %). The adapter/AI must map percentage → NSC level.

### Step 6 — Programme choices
First choice + second choice. Search button → view programmes → select study programme (type + search + select). UP's backend **verifies qualification eligibility** from the entered marks ("matching service" data). An **"open only"** toggle filters programmes still open.

### Step 7 — General details
Residence consideration (No/Yes dropdown) + preferred residence · NSFAS application? · UP financial aid application?

## File uploads
| Field | Accepted types | Size | Naming | Notes |
|---|---|---|---|---|
| SA ID | _TBD_ | _TBD_ | _TBD_ | — |
| Grade 11 final results **OR** grade 12 certificate | _TBD_ | _TBD_ | _TBD_ | **Exactly one, not both.** Grade 12 cert only exists post-finals, so matriculants almost always upload grade 11 final. |
| Academic transcript | — | — | — | **Not required** for matric students |
| Sporting accomplishments | _TBD_ | _TBD_ | _TBD_ | Optional |

## Submission confirmation
- Flow ends: **Declaration → Verify application → Payments**.
- Confirmation URL / DOM markers: _TBD_ **[VERIFY — capture for `verify_submission()`]**
- **Payment gate:** we do not process payments. Set the automation to stop at/after *Verify application*; surface the payment link to the student (proof-of-payment upload or online card). **Decide exact stop point with Partner A.**

## Uniflo profile mapping & app gaps
- **Preferred first name** — ask the student explicitly.
- **Disability + required assistance** — capture in enough detail to map to programme support.
- **Subject order** — UP requires subjects in school-report order; consider preserving subject order in the profile (UP-only, but harmless elsewhere).
- **Mark mapping** — store both the NSC level (1–7) and the actual percentage; UP asks for both.
- Confirm all mappings against `student_profiles` / `academic_records` before adapter work. **[VERIFY against schema]**

## Screenshots
- Source: Notion → *Uni Research / UP* (presigned links expire).
- TODO: export PNGs to `docs/phase-3/portal-research/screenshots/up/` and reference them here.

## Open questions / to verify
- [ ] Whether address line 1 is the only required address field.
- [ ] Whether gender is restricted to male/female.
- [ ] OCR reliability on the security code — **blocker check**.
- [ ] Full document formats + size limits.
- [ ] Submission-confirmation URL + DOM markers, and exact payment stop point.
- [ ] The NSC level ↔ percentage mapping table the adapter will need.

---

## Appendix — raw dictated walkthrough
> Original unedited notes, kept as the source of truth for the structured sections above.

First thing that'll happen is she'll be prompted with an I want to, then I'll be a drop down, and we're gonna select a new application. After that, new shows will pop up. We're gonna have to enter career of study and first year of study. These will be drop downs. Currently, you're gonna choose undergraduate, first year of studies can be whatever year we are applying to. Student number, first year applied to a UP is gonna be last blank if they don't have it. Last name, first name, middle names. Then you put in your email address, then you repeat on confirm email address, and then date of birth, which you're gonna click the button to actually select the date of birth. There is a show called Identify Me by: Gonna Choose Between SAID Number or Password Number and then you're gonna put in the actual value in the next step. And then much like the one in UCT, there's going to be a security code put in, and you have to enter it in order to continue. So you have to use computer vision for that for you to see the code, recognize it, and then enter. After that, login details will be sent to the supplied email. You can go back to the i one two, and instead now, we're going to log in to continue or view study application. We're gonna input whatever application ID was sent along with the password that was supplied. After entering all that, you'll be prompted to confirm your email and change your password. So you're gonna put here whatever old positive or supplied, the new positive, and then confirm the new positive and then click okay. Okay. Cool. After all of that, we'll move on to personal information. Let's select the title. We're gonna enter a preferred first name, which we should ask the student for in the app so to make note of that. Citizenship should be a safe citizen, and then African national ID should still be there for more than fourteen previous contact details, gonna put in the address. So countries are drop down address... this address line, one two three four. You only have to fill in address one, I assume. They don't indicate on the side, but I assume yes. And then for city server, we actually have to click a button to actually search for the city. After a few chews around a city or suburbia, the postal code in the province will automatically be put in for you. You then have to enter your mobile number and an alternative mobile number, if applicable. Email address should already be there from previous steps. Moving on to demographic details, the vast array of agenda which will be a drop down, home language is also going to be a drop down, population group which is basically just your ethnicity group, and then there's gonna be a telesmaul part with a drop down. Options, I'm currently still in a high school. I was... I am or was post school, technical, college student, university of technology student. I am or was a university student. I'm repeating. I am unemployed, and I haven't studied before at a tertiary institution. I am working and haven't studied before at a tertiary institution. Yeah. Also be prompted to see if you have a disability or not. If you do, just click the slider at the name and click the plus button to add your disabilities by category, then they'll retire, but then they'll be a part where they ask you for your required assistance We should ensure we cover this in good detail in our app so we can map it regarding or to the degree required.

Move on to tertiary education. They ask if you were previously enrolled in anything tertiary related. We are going to say no. Why is that? Because you're dealing with high school students. They're gonna move on to secondary education, and they ask for the final school year, which will be a drop down. Examining authority is going to depend on whether student was Options include Limpopo, DOE, Cosmetal, DOE, IAB independent exam board, IAB ISC, exam board for Christian Ed, Cambridge, foreign country, etcetera, etcetera. And then gonna be asked for your school name, click the search button, and actually search for it to have it be put in the school grade types. We remain looking for a national senior certificate or IEB. I don't specify your highest completed grade. If you downgrade twelve, you'll have to put in your examination number. If not, leave it blank. And then on exemption type, you'd say that currently busy with schooling, which will be a drop down option. Here, we're adding in the actual subjects. They specifically say that they must be ordered the same way in which they are in their school report. So maybe we can make that a constraint in the app to overall because no other university had this constraint, but it'll just be good to follow. So just so it can work around for UP. But then, yeah, it's it's gonna be a drop down where you choose the subject, drop down for the mark, and then you fill it in. Basically, how it works is usually in the subject, mark is basically the ranking seven in the South African learning system is usually eighty percent plus and whatnot. So you must learn those mappings. Subject is just a full subject name. Mark refers to those values, and then percent is the actual percentage mark for whatever subject you are learning. So you feel that you have two choices. The first choice and the second choice. So you click, um, search button to actually start viewing the choices they offer. Then they... you... there's a tab where you're gonna have to select your study program. You type something, and then you press search, and then you're gonna select it. The UP system in the back end will verify whether or not you qualify for the specific qualification you choose using the MogSave service data in the previous section. A name that selects the retry section on top, there's an open plant only, so it allows you to sort out programs that are still open or not. Other than that, you wanna view them. Move on to general details, sir, that asked you whether you want to be considered for a residence place. It's a drop down of no and yes, and then there'll be financial... and then does your preferred residence that you want. And then they ask you if you are going to apply for Naspers and if you want to apply for UP financial aid. After that, I wanna ask you for your SAID, and then your grade twelve, grade eleven final results, and grade twelve results. In the mandatory school results, the required are the eleven final or the grade twelve actual certificate, which can only be submitted by people virtually until their final exam, which most people would have not. So it's either one of the two and not both, which is a good thing to keep track of. There's other school results you could do as in if you have been admitted not grade twelve results, you don't put them there. You staff certificate grade eleven extra marks or SAT grades. Yeah since we dealing with matric students, then you don't have to upload your academic transcript. Let's just scroll down. Additionally, there's also a place to upload your sporting accomplishments if applicable to the specific student. After that there will be a declaration, and then you can verify your application. Then you can move on to payments. And then after all of that, it's fine. We can actually apply. Seeing as how we do not process payments, first thing we do with , we have to set up the link up until here so that we can handle the payment, either upload the proof of payment or do an online credit card payment. Whatever will float the about.
