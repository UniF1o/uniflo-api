# Wits — Portal Research

> **Status: Draft.** Reformatted from the dictated walkthrough + Notion screenshots (research dated 2026-05-17). DOM selectors, exact required/optional flags, validation rules, and the submission-confirmation markers still need a verification pass against the live portal. Unknowns are marked `_TBD_` or **[VERIFY]**. Raw dictation preserved in the appendix.

## Portal URL
- Login: <https://self-service.wits.ac.za/psc/csprodonl/UW_SELF_SERVICE/SA/c/VC_OA_LOGIN_MENU.VC_OA_LOGIN_FL.GBL?Page=VC_OA_LOGIN_FL&Action=U>
- Engine: PeopleSoft / Oracle (same family as UCT and UP).

## Application window
- **30 June 2026:** Faculty of Health Sciences (all programmes), Bachelor of Architectural Studies, Bachelor of Audiology, Bachelor of Speech-Language Pathology, BA Film & TV.
- **30 September 2026:** All other undergraduate programmes + Residence applications.
- Source: <https://www.wits.ac.za/undergraduate/apply-to-wits/>

## Test account
- Credentials live in **Bitwarden** per Phase 3 plan §3 — _TBD: link Bitwarden entry._ (Deliberately not committed.)
- Wits emails a **system-generated temporary ID + temporary password**; applicant then sets a permanent password.

## Anti-automation measures ⚠️
- **Security code (6-character image)** on the Create-Temporary-ID page — "type the six characters shown". Requires OCR/computer vision to solve headlessly. Flag as a **blocker candidate** — raise in the Sunday sync before week 10 if vision solve is unreliable.
- **Email delivery of temp credentials** — automation needs inbox access to read the temp ID + password.

## Application flow (pages in order)

### Step 1 — Create temporary ID
1. **Create temporary ID**.
2. **Nationality** (dropdown, default South Africa):
   - SA → National ID Type prefilled → enter **ID number**.
   - Non-SA → asked about **permanent residency**:
     - PR holder → PR certificate + BRSA national ID (+ further fields). **[VERIFY exact fields]**
     - Non-PR → passport number (+ further fields). **[VERIFY]**
3. **Applicant details:** title, first name, middle name(s) (nullable), surname, DOB (day dropdown / month dropdown / year typed), gender, email, country code (+27 prefilled) + mobile (last 9 digits).
4. **Security check:** enter the 6-character security code shown (see anti-automation).

### Step 2 — Set permanent password
Temp ID + temp password arrive by email → enter them in the confirmation tab → redirected to a password-reset page → set a permanent password.

### Step 3 — Log in & begin application
1. Log in with temp ID + permanent password.
2. **Apply for admission** → Application action dropdown: *Begin new* / *Continue existing* → **Begin new** → application ID is displayed.
3. Application type (Undergraduate full-time) · Academic year (default current+1) · Academic calendar (default January).
4. Application proper: nominally **17 steps**, collapsed to ~6 shown. "Next" top-right.

### Steps (collapsed)
| Step | Page | Notes |
|---|---|---|
| — | Personal details | title, first/middle/last name, DOB, gender — prefilled from Step 1 → **skip** |
| — | Current activities | matriculants pick **School**; "+" to add a **sport** → app gap |
| — | Secondary education | see fields |
| 5 | Tertiary studies | "Previous/current tertiary?" → **No** |
| — | Study choices | **3 choices** (1 compulsory, 2 optional) |
| Step 4 (addresses) | Domicilium / residential / postal | see fields |
| — | Contact details | email + mobile prefilled; optional home/work phone |
| — | Demographic details | see fields |
| — | Next of kin | see fields → app gap (NOK address) |
| — | Emergency contact | "same as next of kin" option → app gap |
| — | Indemnity | accept terms → handling note below |
| — | Payment | R100 fee → handling note below |
| — | Document uploads | see uploads |
| — | Submit + **Validate applicant** | run validation to catch errors |

## Form fields

### Applicant details (Step 1)
| Field | Type | Required | Options / validation | Uniflo mapping |
|---|---|---|---|---|
| Title | dropdown | yes | Admiral, Advocate, Ambassador, Associate Professor, Bishop, Captain, Colonel, Doctor, Father, Honourable, Justice, Lieutenant, Lt General, Miss, Mr, Mrs, Ms, Mx, Professor, Professor Emeritus, Rabbi, Rev, Sister | profile title |
| First name | text | yes | — | profile first name |
| Middle name(s) | text | optional (nullable) | — | profile middle names |
| Surname | text | yes | — | profile last name |
| DOB day / month | dropdown | yes | split selectors | profile DOB |
| DOB year | text | yes | typed | profile DOB |
| Gender | dropdown | yes | Female / Gender Neutral / Male | profile gender |
| Email | text | yes | — | profile email |
| Country code + mobile | text | yes | +27 prefilled, last 9 digits | profile phone |

