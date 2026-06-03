# UCT — Portal Research

> **Status: Draft v2 — verified from screen recording.** Rebuilt from `uct.mp4` (38:26) frame-by-frame. Field labels, control types, required flags, dropdown option lists, the 16-step flow, and the document-upload + review steps are confirmed from video. **Not** fully captured: Step 16 (Agreement and Submission) and the post-submit confirmation page — the recording ends at the Step 15 review confirm dialog. Sample data shown in the video is intentionally omitted (PII).
>
> **Drive mechanism: accessibility-tree primary (approach C).** The "Control / target" column names the visible label + control type, not a CSS selector.

## Portal URL
- **Account creation:** `publicaccess.uct.ac.za/psc/public/...UCT_ONL_HOME_FL.GBL` (page "Create Account")
- **Login + application:** `studentsonline.uct.ac.za/psc/students/...` (page "Online Application")
- Engine: **PeopleSoft Fluid** (`NUI_FRAMEWORK` / `PT_AGSTARTPAGE_NUI`). Left-nav wizard, 16 numbered steps, each with a status (Not Started / In Progress / Complete / Visited). **Save** + **Next/Previous** top-right.

### Interaction pattern (for the adapter — approach C)
Mostly **native `<select>` dropdowns** (target by visible label — good for accessibility-tree). A handful of modal pickers:
- **Postal Code** → PeopleSoft "Lookup" modal: Search Criteria (Postal Code / State / Suburb-Town-City, all "begins with") → Search → results grid (Postal Code · State · Suburb/Town/City · Post Office Box) → click row. (Suburb/Town/City then becomes a dropdown.)
- **School Search** → modal: Province dropdown + Search Name (**≥4 consecutive letters**, need not be the first letters) → Search.
- **Subjects** → "Subject Details" modal: Subject dropdown + percentage field(s).
- **Contact numbers / emails** → "+" opens an add-row modal.
- **Document upload** → "File Attachment" modal (My Device → file → Upload Complete → Done).

## Application window
- For the **2027** intake (video shows year selector = 2027). Opens 1 April; closes 31 July (per earlier research — _verify each cycle_).

## Account / login
- Credentials live in **Bitwarden** per Phase 3 plan §3 — _TBD: link entry._
- **Self-created account** (username + password chosen by applicant), separate from the application login host.

## Anti-automation measures ⚠️
- **Email OTP at account creation** — after "Create", a "Confirm Email Address" modal requires an **OTP emailed to the applicant (valid 15 minutes)** → Verify OTP. Headless automation needs inbox access. (No OTP seen at subsequent logins — _verify_.)
- **NBT registration is a separate portal** (`nbtests.uct.ac.za`, "National Benchmark Tests project" / CETAP) with its **own account, contact-info, test/venue booking, fee agreements**, producing an **NBT Reference number** that Step 10 consumes. Required for all SA-resident undergrad applicants (and mandatory for Commerce & Health Sciences). **Flag: this is a second, independent automation surface — likely out of MVP scope; the student may need to complete NBT themselves.**
- No captcha/image challenge observed.

## Page flow — Online Application, 16 steps
| # | Step | Notes |
|---|---|---|
| 1 | Introduction | Info only — see below |
| 2 | Personal Information | |
| 3 | Contact Details | |
| 4 | Parent/Guardian and Fee Payer Information | |
| 5 | Secondary School Information | |
| 6 | Tertiary Information | minimal for matriculants |
| 7 | Post School Activity | none for "completing school this year" |
| 8 | Programme Choices | 2 choices |
| 9 | Referees & Supervisors | skipped for undergrad |
| 10 | NBT Information | NBT reference (from separate portal) |
| 11 | Funding Information | |
| 12 | Housing Information | |
| 13 | Redress and Disadvantage Factor Information | |
| 14 | Document Uploads | **SA ID required** |
| 15 | Review Application | confirm dialog |
| 16 | Agreement and Submission | **not captured — TBD** |

