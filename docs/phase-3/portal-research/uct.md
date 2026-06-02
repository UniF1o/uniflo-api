# UCT — Portal Research

> **Status: Draft.** Reformatted from the dictated walkthrough + Notion screenshots (research dated 2026-05-25). DOM selectors, exact required/optional flags, validation rules, and the submission-confirmation markers still need a verification pass against the live portal. Unknowns are marked `_TBD_` or **[VERIFY]**. Raw dictation preserved in the appendix.

## Portal URL
- Landing / login: <https://publicaccess.uct.ac.za/psc/public/EMPLOYEE/SA/c/NUI_FRAMEWORK.PT_LANDINGPAGE.GBL?LP=UCT_ONLINE_APP_PUBLIC&lp=SA.EMPLOYEE.UCT_ONLINE_APP_PUBLIC>
- Engine: PeopleSoft / Oracle (same family as Wits and UP) — selectors will look like `win0divUCT_...`. **[VERIFY]**

## Application window
- Opens: **1 April 2026**
- Closes: **31 July 2026**

## Test account
- Credentials live in **Bitwarden** per Phase 3 plan §3 — _TBD: link Bitwarden entry._ (Deliberately not committed.)
- Account is self-created (username + password chosen by applicant), unlike Wits/UP which email a system-generated ID.

## Anti-automation measures ⚠️
- **Email OTP at account creation** — after "Create", an OTP is sent to the applicant's email; must be entered to verify before login. Headless automation needs inbox access to read it. Flag as a **partial blocker** — solvable only if the automation controls the test inbox. **[VERIFY whether OTP recurs at login or only at signup.]**
- No captcha/security-code image reported for UCT (contrast Wits/UP). **[VERIFY]**

## Application flow (pages in order)

### Account creation (pre-application)
1. From the landing page → **Create account**.
2. Fields: first name (as per ID), last name, date of birth (date-picker button), SA national ID **or** passport number, email, confirm email, username, password, confirm password.
   - **Username rules:** ≥10 chars, case-sensitive, only letters/numbers/hyphens/underscores/full-stops, may not be an email address.
   - **Password rules:** ≥16 chars, ≥1 special char, ≥1 number, ≥1 lowercase, ≥1 uppercase.
3. Submit → **email OTP** → enter OTP → **Verify OTP** → redirected to login.
4. Log in with username + password → choose **Undergraduate** → verify application year → **Start application**.

### The application — 16 steps
> ⚠️ **One-way flow:** once a section is completed you cannot go back. Every value must be verified before advancing. "Next" button is top-right; pattern is **Save → Next**.

| # | Step | Notes |
|---|---|---|
| 1 | Introduction | Info only |
| 2 | Personal information | see fields below |
| 3 | Contact details | see fields below |
| 4 | Parent / guardian information | see fields below |
| 5 | School information | see fields below |
| 6 | Tertiary information | "Applied to UCT before?" → leave blank; prior activity → blank (not expected for matric) |
| 7 | _TBD — not covered in walkthrough_ | **[VERIFY: narrative skips 7]** |
| 8 | Programme choices | 2 options: 1 compulsory + 1 other |
| 9 | Referees & supervisors | Skippable for most undergrad applicants |
| 10 | NBT information | **UCT-specific** — see fields |
| 11 | Funding | see fields |
| 12 | Student housing | "Be considered for student housing?" |
| 13 | Redress & disadvantage factors | see fields |
| 14–15 | _TBD_ | **[VERIFY exact ordering]** |
| 16 | Document uploads → Review application | see uploads |

## Form fields

### Step 2 — Personal information
| Field | Type | Required | Options / validation | Uniflo mapping | Selector |
|---|---|---|---|---|---|
| First name | text | yes | — | profile first name | _TBD_ |
| Preferred name | text | _TBD_ | Goes on the **student card** → student should control it | **app gap** (see below) | _TBD_ |
| Maiden name | text | optional | — | _TBD_ | _TBD_ |
| Surname | text | yes | — | profile last name | _TBD_ |
| Date of birth | date | yes | — | profile DOB | _TBD_ |
| Home language | dropdown | yes | _TBD list_ | profile home language | _TBD_ |
| Race | dropdown | yes | _TBD list_ | profile population group | _TBD_ |
| SA ID number | text | yes | — | profile national ID | _TBD_ |
| Title | dropdown | yes | Mr / Mrs / Prof / … | profile title | _TBD_ |
| Citizenship | dropdown | yes | South Africa / … | profile citizenship | _TBD_ |
| Has disability? | yes/no | yes | If yes → disability-type dropdown + **current support** field | **app gap** | _TBD_ |

