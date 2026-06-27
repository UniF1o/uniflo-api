# Portal branch-mapping plan

> **Purpose:** The original portal walkthroughs covered one path per portal — a current Grade 12 student (UCT: completed-matric / gap-year). This document tracks what still needs to be walked: every non-transfer applicant-type branch across all portals, so the automation knows which fields appear and what they require for each kind of student. Stellenbosch University is a net-new portal being onboarded here for the first time.

---

## Hard rules — read before starting anything

1. **Never submit, never pay.** Stop before any final Apply / Submit / Pay button. These are live portals; a submission triggers real processing.
2. **Mark the checklist as you go.** After completing each track for a portal, edit this file and change `[ ]` to `[x]` in the completion checklist at the bottom, then commit. Do not batch up checkmarks at the end — mark each item the moment it is done so progress is visible at any time.
3. **Write findings immediately.** After each branch, append the findings to the portal's research doc before moving to the next branch. Do not keep notes in memory and write them all at the end.
4. **One portal per session.** Finish all branches for a portal before starting the next one. This keeps context tight and prevents session conflicts.
5. **University transfer paths are out of scope.** If you encounter a "previously enrolled at tertiary" or "transfer" option: select it, screenshot the fields that appear, note their labels, then stop. Do not map sub-fields or navigate further down that path.

---

## Background — what this research is for

UniFlo automates university applications on behalf of students. The backend adapters (`app/automation/adapters/`) fill in each portal's form using data from the student's profile. Currently the adapters only handle one applicant type — a student who is still in Grade 12. To support other students (gap year, repeating matric, employed, etc.) the adapters need to know:

- Which field controls the applicant type on each portal
- What other fields appear or become mandatory when a different applicant type is selected
- What the exact option strings are (they differ per portal and must match exactly)

This research populates the branch maps that the adapter logic will eventually read.

---

## How to do this — methodology

### Tools

Use the **Playwright MCP** tools (`mcp__playwright__browser_*`) to drive the browser. These are already available. Load them with:

```
ToolSearch: select:mcp__playwright__browser_navigate,mcp__playwright__browser_snapshot,mcp__playwright__browser_take_screenshot,mcp__playwright__browser_click,mcp__playwright__browser_select_option,mcp__playwright__browser_type,mcp__playwright__browser_fill_form,mcp__playwright__browser_wait_for
```

Use the **Gmail MCP** (`mcp__claude_ai_Gmail__*`) if any portal sends an email (e.g. OTP or account details). The inbox is `unknown.user.jane.doe@gmail.com` — search threads there.

### General approach (applies to all portals)

1. **Navigate** to the portal URL.
2. **Login** using the credentials in the test accounts table below.
3. **Take a snapshot** (`browser_snapshot`) to read the accessibility tree and find the branching field. Always target elements by their visible label or role — not by CSS class or id — because the portals use generated ids that change.
4. **Open the dropdown / change the radio** using `browser_select_option` (for `<select>` elements) or `browser_click` (for radio buttons and LOV links). For ITS LOV popups (UJ only), click the LOV icon next to the field to open the picker, then click the target row.
5. **Take a screenshot** with `browser_take_screenshot` after each change. Save it to the path specified for that portal.
6. **Read the page** with another `browser_snapshot` to see which new fields appeared.
7. **Document the findings** in the portal's research doc before moving on.
8. **Reset** by changing the field back to the original value before moving to the next track.
9. **Mark the checklist** in this file and commit.

### How to handle captchas (UP and Wits only)

Both UP and Wits use an image captcha that can be decoded without OCR — the characters are embedded in the image filenames in the DOM. You do not need to actually read the image.

**UP:** Use `browser_snapshot` or `browser_evaluate` to read the `src` attributes of the six captcha `<img>` tags. Each filename follows the pattern `UP_{case}_{char}_{seq}.JPG` where `L` = lowercase and `U` = uppercase. Read all six in order and type the decoded string into the Security Code field.

**Wits:** Same scheme with a `VC_` prefix. E.g. `VC_L_Y_1.JPG` → `y`.

For the existing accounts in this plan, captcha is only needed if you must create a fresh account. Since all four original portal accounts already exist, you should be able to re-login without hitting the captcha. Only Stellies will need captcha handling at account creation (if it has one).