> **Navigation:** the left-nav lets you jump to completed steps and there is a **Previous** button — the flow is **navigable**. **Confirmed (2026-06-03): the Previous button works**; the dictation's "can't go back once a section is complete" was a mistake.

### Account creation (pre-application)
First Name (as per SA ID/Passport) · Last Name · Date of Birth (calendar) · SA National ID / International Passport Number · Email · Repeat Email · Username · Password · Confirm Password → **Create** → email OTP → Verify → log in.
- **Username:** ≥10 chars · case-sensitive · only numbers/letters/hyphens/underscores/full-stops · may not be an email.
- **Password:** ≥16 chars · ≥1 special · ≥1 numeric · ≥1 lowercase · ≥1 uppercase.

### Step 1 — Introduction
Info only: after submission UCT emails an acknowledgement with the **applicant number + login** to monitor the application, and **instructions for submitting additional forms and documents** (so some documents are handled later, by email — not all in-portal).

## Form fields

### Step 2 — Personal Information
| Field | Control | Req | Options | Uniflo mapping |
|---|---|---|---|---|
| First Name (as per ID/Passport) | text | * | | first name |
| Middle Name (as per ID/Passport) | text | optional | | middle names |
| Preferred Name | text | optional | → **app gap** (prints on student card) | preferred name |
| Maiden Name | text | optional | | maiden name |
| Surname (as per ID/Passport) | text | * | | last name |
| Title | dropdown | optional | Associate Professor, Dr, Miss, Mr, Mrs, Ms, Mx, Professor | title |
| Date of Birth | date | * | | DOB |
| Sex | dropdown | * | Female / Male | sex |
| Home Language | dropdown | * | (Ndebele, …) | home language |
| Indicate Type of Citizenship or Residency in SA | dropdown | * | SA Citizen / … | citizenship |
| Race (Self-Declared) | dropdown | * | African, …, No Information | population group |
| SA ID Number | text | * | | national ID |
| Do you need assistance because of a disability? | checkbox | — | if ticked → support detail → **app gap** | disability |

### Step 3 — Contact Details
| Field | Control | Req | Notes | Uniflo mapping |
|---|---|---|---|---|
| Country | dropdown | * | South Africa | country |
| Postal Code | **Lookup modal** | * | Search Criteria (Postal Code/State/Suburb-Town-City) → results grid | postal code |
| Suburb/Town/City | dropdown | * | populated after postal code | suburb/city |
| Address Line 1 | text | * | | address line 1 |
| Address Line 2–4 | text | optional | | address lines 2–4 |
| Postal Address | group | — | "My postal address is the same as my home address" checkbox (default on) | postal address |
| Contact Numbers | "+" modal | * | Phone Type (Business / Fee / Home / Non-SA Cellular / **SA Cellular** / Term) + Country Code (auto, e.g. 027) + Telephone | phone |
| Email Addresses | "+" modal | * | Email Type (Personal) + Email Address | email |

### Step 4 — Parent/Guardian and Fee Payer Information
Rules: **under 18** → Parent/Guardian **and** Fee Payer required; **18+** → Parent/Guardian optional but **Fee Payer compulsory**. International applicants completing P/G must give SA Cellular or Other Telephone.
| Field | Control | Req | Uniflo mapping |
|---|---|---|---|
| P/G Title · First Name · Surname | mixed | cond. | guardian name |
| P/G SA ID Number / Passport Information | text | cond. | guardian ID |
| P/G Relationship | dropdown | cond. | (Brother, …) |
| P/G Email Address | text | cond. | guardian email |
| P/G Contact: SA Cellular · Work Telephone · Other Telephone | text | cond. | guardian phone |
| Is your parent/guardian address different from your postal address? | checkbox | — | → **app gap: guardian address** |
| Fee Payer Information | section | * | person responsible for fees (not the funder/bursary) |

