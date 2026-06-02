# UJ — Portal Research

> **Status: Draft.** Reformatted from the dictated walkthrough + Notion screenshots (research dated 2026-05-22). DOM selectors, exact required/optional flags, validation rules, and the submission-confirmation markers still need a verification pass against the live portal. Unknowns are marked `_TBD_` or **[VERIFY]**. Raw dictation preserved in the appendix.

## Portal URL
- Login: <https://registration.uj.ac.za/pls/prodi41/gen.gw1pkg.gw1startup?x_processcode=ITS_OAP>
- Engine: **ITS Integrator** (different from the PeopleSoft/Oracle portals — UCT/Wits/UP). Selectors and patterns will differ; nearly every lookup is a **search button** rather than a free-text field.

## Application window
- Opens: **1 April**
- Closes: **31 October**

## Test account
- Credentials live in **Bitwarden** per Phase 3 plan §3 — _TBD: link Bitwarden entry._ (Deliberately not committed.)
- UJ issues a **student number** (the walkthrough notes "wait for student-number confirmation"). The applicant also sets a **5-digit numeric PIN** near the end. **[VERIFY login mechanics for re-entry.]**

## Anti-automation measures ✅
- **No captcha** — explicitly confirmed in the walkthrough. This makes UJ the **strongest first-adapter candidate** of the four (no OCR/OTP blocker).
- **POPIA agreement** must be accepted, and a final **agreement** before PIN creation. Not anti-automation per se, but a consent gate — see app-gap note.

## Application flow (pages in order)

### Entry
1. Applicant type: **New applicant** / Returning / Internal (has UJ student number) → **New applicant**.
2. "Do you already have a student number?" → **No**.
3. "Finalize an incomplete application?" → **No** (Yes = continue an existing application).
4. **POPIA agreement** → accept (consent gate — see app gap).

### Sections
| Step | Page | Notes |
|---|---|---|
| 1 | Biographical details | see fields |
| 2 | Address & contact | search-based postal code |
| 3 | Residence + disability | see fields |
| 4 | Next of kin + account (payer) | see fields → app gap (payer address) |
| 5 | Results details | matric year + subjects |
| 6 | Educational institutions | school(s) attended |
| 7 | Programme selection | faculty + qualification → 5-digit PIN |
| 8 | Summary → accept agreement | see confirmation |

## Form fields

### Step 1 — Biographical details
| Field | Type | Required | Notes | Uniflo mapping |
|---|---|---|---|---|
| Nationality / SA citizen? | choice | yes | — | profile citizenship |
| ID number | text | yes | — | profile national ID |
| Citizenship code | search | yes | **Search button** → select South Africa | profile citizenship |
| Date of birth | date | yes | date-picker button | profile DOB |
| Title | text/dropdown | yes | — | profile title |
| Initials | text | yes | — | profile initials |
| Surname | text | yes | — | profile last name |
| First names | text | yes | — | profile first name |
| Maiden name | text | optional | if applicable | profile maiden name |
| Marital status | _TBD_ | yes | — | profile marital status |
| Home language | _TBD_ | yes | — | profile home language |
| Ethnic group | _TBD_ | yes | — | profile population group |
| Gender | choice | yes | **Male / Female only** (Notion note) | profile gender |
| Address line 1 | text | yes | street name | profile address line 1 |
| Address line 2 | text | yes | suburb | profile suburb |
| Address line 3 | text | yes | town | profile city/town |
| Address line 4 | text | yes | province | profile province |
| Postal code | **search** | yes | **Do not type** — click search button to look it up | profile postal code |

### Step 2 — Contact information
SA cell phone number (required) · Work/cell phone (optional) · Home telephone (optional) · Email + confirm email.

### Step 3 — Residence + disability
Apply for residence? (yes/no) · Disability (tick yes/no → **search** for disability + optional remarks). Save & continue.

### Step 4 — Next of kin + account (payer)
- **Next of kin:** name + phone number.
- **Account (payer):** name of person responsible for payments (use the guardian) · contact name · **address re-entered in full** (no "same as student" option) · email. Save & continue.
- → **app gap: UJ has no "same as applicant" for the payer address — must store/supply the payer address separately.**

### Step 5 — Results details
Matric year · Post-grad / under-grad (dropdown → **Undergrad**) · Upgrading results? (yes/no) · SA or international matric (→ **SA**) · Endorsement from school-leaving certificate · "Currently in grade 12".
- **Subjects** (everything via search buttons): per subject → search school-leaving subject · search grade (→ NSC) · final / grade-11 symbol · mark. Save & continue.

### Step 6 — Educational institutions
Which school last attended (**search**) · current status (grade 12) · attended any other institution previously? → **No**. Next.

### Step 7 — Programme selection
Academic year to apply for · Qualification type (short → long courses; most applicants = degree/"curricular" courses) · Faculty (**search**) · Programme / field of study (**search**) · Year of study (→ first year) · How registered + when to study (auto-selected).
- **"Add qualification"** wipes current selections to let the applicant pick a different qualification — handle carefully in automation.
- Summary → accept → **create 5-digit PIN**: numeric only, **cannot start with 0**, **no repeating characters** → accept agreement.