### Step 3 — Contact details
| Field | Type | Required | Notes | Uniflo mapping |
|---|---|---|---|---|
| Country | dropdown | yes | — | profile country |
| Postal code | text | yes | Drives the suburb dropdown | profile postal code |
| Suburb / town / city | dropdown | yes | **Populated from postal code** | profile suburb/city |
| Address line 1 | text | **yes** | Home address | profile address line 1 |
| Address line 2–4 | text | optional | — | profile address lines 2–4 |
| Postal address | group | — | "Same as home address" option | profile postal address |
| Contact numbers | repeatable | yes | "+" adds a row: phone type + country code + number | profile phone |
| Email addresses | repeatable | yes | "+" adds a row: email type + address | profile email |

### Step 4 — Parent / guardian information
| Field | Type | Required | Notes |
|---|---|---|---|
| Title, ID/SAID, first name, surname, relationship, email | mixed | yes | — |
| Contact numbers | text | yes | SA cellular required |
| Guardian address | group | _TBD_ | "Same as applicant" option; else enter manually → **app gap: capture guardian address** |
| Fee payer | — | — | List parent/guardian as fee payer for simplicity |

### Step 5 — School information
| Field | Type | Required | Notes |
|---|---|---|---|
| Year of first secondary-exam completion | dropdown | yes | — |
| School has 3 or 4 terms | choice | yes | — |
| Grade 11 at same school as grade 12? | yes/no | yes | — |
| Grade 12 school in RSA? | yes/no | yes | — |
| School name | search | yes | **Find School** button → search |
| Qualification | dropdown | yes | → **NSC** |
| Grade 11 final results | dropdown+mark | yes | subject dropdown + mark each |
| Grade 12 April/June results | dropdown+mark | yes | subject dropdown + mark each |

### Step 8 — Programme choices
Level of qualification (Undergraduate) · Faculty · Academic qualification (e.g. BSc) · Specialization/major. Two choices: one compulsory, one optional.

### Step 10 — NBT information **(UCT-specific)**
NBT registration number · Year written/to-be-written · NBT exam date. **[VERIFY: is NBT mandatory for all faculties or only some?]**

### Step 11 — Funding
"Received funding from another institution?" · "Require financial assistance for the programme?"

### Step 13 — Redress & disadvantage factors (all dropdowns, each with an "I do not know" option)
Father's racial classification during apartheid · Mother's racial classification · Mother's first language · Highest education level of father/male guardian · Highest education of any grandparent · Family relies on state social pension? · Family receives a child-support grant on your behalf?
- Racial-classification options: Black, Chinese, Coloured, Indian, prefer-not-to-answer, do-not-know, "parents not resident during apartheid", White.

## File uploads
| Field | Accepted types | Size limit | Naming | Notes |
|---|---|---|---|---|
| SA ID document | _TBD_ | _TBD_ | _TBD_ | Confirmed in walkthrough |
| Other docs (grade 11/12 results?) | _TBD_ | _TBD_ | _TBD_ | **[VERIFY — narrative only named the ID]** |

## Submission confirmation
- Confirmation URL: _TBD_ **[VERIFY]**
- DOM markers / confirmation text: _TBD_ **[VERIFY — capture exact page for `verify_submission()`]**
- Final step is **Review application**; no payment step appeared in the UCT walkthrough (contrast Wits/UP). **[VERIFY whether UCT charges an application fee.]**

## Uniflo profile mapping & app gaps
Recurring "add this to the app" notes from research:
- **Preferred name** — student-controlled (printed on student card).
- **Disability support detail** — capture the type *and* the current/required support, not just a yes/no.
- **Parent/guardian address** — may differ from the student's; store separately.
- Confirm every mapping above against the actual `student_profiles` / `academic_records` columns before adapter work. **[VERIFY against schema]**

## Screenshots
- Source: Notion → *Uni Research / UCT* (presigned image links expire). 
- TODO: export PNGs to `docs/phase-3/portal-research/screenshots/uct/` and reference them here.

## Open questions / to verify
- [ ] Step 7 and steps 14–15 content (walkthrough skipped them).
- [ ] Whether email OTP recurs on every login or only at signup.
- [ ] Full document-upload list, formats, and size limits.
- [ ] Submission-confirmation URL + DOM markers.
- [ ] Whether NBT is required for the target faculties.
- [ ] Application fee (if any).

---

## Appendix — raw dictated walkthrough
> Original unedited notes, kept as the source of truth for the structured sections above.