### Current activities
Options: currently upgrading matric / employed / gap year / school / university → matriculants pick **School**. Optional **sport** via add button. → **app gap: capture current-year activity + sport.**

### Secondary education
School (type + select) · Examining authority (province) · Examination year · Examination month · Examination number (if available) · Final grade 11 results (subject dropdown + marks) · Secondary education type (South African) · Current school status (currently grade 12 / completed grade 12 / upgrading) · Grade 12 trial results (if applicable). **[VERIFY full subject list / mark format]**

### Study choices
3 choices total. Academic program (the qualification) · Academic plan (≈ faculty, e.g. *BSc Engineering*). **[VERIFY]**

### Step 4 — Addresses
| Field | Type | Notes |
|---|---|---|
| Domicilium: country | dropdown | — |
| Domicilium: address line 1, line 2, suburb | text | suburb typed |
| Address search | button | autofills **city, postal code, province** |
| Residential address | group | "same as other address" → reuse domicilium |
| Postal address | group | "same as other address" → reuse domicilium |

### Demographic details
Marital status (dropdown) · Population group · Home language · Religious affiliation · Disability (yes/no → if yes, disability dropdown).

### Next of kin
Name, title, initial, surname, phone numbers, relationship to applicant, email, **NOK address**. → **app gap: store next-of-kin address.**

### Emergency contact
"Use same details as next of kin" button; else relationship, contact name, mobile, additional emergency phone. → **app gap: allow emergency contact distinct from NOK.**

## File uploads
| Field | Accepted types | Size limit | Naming | Notes |
|---|---|---|---|---|
| ID document / passport copy | _TBD_ | _TBD_ | _TBD_ | **Must be certified < 3 months ago** |
| Matric certificate | _TBD_ | _TBD_ | _TBD_ | Or final grade 11 results if no matric yet |

## Submission confirmation
- Confirmation URL: _TBD_ **[VERIFY]**
- DOM markers / confirmation text: _TBD_ **[VERIFY — capture for `verify_submission()`]**
- **Payment + indemnity gate before final submit** — see handling notes.