### How to navigate backwards in a wizard

UP, Wits, and UCT use a left-nav wizard. To go back to an earlier step:

- **UP / Wits:** Click the step name in the left navigation panel. Most steps remain editable even after being marked Complete.
- **UCT:** Click the step number in the left navigation. The instance is parked at Step 15 — navigate back to whichever step has the branching field.
- **UJ:** Uses a page-by-page form with Previous buttons at the bottom of each page.

If the portal blocks navigation back (e.g. a step is locked after submission), note that in the research doc and move on.

---

## Synthetic applicant — Jane Doe

This identity is used for every portal. It is entirely fictitious. Never substitute real student data.

| Detail | Value |
|---|---|
| Full name | Jane Doe |
| Date of birth | 14 May 2008 (`2008-05-14`) |
| SA ID number | `0805140001084` |
| Email | `unknown.user.jane.doe@gmail.com` |
| UniFlo app password | `JaneDoe@2027` |

The email inbox is accessible via the Gmail MCP connector (`mcp__claude_ai_Gmail__*`). Use it to read OTPs and emailed credentials without manual copy-pasting.

## Portal accounts

All existing accounts are parked mid-application. Re-login and navigate to the branching section — do not create fresh accounts unless the portal has locked the session and re-login truly fails.

| Portal | Login | Password | Parked at |
|---|---|---|---|
| UJ | no pre-login — enter via POPI gate each time | n/a | Page D (no student number — never submitted) |
| UP | Application ID `T4005778` | `JaneDoe@UP2027` | Mid-application, Verify not clicked |
| Wits | Temporary ID `T1872394` | `JaneDoe@Wits27` | Wizard parked (indemnity not accepted, Submit never clicked) |
| UCT | username `jane.doe.2027` | `JaneDoe@UCT_2027` | Instance `UCT_ONLAPP1428528` at Step 15 |
| Stellies | TBD — account to be created | TBD | Not started |

### Additional account notes

**UJ:** No student number is ever assigned until final submission — which we never do. Each session re-enters Jane's biographical data from Page 0 (POPI gate). The application state is not saved server-side between sessions.

**UP:** The account was created with a DOM-decoded captcha (pattern `UP_{case}_{char}_{seq}.JPG`). The password was changed from the emailed temporary to `JaneDoe@UP2027` on first login. Application is parked before Verify — the Apply button is visible but was never clicked.

**Wits:** Temporary ID `T1872394` was issued by the portal after account creation (captcha `e5qn2n`, DOM-decoded). The temporary password was Jane's DOB as `yymmdd` (`080514`). Permanent password was set to `JaneDoe@Wits27`. The wizard is parked at Step 17 with indemnity not accepted and Submit never clicked.

**UCT:** Username `jane.doe.2027`, password `JaneDoe@UCT_2027`. No OTP is sent at subsequent logins — only at original account creation (already done). The instance `UCT_ONLAPP1428528` is parked at Step 15 In Progress; the review confirm dialog was dismissed (No). Steps 1–14 are saved Complete.

### Login steps per portal

**UJ:** Navigate to the application portal. Accept the POPI agreement on Page 0. Fill in the biographical details on Page A using the synthetic applicant data. UJ does not issue a student number until final submission, so there is no pre-existing account — you re-enter the biographical data each session and work through the pages from scratch.

**UP:** Go to `upnet.up.ac.za/psc/upapply/...`. On the landing page, choose "login to continue / view study application" from the "I want to" dropdown. Enter Application ID `T4005778` and password `JaneDoe@UP2027`.

**Wits:** Go to `self-service.wits.ac.za/psc/csprodonl/...`. On the login page, enter email `unknown.user.jane.doe@gmail.com`, Temporary ID `T1872394`, and password `JaneDoe@Wits27`.

**UCT:** Go to `studentsonline.uct.ac.za`. Login with username `jane.doe.2027` and password `JaneDoe@UCT_2027`. No OTP is sent at subsequent logins — only at the original account creation (already done).

**Stellies:** Find the application portal URL by checking `sun.ac.za` for an "Apply" link or a dedicated apply subdomain. Document the URL in `stellies.md` immediately.

---

## Tracks to cover