So when you log in to the portal, There's gonna be a bunch of options. You're gonna click create account because you don't have one yet. So information needed here is first name as per your SAID or whatever document you're using, last name, your date of birth, which there's gonna be a button to press to select, your South African national ID slash your passport number, your email address, then you have to repeat your email address, then you have to form a username. The username has some requirements. It must be at least ten characters in length. Usernames are case sensitive, can only contain numbers, letters, hyphens, underscores and full stops. An email address may not be used as the username. And then you're gonna put in your password and confirm your password. Your password must be at least sixteen characters in length, contain one special character at least, at least one numeric character, one lowercase character, and one uppercase character. After create... present create, you're gonna present an OTP to your email. You're gonna go to your email, get the OTP, and then click verify OTP. After everything, you'll be redirected to to the login page. We're gonna use whatever username you had, plus your password to log in. after you log in, there's gonna be options to choose from. Below, you click undergraduate because that's what we'll be applying for at this stage and time. verify year u are applying for and then click start application

Okay. So there's gonna be sixteen steps, much like the one we did for wits The only caveat with UCT's application is that as soon as you complete a setting, you can't go back. So you have to verify and make sure that you're submitting accurate information for UCIT. is going to be a next button at the top right corner whenever you're done completing everything. The first one is just an introduction, then we'll move on to personal information. Personal information of your first name, preferred name, this I think we should ask the student because from my experience, the preferred name is what is gonna be put on their student card, so they should have as much control on that as much as they want. There's maiden name and an option, surname, date of birth, home language, race, SAID number, and then the title whether they are mister, missus, professor, and then their citizenship in South Africa. And then they have to, uh, specify whether or not they have any disabilities. Fluidicity is a thick gas jamming disability. It's gonna be a drop down where you can choose what disability you're affected by. They also have a shield where you have to specify what support you currently do have. So do make note of that so we can also add it to the app itself. So the flow with u c t is after you done filling in any information, you're gonna press save, then you're gonna click next. So next one would be contact details. So you have to fill in your country, postal code, suburb slash town slash city, address line one, two, three, four, but owner address line one is compulsory. That's your home address. On the right side, there's the postal address, but you have the option to keep it the same as your home address. So the country and then the suburb will be drop downs. The the drop down for suburbs slash town city will be based on whatever postal code you put in, which is good to know. Still within contact details, there's gonna be a place for contact numbers and email addresses. You click the plus sign there to add a new new row. You're gonna select one of our phone type, input the country code, and then the actual number. For emails, you select the email type and the actual email address is what you put The next is parent guardian formation, so the gods for the title, SAID number, or whatever identification. First name, surname, relationship to the applicant, and email address. And then contact numbers will be required to SA cellular. They're gonna ask if your parent or guardian's address, if it's the same, just say it's the same. If not, you might have to put in the the address too. So that's another thing to note to make sure. We also ask for the parent or guardian address in case it might be different? There's going to be a few pain formation. Just list the parent guardian as the fee payer for simplicity sake. So step five is school information. You're gonna select the year you're completing or completed your secondary schooling examination for the first time. And then indicate whether your school has three or four terms. Did you complete the eleventh at the same school as grade twelve? Is your grade twelve or equivalent school in the Republic of South Africa? And then you're gonna have to press find school and then input the school name. So Still living qualification of the Dropbox, just choose the appropriate one which will be NSC. After all that would be prompted to add in grade level final results in grade twelve April results. So you have to click from a drop down then add the actual mark for each of those. Step six is basically just tertiary information asking if it applied to UCT before. You can leave that as blank. Any postal activity, we can leave that as breakers. We don't anticipate that from a trade student yet because they're still in school. And then we're gonna move on to step eight, which is program choices. UCT gives you... lets you choose two options, one compulsory and one other. Gonna choose your level of qualification. You should be undergraduate. Faculty, academic qualification, which will be a bachelor of science in in the science faculty, and then the specialization or whatever major people wanna be doing. the next step of the problem choices will be referees and supervisors, but for most people, they won't need that so we can skip that. An important part, especially for UCT, is step ten and b t information. It has to import your NBT registration number and the year you're gonna write the NBT or have written it in. the nbt exam date will also be required. The next step, eleven of sixteen, is about funding. There's gonna be options to ask if you've received just first funding from another institution or whether or not you require financial  assistance for the program. next step asks if student wants to be considered for student housing

The next part is redress and disadvantage factor inflammation. It will be asked for both your father and mother's racial classification during apartheid. the highest level of education, highest level of education by any grandparent, and does your family rely on social pension from the state? Under racial classification, there's multiple options to choose from. Black, Chinese, colored, Indian. You can choose not to answer. You have the option to say do not know, to say that your parents did not resign and say during apartheid or that they were white. also asked for your mother's first language Yeah. There are service tires, level of education of your father slash male guardian. Does your family receive child support grant on your behalf? for each of these there is a i do not know option. they are all dropdown selections. next is document uploads asking for sa id document. the last step is a review application