## File uploads
| Field | Accepted types | Size | Naming | Notes |
|---|---|---|---|---|
| _TBD_ | _TBD_ | _TBD_ | _TBD_ | **[VERIFY — walkthrough didn't reach a document-upload step; confirm whether UJ uploads docs in-portal or later]** |

## Submission confirmation
- Flow ends at **Summary → accept agreement** (after PIN creation).
- Confirmation URL / DOM markers: _TBD_ **[VERIFY — capture for `verify_submission()`]**
- **[VERIFY whether an application fee / payment gate exists for UJ — not mentioned in the walkthrough.]**

## Uniflo profile mapping & app gaps
- **Payer (account) address** — UJ offers no "same as student", so we must hold a payer address.
- **5-digit PIN** — generated during submission (numeric, no leading 0, no repeats). Store securely (Bitwarden / secrets, not the profile DB). **[Decide storage with Partner A.]**
- **POPIA + final agreement** — consent gates; consider surfacing the agreement link to the student for transparency (same open question as Wits indemnity).
- Confirm all mappings against `student_profiles` / `academic_records` before adapter work. **[VERIFY against schema]**

## Screenshots
- Source: Notion → *Uni Research / UJ* (presigned links expire).
- TODO: export PNGs to `docs/phase-3/portal-research/screenshots/uj/` and reference them here.

## Open questions / to verify
- [ ] Login/re-entry mechanics (student number + PIN?) for resuming an application.
- [ ] Whether/where documents are uploaded in-portal.
- [ ] Application fee / payment gate (if any).
- [ ] Submission-confirmation URL + DOM markers.
- [ ] PIN storage approach (decide with Partner A).

---

## Appendix — raw dictated walkthrough
> Original unedited notes, kept as the source of truth for the structured sections above.

So I'm going into u j. There's going to be an option to choose from new applicant, a returning, or internal applicants, people already existing with the u j student number. For us, we're gonna go to new applicants. They are prompted later. They already have a student number. We're gonna click no. Are they referring to finalize an incomplete application for the first part to make it no if for continuing an application, make it yes. So there's a huge apoebi egg that people do have to accept? I don't know. You maybe may have to save the link, send it to the users so they can drink for themselves and then choose to accept. And then the AI can take over from there. no capcha for this one So now we'll move on to biographical details. As for nationality, whether you're a basic citizen or not, as for your ID number, citizenship code, it's going to be a search. So click the search button, and then just select South Africa. Your date of birth, you are going to have to click the button for date of birth and to actually choose the date of birth. Then you input your title, your initials, surname, and first names. maiden name too if applicable and maritial status. input in home language too. ethnic group too You just have to put in your skin and dress so they do give you some guidelines. Address line one, pick your social street name. Address line two, your suburb. Line three should be your town name, and line four should be your province. for postal code you do not type it in, you click the button that looks like search and search for it there We then move on to contact information where they ask you for your South African cell phone number. Um, your work phone... cell phone number optionally, and your home telephone number optionally. Then you have to put in your email address and then verify it by inputting it again.

Residents information, they ask you to choose if you want to apply for residence or not. Then there's also disability information. We have to tick whether or not you have a disability. And then much like we have been doing with this system, there's going to be a button that is like a search. We're gonna definitely look for whatever disability the person has and any remarks. The remarks here are not compulsory, but would be good to include. after this press save and continue

We now move on to the next of kin details, where they ask for the name of next of kin and then the next of kin's phone number. Account details, you're gonna enter the account, the name of the person who is responsible for making payments. So we're gonna use the information of the guardian, whatever guardian there is. So you're gonna put in the contact name, and then UJ requires you to write down the address information again. There's no option to just make it the same as the student applying. address in entered the same way as before. and also include email address of account payer. then press save and continue

next step is results details. input in your matric year and there will be a drop down wanting u to specify whether u are applying for post grad or under grad. After specifying that you are of undergrad, you're gonna be asked whether or not you are upgrading your credit or results, whether or not you have completed South African or international metric for most people with doing now will be South African. And then you're gonna be asked, most of this have been a drop down. Now much like you, Jay's infrastructure, there is going to be that button that will take a search button, which is essentially what you're gonna use to do for a majority of the things we'll be doing here. So indicate your endorsement from your school leave certificate. You're gonna put in... choose the currently in grade twelve. And then for school subjects, basically, everything is done the same way where with each subject, you click the search button thing to choose the school leaving subject. You choose the search button thing for the grade, which is will be NSC. then the final to eleven symbol, which you'll have to choose there. For the mark, you actually got. after all entered, press save and continue

The next step would be educational institutions and ask for school details, which school did you last attend, and what are you going to be doing? There'll also be a search button here to click. So for the first one, you're gonna search out whatever school the student put in. The second one, they could just specify that they are grade twelve people. Something else asked is if they've attended any other institution previously, which should be no because why they are high school students. going on to next section

The next section will ask you for your academic year that you wish to apply for. When I applied, the focus I have a bachelor's degree from short courses to extra long courses, the ones that most will be applying for will be curricular courses. And then you're gonna be asked for the specific faculty. So for you, Jay, just click the search button, and then have it there. And then you're gonna choose your program for which of study I applied. For most people, it would be first year. You're gonna click that option. After clicking Witcher of Study, how did you register for this program, and when would you like to study? You'll be automatically selected for you. You cannot lick add qualification into this another thing they wanna study for after the add qualification button, everything will just be wiped and they can reselect things for a different qualification. After going to the summary and accepting everything, you're gonna have to create a five digit PIN that can only consist of numerical values. You cannot start with a zero, and you cannot have repeating characters. after that you will accept the agreement. since this is another part that students have to see the agreement we can implement something for that