| Track | What it means |
|---|---|
| Completed Grade 12, prior year | Student has the NSC certificate already (finished matric in a previous year) |
| Repeating matric / upgrading marks | Student is re-sitting NSC exams to improve their marks |
| Gap year | Student finished school but is not studying or working formally |
| Employed / working | Student is post-school and in employment |
| International applicant | Non-SA exam authority, non-SA ID document |
| ~~University transfer~~ | Out of scope — note the fields exist, do not map sub-fields |

"Still in Grade 12" is already done for UJ, UP, and Wits. UCT was walked as completed-matric / gap-year, so gap year is done for UCT.

---

## Output format

For every track you walk, append to that portal's research doc under a new heading. The research docs are at `uniflo-api/docs/phase-3/portal-research/<slug>.md`.

```markdown
## Branch mapping (YYYY-MM-DD)

### Track: <track name>

**Trigger field:** <field label and location in the form>
**Option selected:** <exact string as it appears in the dropdown / radio>
**Fields revealed:** list each field label, control type, and whether required
**Fields hidden:** list
**Validation changes:** e.g. "Examination Number becomes mandatory", "Grade 11 slot disappears from Documentation"
**Notes:** any other behaviour differences vs the standard path
**Screenshots:** `screenshots/<slug>/branch-<trackname>/`
```

Screenshots go in `uniflo-api/docs/phase-3/portal-research/screenshots/<slug>/branch-<trackname>/` with descriptive filenames, e.g. `step3-gap-year-selected.png`.

---

## Portal 1 — UJ

**Research doc:** `uniflo-api/docs/phase-3/portal-research/uj.md`
**Screenshots:** `uniflo-api/docs/phase-3/portal-research/screenshots/uj/branch-*/`
**Account:** no pre-login — fill biographical data from scratch each session

Read `uj.md` before starting. It documents the full page flow and the ITS Integrator interaction pattern (LOV popups, JSText eval steps, etc.).

### Branching fields to target

#### Page C — Endorsement LOV

This is the matric-status field. It is an ITS LOV (a popup picker, not a native `<select>`). Click the LOV icon next to the Endorsement field to open it. Read every option in the picker — record the full list with exact strings.

The "CURRENTLY IN GR.12" option is already covered. For each other option:

1. Click the option to select it and close the picker.
2. Take a screenshot of the full Page C form.
3. Note: does an Examination Number field appear or become mandatory? Do the subject rows change format? Does any block appear or disappear?
4. Record all observations in `uj.md`.

Expected options (exact strings to be confirmed from live portal):
- `CURRENTLY IN GR.12` — already done
- A completed / final matric option
- A repeating / upgrading option
- Possibly others — capture the full list

#### Page D — "What are you currently doing?" LOV

Same ITS LOV pattern. Click the LOV icon to open, read every option, record them all.

For each option that has not been walked:
1. Select it.
2. Screenshot the full Page D state.
3. Note: does a new sub-section appear (employment details, gap-year date range, institution name)?
4. If a tertiary / transfer option appears — select it, screenshot, note the field labels, then stop. Do not fill in or navigate further.

#### International branch — Page C

Find the SA / International radio or toggle on Page C. Switch to International.

Screenshot the full Page C. Record:
- Which exam-authority options appear (dropdown or LOV — capture all)
- What qualification-type field appears (all options)
- Any "extra sittings" or additional sub-fields

After screenshotting, switch back to South African before leaving Page C.

---

## Portal 2 — UP

**Research doc:** `uniflo-api/docs/phase-3/portal-research/up.md`
**Screenshots:** `uniflo-api/docs/phase-3/portal-research/screenshots/up/branch-*/`
**Account:** Application ID `T4005778` / `JaneDoe@UP2027`

Read `up.md` before starting. It documents the PeopleSoft OAP interaction pattern (native `<select>` dropdowns, postcode modal, study-choice modal, etc.).

Login, then use the left-nav to jump directly to whichever section has the branching field.

### Branching fields to target

#### Demographic Details — "Tell us more"

This is a native `<select>` dropdown. Navigate to Demographic Details. Use `browser_snapshot` to find the dropdown labelled "Tell us more". Open it and record every option with its exact string — the full list must be captured even for options you are not walking.

"I am currently still in high school" is already done. For each remaining option:

1. Select the option using `browser_select_option`.
2. Screenshot the full Demographic Details section.
3. Navigate to other sections (Secondary Education, Documentation) and screenshot those too — some options may affect fields on other pages.
4. Note everything that changed vs the high-school path.
5. Return to Demographic Details and reset to the original value before the next track.

#### Secondary Education — Completed matric path

Navigate to Secondary Education. Change two fields:
- **Highest grade completed** → Grade 12
- **Exemption Type** → the completed-matric option (find and record the exact label from the live LOV)

Screenshot the full Secondary Education section. Then navigate to Documentation and screenshot that too. Note:
- Did an Examination Number field appear or become mandatory?
- Did the Documentation section change (Grade 11 Results slot removed? Grade 12 Results slot added or changed label)?
- Did any other section unlock or change?

Capture the full Exemption Type option list.

Reset both fields before leaving Secondary Education.

#### Personal Information — Non-citizen branch

Navigate to Personal Information. Change Citizenship Status to the non-citizen option.

Screenshot. Note:
- Which Country-of-Citizenship field appears
- What happens to the SA National ID field (does it disappear? Does a Passport Number field replace it?)
- Any downstream changes to other sections

Capture the full Citizenship Status option list.

Reset Citizenship Status before leaving.

---

## Portal 3 — Wits

**Research doc:** `uniflo-api/docs/phase-3/portal-research/wits.md`
**Screenshots:** `uniflo-api/docs/phase-3/portal-research/screenshots/wits/branch-*/`
**Account:** Temporary ID `T1872394` / `JaneDoe@Wits27`

Read `wits.md` before starting. It documents the 17-step PeopleSoft Fluid wizard — login, then use the left-nav to jump to the step you need.

### Branching fields to target

#### Step 3 — Main Activity

This is a native `<select>` dropdown. Navigate to Step 3 using the left-nav.

The five options are: Currently upgrading matric / Employment Or Occupation / Gap Year / School / University. "School" is done. For each of the remaining four:

1. Select the option.
2. Screenshot the full Step 3 page.
3. Click Save, then navigate to Step 4 and screenshot Step 4 in full — the Main Activity value may affect which fields appear on the secondary education step.
4. Note any sub-fields that appear on Step 3 itself (e.g. employer name, gap-year dates).
5. For "University" (transfer branch): screenshot Step 3 and Step 4, note which fields appear, then stop. Do not fill in or navigate further down that path.
6. Navigate back to Step 3 and reset Main Activity to "School" before the next track.

#### Step 4 — Current School Status radio

Navigate to Step 4. Find the "Current School Status" radio (two options: "Current Grd 12" / "Completed Grd 12 OR Upgrading").

Switch to "Completed Grd 12 OR Upgrading". Screenshot the full Step 4. Note:
- Does an Examination Number field appear or become required?
- Does the "Copy Grade 11 Subjects" button disappear?
- Do the Grade 12 subject rows change in any way?

Reset back to "Current Grd 12" before leaving Step 4.

#### Step 4 — Secondary education type radio (International branch)

On the same Step 4, find the "Secondary education type" radio (South African / International).

Switch to International. Screenshot the full Step 4. Capture:
- Country of Origin field (free-text or dropdown — if dropdown, record all options)
- International Exam Authority dropdown — open it and record all options (8 were noted in the original walkthrough; confirm and add any new ones)
- Qualification type dropdown — all options (9 noted previously; confirm)
- Any extra-sittings or additional fields that appear

Reset back to South African before leaving Step 4.

---

## Portal 4 — UCT

**Research doc:** `uniflo-api/docs/phase-3/portal-research/uct.md`
**Screenshots:** `uniflo-api/docs/phase-3/portal-research/screenshots/uct/branch-*/`
**Account:** `jane.doe.2027` / `JaneDoe@UCT_2027`, instance `UCT_ONLAPP1428528`

Read `uct.md` before starting. The original walkthrough was done as completed-matric (2024) / gap-year, so that track is already covered. This session maps the remaining branches.

Login — no OTP is needed at subsequent logins. The instance is parked at Step 15; navigate backwards to whichever step has the target field.

### Branching fields to target

#### Step 7 — Post School Activity

Navigate back to Step 7 using the left-nav. This step has a dropdown with 10 activity options. Gap year is already done. Open the dropdown and record all 10 options with exact strings.

For each of the remaining 9 options:

1. Select the option.
2. Screenshot the full Step 7 page.
3. Note which sub-fields appear (From date, To date, institution name, employer, activity description, etc.) and which are marked required.
4. If a "studying at another institution" or similar transfer option appears — screenshot the revealed fields, note their labels, then stop for that option.
5. Reset to gap year before selecting the next option.

#### Step 6 — "Applied to UCT before" toggle

Navigate to Step 6. Switch the "Applied to UCT before" toggle to Yes.

Screenshot. Note which sub-fields appear (previous application year, previous student number, reason for reapplication, etc.). Record all field labels and whether they are required.

Toggle back to No before leaving Step 6.

#### Step 2 — Citizenship (non-SA branch)

Navigate to Step 2. Change Citizenship to a non-SA option.

Screenshot. Note:
- Does a Passport Number field appear?
- Does a Country of Origin field appear?
- Are there any downstream changes (e.g. Step 14 document requirements change)?

Capture the full Citizenship option list. Reset to South African before leaving Step 2.

#### Step 5 — School leaving year variants

Navigate to Step 5. Change the school-leaving year to a prior year (e.g. 2023 instead of 2025/2026).

Screenshot. Note whether any field labels, validation rules, or subject slot configurations change. Reset to the original year before leaving.

---

## Portal 5 — Stellenbosch University (Stellies)

**Research doc:** to be created at `uniflo-api/docs/phase-3/portal-research/stellies.md`
**Screenshots:** `uniflo-api/docs/phase-3/portal-research/screenshots/stellies/`
**Account:** to be created during the walkthrough

This is a net-new portal with no prior research. The session has two parts — do them in order in a single session.

### Part 1 — Initial walkthrough (do this first)

Walk the full portal end-to-end as a "Still in Grade 12" student and document everything in a new file `uniflo-api/docs/phase-3/portal-research/stellies.md`. Mirror the format of `uj.md`, `up.md`, `wits.md`, and `uct.md` — those files are the template.

Work through these in order:

1. **Find the portal URL.** Check `sun.ac.za` for an "Apply" or "Online Application" link. Document the exact URL.
2. **Document the engine.** What platform is it built on (PeopleSoft, ITS Integrator, bespoke)? What does the page flow look like (wizard steps, page-by-page, single form)?
3. **Record anti-automation measures.** Is there a captcha? If so, what type — image (can it be DOM-decoded like UP/Wits?), reCAPTCHA, or other? Is there an email OTP? Document the exact mechanism.
4. **Create an account.** Use the synthetic Jane Doe identity from `portal-walkthroughs-plan.md`. Screenshot every step of account creation. Write the credentials into `stellies.md` immediately under a "Test account credentials" section — do not wait.
5. **Walk every form section.** For each section: record the section name, every field label, the control type (dropdown / text / radio / toggle / modal picker), whether it is required, and every selectable option in full (do not abbreviate — capture the complete list). Screenshot each section.
6. **Capture the programme picker.** Document the faculty → programme hierarchy with codes. If there is a search modal, search with `%` or blank to get the full list.
7. **Document eligibility gates.** Does the portal reject ineligible programme choices in real time? What message does it show?
8. **Stop before Submit / Pay.** Document the final step layout but do not click it.

### Part 2 — Branch mapping (do this immediately after Part 1)

In the same session, navigate back to the applicant-type branching field(s) and cover all tracks using the same methodology as the other portals:

- Completed Grade 12, prior year
- Repeating matric / upgrading marks
- Gap year
- Employed / working
- International applicant
- University transfer — note fields only, do not map sub-fields

Append findings under a "Branch mapping (date)" section in `stellies.md` using the output format above.

---

## Completion checklist

**Agents: mark each cell `[x]` as soon as you complete that item, then commit this file. Do not wait until the end of the session.**

| Portal | Initial walkthrough | Completed matric | Repeating / upgrading | Gap year | Employed | International |
|---|---|---|---|---|---|---|
| UJ | done | [ ] | [ ] | [ ] | [ ] | [ ] |
| UP | done | [ ] | [ ] | [ ] | [ ] | [ ] |
| Wits | done | [ ] | [ ] | [ ] | [ ] | [ ] |
| UCT | done (gap year path) | n/a | n/a | done | [x] | [x] |
| Stellies | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