### Step 5 — Secondary School Information
Year of first secondary exam · School has 3 or 4 terms (dropdown) · Grade 11 at same school as Grade 12? (checkbox) · Grade 12 school in RSA? · **School Search** modal (Province + name ≥4 letters) · Qualification (dropdown, e.g. NSC(DBE)).
**School Subjects** — tabs **Grade 11** / **Grade 12**:
| Tab | Modal fields | Table columns |
|---|---|---|
| Grade 11 | Subject (large dropdown) · **Grade 11 Final %** | Subject |
| Grade 12 | Subject · **April Results %** · **June Results %** | Subject · April Results % · June Results % |

→ UCT captures **Grade 11 final %, Grade 12 April %, and Grade 12 June %** per subject. Subject dropdown is a native list (Accounting, Advance Program English/Maths, Afrikaans/English 1st/2nd/Home Lang, Electrical Technology, Engineering Graphics & Design, Geography, Life Orientation, Life Sciences, Mathematics, Physical Sciences, Xitsonga, "Exempted: Mathematics", …).

### Step 6 — Tertiary Information
"Applied to UCT before?" / prior tertiary — minimal/blank for matriculants. _(fields TBD)_

### Step 7 — Post School Activity
For "completing secondary school this year" → no fields, just **Save**.

### Step 8 — Programme Choices
First choice + **second choice (optional)**:
| Field | Control | Req | Options |
|---|---|---|---|
| Level of Qualification | dropdown | * | Undergraduate |
| Faculty | dropdown | * | Commerce · Engineering/Built Environment · Humanities · Law · Science |
| Academic Qualification | dropdown | * | (e.g. Bachelor of Science, Bachelor of Laws) |
| Specialisation or Major | dropdown | * | (Applied Mathematics, AI, Biochemistry, Biology, Computer Engineering, Computer Science, Genetics, Mathematics, …) |
| Second Specialisation or Major | dropdown | cond. | |

### Step 9 — Referees & Supervisors
"Your Programme Choices do not require a referee or supervisor" → **Save** (skipped for undergrad).

### Step 10 — NBT Information
Consumes the **NBT Reference number** obtained from the separate `nbtests.uct.ac.za` portal (+ year/exam date). See anti-automation note — NBT is its own registration + booking flow.

### Step 11 — Funding Information
"Have you received NSFAS funding from another Institution?" (checkbox) · "Do you need financial assistance for this programme?" (checkbox). + NSFAS info.

### Step 12 — Housing Information
_(fields TBD — step exists, marked Complete in video.)_

### Step 13 — Redress and Disadvantage Factor Information
All dropdowns (used to compute redress category + disadvantage factor → Weighted Points Score):
- Mother's racial classification under apartheid · Father's racial classification under apartheid — options: Black, Chinese, Coloured, Indian, White, "I choose not to answer", "I do not know", "My parents did not reside in SA during apartheid".
- Mother's first language.
- Highest education of mother/female guardian · of father/male guardian (e.g. Matric / Grade 12 / Senior certificate) · by any grandparent.
- Does/did your family receive a child-support grant on your behalf? (incl. "I do not know").
- Does/did your family rely on a social pension from the State?

### Step 14 — Document Uploads
- Rules: one file per document; combine multiples first; permitted types **.doc .docx .htm .jpeg .jpg .odt .pdf .rtf .tif .xls .xlsx**.
- Shows the Choice 1 / Choice 2 summary, then an upload grid (Document · Choice Number · File · Upload).
- **Required: `*SA Identity Document` (Choice Number = All).** Upload via "File Attachment" modal (My Device).
- → **Corrects UJ contrast: UCT *does* require an ID upload in-portal.** (Other supporting docs may follow by email per Step 1.)

### Step 15 — Review Application
Collapsible review of every section; confirm dialog: *"Do you confirm that all the information provided has been reviewed and is correct?"* → Yes/No.