## Uniflo profile mapping & app gaps
- **Current-year activity** (school / gap year / upgrading / employed / university) + **sport**.
- **Next-of-kin address** and a **separate emergency contact** (not always the same person).
- **Indemnity handling:** student must accept terms. Open design question — save the indemnity link and have the student accept it themselves (transparency) vs. auto-accept. **Decide with Partner A.**
- **Payment handling (R100 fee):** we do **not** process payments. Capture the fee + bank details and surface them to the student (don't auto-pay). Avoid the self-service payment portal path in automation.
- Confirm all mappings against `student_profiles` / `academic_records` before adapter work. **[VERIFY against schema]**

## Screenshots
- Source: Notion → *Uni Research / WITS* (presigned links expire; steps 1–4 captured there).
- TODO: export PNGs to `docs/phase-3/portal-research/screenshots/wits/` and reference them here.

## Open questions / to verify
- [ ] Non-SA / PR applicant field sets (out of MVP scope but document).
- [ ] Reliability of OCR on the 6-char security code — **blocker check**.
- [ ] Full subject list + mark entry format for grade 11/12 results.
- [ ] Submission-confirmation URL + DOM markers.
- [ ] Indemnity acceptance approach (decide with Partner A).
- [ ] Payment-details capture approach.

---

## Appendix — raw dictated walkthrough
> Original unedited notes, kept as the source of truth for the structured sections above.

First thing on the portal ⇒ press "create temporary id"

So click the drop down for nationality. If choosing South African, national ID type will just already be chosen for you, and then all you have to do is write your ID number under national ID. If you choose anything besides South Africa, you're gonna have to specify whether or not your South African permanent residence and input in your passport number. For nonpermanent or for people who aren't from South Africa, they are gonna have other fields to fill in afterwards, such as PR certificate and BRSA national ID, etcetera, etcetera.

After that, now you put in applicant details. We're just gonna be the name, title. There's a drop down where Basically, they're just filling in miss the missus. They're gonna put in your first name, middle names, surname, date of birth, date of birth the month, and then date of birthday. Yes. We will separate it. Do you have the day, you have the month, then you have the year. Day and month are drop downs, and then, yeah, you have to fill in yourself. Then you have to fill in your gender. Options for gender are female, gender neutral, or male. After that you're gonna fill in your email address and then country code and mobile number. So you're gonna put in whatever country code you're using, and then the rest of the digits. After that, there's gonna be a security check where essentially you're gonna have to use computer vision to see what digits are being displayed there. Put the security code, whatever it is, into the security code field, and then you can press continue.

After that, Become a regional play, you can at least confirm temporary password. When you click that, you're gonna be prompted into your place with user details, filling the email address, filling whatever temporary ID was received, and then you fill in the password, which is the temporary password you received. And then after that, you're gonna click okay. After that you will be redirected to a new page where you will actually make a password, and then from now on you will use that password you've actually made. after saving it and whatnot.

After that, they came back to the main page where there's gonna be some temporary ID and the password you've actually made now. So you're gonna fill in your temporary ID and the password, and then click the login button. Moving on to the Apply for admission page, there's going to be a drop down application action where it's going to be begin your application or continue existing application. As of now, we're just going to be beginning a new application. After that, after we select beginner, pick new application, our application ID will be displayed. Application type, that's when we're gonna choose undergraduate full time. Academic care is whatever year we're applying to be in. then just leave academic calendar as january

So now after all of that, we're gonna come to step one or seventeen. Welcome to wits online application. I just don't know where this is gonna be. Next button on the top right of every one of these, this is built off Oracle's application service that wits uses, much like UCT. After that, there's gonna be... when you do click next, however, it it summarizes back... instead of seventeen pages, it'll only show you, like, six of them. The next page to fill will be personal details, the fields in personal details are title, first name, middle name, last name, date of birth, and gender. All of this is gonna be processed from beforehand, so that can be skipped. And then moving on to current activities since we are mainly gonna be dealing with matric students, We should just click school. We should make a note of this too to add to uniflo so people can specify what they were doing that year. The options are currently upgrading matric employed, gap year, school, or university. There is also an additional sports button where you can add a sport to those people who would be adding sports. Maybe also add that to the app as a thing to ask for, but we can see as time goes on. So, like like I said, the the next things you do after the event is you choose before. If... because you have chosen school and current activities, the next step becomes secondary education So after selecting one of the schools, be ready to go. When you press the school button, it's gonna be forced to type in whatever school you attended and then click it from the options. Grade twelve particulars, examining authority, you're gonna click whatever province the student has. The examination year, examination month, and exam number if available. And then after that, you're gonna fill in the final grade eleven results. There's gonna be a drop down for subjects and then a place to type in the marks to . So secondary education type, you just click South African. Current school status, whether you are currently grade twelve or complete grade twelve or upgrading. And then there's gonna be a select school button where you're gonna look for the actual school that the student attended. Depending on what on the fifth and grade twelve, after grade eleven is asked the grandskilophone trial results, two at full matriculin incisions keep this as a copy of grade eleven to people who have actually done grade twelve should put in their actual grade twelve marks to the same way in which they did for grade eleven. Step five, ask if you have any previous or current tertiary studies. You're just gonna leave it as no, and then move on to the next choice. So next step would be studying choices words allows you to choose three one compulsory two optional, so does the webian academic program. We... they actually choose whatever it is that you want to apply for... that you're applying for. Academic plan is basically, like, the faculty. So you can get a bachelor of science in engineering, bachelor of science in whatever it is that's happening. And then, yeah, net is the domicillum address So the fields in here are country, which will be a drop down. You're gonna put in address line one, address line two, then suburb. In suburb, you have enter the suburb Dalla addresses a residential address just click same as other address and assume step nine postal address, which is also put it as the same as domicilem. and then press address search button. And then to automatically put city, postal code, and province for you. For the next few addresses, residential address, just keep it the same. It... there's gonna be a same as other address. Just keep it the same as the domicili um address. and then do the same thing for the postal address that's gonna be next. For contact details, do you still have your email address from before, and they still have your mobile phone number? You could optionally add home phone and work phone, but for now, we'll just leave that alone. Now moving on to demographic details. Miracle status, you're gonna put that in. There's a drop down. Population group, home language, religious affiliation, and they ask whether or not you have a disability. If you do have a disability after sleeping years on the drop down, it's gonna prompt you to select which disability you do have. The next step is to fill in the next of kin's details. It's gonna be the name, title, initial, surname, phone numbers, relationship to applicant, and email address, and then there's gonna be the next of kin's address, which is something we should also add to the app. So to take note of that, we After that, there will be emergency contact details. There's a button to to use same details as next of kin. If people want to specify someone different other than next of kin as an emergency contact, do keep that in mind too. We're gonna need to store the relationship to applicant contact name, mobile phone, and additional emergency contact phone.

The next part is an indemnity, where the student will have to accept. I don't know how we should handle this one, whether or not we should save the link, send it to the students so they can go click it themselves for the sake of transparency and being honest within the app. So you can advise them on how we go about doing that, Claude. After that, though, there's gonna be payment where there's a hundred grand application fee. So I think with our services, we don't probably stop on that page and then save that link and then direct the user to there so they can handle the payment because don't handle that at this stage. Okay. Regarding the payment stuff, basically, what this university does is they show you how much an application fee is, which is hundred rand, and then they give you details on how to pay for them. I think we should find a way to save these details and then send them to a student so that they can see. Because after this, there's going to be document uploads, and the documents that they are required to upload is a copy of their ID document and final grade eleven results.

Make sure to press validate applicant to make sure no errors were done in the application