### Step 16 — Agreement and Submission
**Terms and Conditions** page (captured via screenshot): *"Please read the Terms and Conditions agreement below. By submitting your application you agree to these Terms and Conditions."* Followed by an **Agreement / declarations list**: abide by the University's rules · responsible for payment of all fees & arrears (per the fee booklet) · confirm having read the **Privacy Notice** · if currently completing secondary school, UCT may communicate with the school about the application · waive claims against UCT for damage/loss · not expelled/rusticated/excluded from another university · if a minor, parent/guardian consent · information is complete & accurate (non-disclosure / false declaration can lead to cancellation). Footer: *"I confirm the above declaration and hereby submit my application."* Buttons (top-right): **Submit** / **Do not Accept**.

## File uploads
| Field | Required | Accepted types | Notes |
|---|---|---|---|
| SA Identity Document | **yes** | .doc .docx .htm .jpeg .jpg .odt .pdf .rtf .tif .xls .xlsx | one file; combine multiples |
| Other supporting docs | varies | same | some handled later via the post-submission email (Step 1) |

## Submission confirmation
- Sequence: Step 15 Review (confirm the "reviewed and correct" dialog) → **Step 16 Agreement and Submission** → click **Submit** (decline = **Do not Accept**).
- The submit control is the **Submit** button on the Step 16 Terms & Conditions page.
- Post-submit **success** page (URL + DOM markers): still **[VERIFY]** — the submit *screen* is captured but not the page shown after clicking Submit. Reliable success signals: the application status flips from "In Progress", and UCT **emails an acknowledgement with the applicant number** (out-of-band).

## Uniflo mapping & app gaps
- **Preferred name** (prints on student card), **disability support detail**, **guardian address** — capture in the app.
- **Marks granularity:** UCT wants Grade 11 final %, Grade 12 April %, Grade 12 June % per subject — richer than other portals. Store enough to populate all three.
- **NBT reference** — needs to exist before Step 10; treat NBT as a separate prerequisite/flow.
- **Fee payer** vs funder distinction — fee payer is the person responsible, not a bursary/NSFAS.
- Cross-check every mapping against `student_profiles` / `academic_records` columns. **[VERIFY against schema]**

## Screenshots
- Frames extracted from `uct.mp4` (1 per ~45s) to a local scratch folder — **not committed**. TODO: export key page shots to `screenshots/uct/`.

## Open questions / to verify
- [x] Step 16 (Agreement & Submission) content — **captured** (Terms & Conditions + Submit / Do not Accept).
- [ ] Post-submit **success** page (URL + markers) shown after clicking Submit.
- [x] Navigation — **confirmed: Previous button works, flow is navigable** (2026-06-03); the "one-way" note was a mistake.
- [ ] Step 6 (Tertiary) and Step 12 (Housing) exact fields.
- [ ] Whether email OTP recurs at login or only at signup.
- [ ] NBT: confirm whether automation attempts NBT registration or leaves it to the student.

---

## Appendix — raw dictated walkthrough
> Original unedited notes, kept as the source for anything the video doesn't show.

So when you log in to the portal, There's gonna be a bunch of options. You're gonna click create account because you don't have one yet. So information needed here is first name as per your SAID or whatever document you're using, last name, your date of birth, which there's gonna be a button to press to select, your South African national ID slash your passport number, your email address, then you have to repeat your email address, then you have to form a username. The username has some requirements. It must be at least ten characters in length. Usernames are case sensitive, can only contain numbers, letters, hyphens, underscores and full stops. An email address may not be used as the username. And then you're gonna put in your password and confirm your password. Your password must be at least sixteen characters in length, contain one special character at least, at least one numeric character, one lowercase character, and one uppercase character. After create... present create, you're gonna present an OTP to your email. You're gonna go to your email, get the OTP, and then click verify OTP. After everything, you'll be redirected to to the login page. We're gonna use whatever username you had, plus your password to log in. after you log in, there's gonna be options to choose from. Below, you click undergraduate because that's what we'll be applying for at this stage and time. verify year u are applying for and then click start application

Okay. So there's gonna be sixteen steps, much like the one we did for wits The only caveat with UCT's application is that as soon as you complete a setting, you can't go back. So you have to verify and make sure that you're submitting accurate information for UCIT. is going to be a next button at the top right corner whenever you're done completing everything. The first one is just an introduction, then we'll move on to personal information. Personal information of your first name, preferred name, this I think we should ask the student because from my experience, the preferred name is what is gonna be put on their student card, so they should have as much control on that as much as they want. There's maiden name and an option, surname, date of birth, home language, race, SAID number, and then the title whether they are mister, missus, professor, and then their citizenship in South Africa. And then they have to, uh, specify whether or not they have any disabilities. Fluidicity is a thick gas jamming disability. It's gonna be a drop down where you can choose what disability you're affected by. They also have a shield where you have to specify what support you currently do have. So do make note of that so we can also add it to the app itself. So the flow with u c t is after you done filling in any information, you're gonna press save, then you're gonna click next. So next one would be contact details. So you have to fill in your country, postal code, suburb slash town slash city, address line one, two, three, four, but owner address line one is compulsory. That's your home address. On the right side, there's the postal address, but you have the option to keep it the same as your home address. So the country and then the suburb will be drop downs. The the drop down for suburbs slash town city will be based on whatever postal code you put in, which is good to know. Still within contact details, there's gonna be a place for contact numbers and email addresses. You click the plus sign there to add a new new row. You're gonna select one of our phone type, input the country code, and then the actual number. For emails, you select the email type and the actual email address is what you put The next is parent guardian formation, so the gods for the title, SAID number, or whatever identification. First name, surname, relationship to the applicant, and email address. And then contact numbers will be required to SA cellular. They're gonna ask if your parent or guardian's address, if it's the same, just say it's the same. If not, you might have to put in the the address too. So that's another thing to note to make sure. We also ask for the parent or guardian address in case it might be different? There's going to be a few pain formation. Just list the parent guardian as the fee payer for simplicity sake. So step five is school information. You're gonna select the year you're completing or completed your secondary schooling examination for the first time. And then indicate whether your school has three or four terms. Did you complete the eleventh at the same school as grade twelve? Is your grade twelve or equivalent school in the Republic of South Africa? And then you're gonna have to press find school and then input the school name. So Still living qualification of the Dropbox, just choose the appropriate one which will be NSC. After all that would be prompted to add in grade level final results in grade twelve April results. So you have to click from a drop down then add the actual mark for each of those. Step six is basically just tertiary information asking if it applied to UCT before. You can leave that as blank. Any postal activity, we can leave that as breakers. We don't anticipate that from a trade student yet because they're still in school. And then we're gonna move on to step eight, which is program choices. UCT gives you... lets you choose two options, one compulsory and one other. Gonna choose your level of qualification. You should be undergraduate. Faculty, academic qualification, which will be a bachelor of science in in the science faculty, and then the specialization or whatever major people wanna be doing. the next step of the problem choices will be referees and supervisors, but for most people, they won't need that so we can skip that. An important part, especially for UCT, is step ten and b t information. It has to import your NBT registration number and the year you're gonna write the NBT or have written it in. the nbt exam date will also be required. The next step, eleven of sixteen, is about funding. There's gonna be options to ask if you've received just first funding from another institution or whether or not you require financial  assistance for the program. next step asks if student wants to be considered for student housing

The next part is redress and disadvantage factor inflammation. It will be asked for both your father and mother's racial classification during apartheid. the highest level of education, highest level of education by any grandparent, and does your family rely on social pension from the state? Under racial classification, there's multiple options to choose from. Black, Chinese, colored, Indian. You can choose not to answer. You have the option to say do not know, to say that your parents did not resign and say during apartheid or that they were white. also asked for your mother's first language Yeah. There are service tires, level of education of your father slash male guardian. Does your family receive child support grant on your behalf? for each of these there is a i do not know option. they are all dropdown selections. next is document uploads asking for sa id document. the last step is a review application
