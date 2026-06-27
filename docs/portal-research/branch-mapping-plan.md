# Portal branch-mapping plan

> **Purpose:** The original portal walkthroughs covered one path per portal — a current Grade 12 student (UCT: completed-matric / gap-year). This document tracks what still needs to be walked: every **non-transfer applicant-type branch** across all portals, so the automation knows which fields appear and what they require for each kind of student. Stellenbosch University is a net-new portal being onboarded here for the first time.
>
> University transfer / previously-enrolled paths are **out of scope** for this pass. Note that those branches exist; do not map their sub-fields.
>
> Do not start driving a portal until told. Never submit, never pay.

---

## Test accounts

All existing accounts are parked mid-application. Re-login and navigate to the branching section — do not create fresh accounts unless the portal has expired the session and re-login is impossible.

| Portal | Login | Password | Parked at |
|---|---|---|---|
| UJ | no pre-login — enter via POPI gate | n/a | Page D (no student number — never submitted) |
| UP | Application ID `T4005778` | `JaneDoe@UP2027` | Mid-application, Verify not clicked |
| Wits | Temporary ID `T1872394` | `JaneDoe@Wits27` | Wizard parked (indemnity not accepted, Submit never clicked) |
| UCT | `jane.doe.2027` | `JaneDoe@UCT_2027` | Instance `UCT_ONLAPP1428528` at Step 15 |
| Stellies | TBD — account to be created | TBD | Not started |

Email used across all portals: `unknown.user.jane.doe@gmail.com`
Synthetic applicant details (name, ID, DOB): see `portal-walkthroughs-plan.md` at workspace root.

---

## Tracks to cover

For each portal, walk these applicant types where the portal distinguishes them:

| Track | Notes |
|---|---|
| Completed Grade 12, prior year | Has NSC cert; may require Examination Number |
| Repeating matric / upgrading marks | Registered for NSC supplementary or upgrade exams |
| Gap year | Left school, not studying, not working formally |
| Employed / working | Post-school, in employment |
| International applicant | Non-SA exam authority / non-SA ID |
| ~~University transfer~~ | Out of scope — note fields exist, do not map sub-fields |

"Still in Grade 12" is already done for UJ, UP, Wits. UCT was walked as completed-matric / gap-year.

---

## Output format

For each track walked, append to that portal's research doc (`<slug>.md`) under a heading:

```
## Branch mapping (YYYY-MM-DD)

### Track: <track name>

**Field changed:** <field label> → <option value>
**Fields revealed:** list
**Fields hidden:** list
**Validation changes:** e.g. Examination Number becomes mandatory
**Screenshots:** `screenshots/<slug>/branch-<track>/`
```

Screenshots go in `uniflo-api/docs/phase-3/portal-research/screenshots/<slug>/branch-<trackname>/`.

---

## Portal 1 — UJ

**Research doc:** `uniflo-api/docs/phase-3/portal-research/uj.md`
**Account:** no pre-login; enter via the POPI gate URL

### Branching fields to target

#### Page C — Endorsement LOV (matric status)

Navigate to Page C. Open the Endorsement dropdown and record every option in the list. Then for each option that is NOT "CURRENTLY IN GR.12":

1. Select the option.
2. Screenshot the full Page C form state.
3. Note: does the Examination Number field become mandatory? Do subject rows change? Does any new section appear?
4. Record the exact option string.

Options expected (verify against live LOV — capture the full list):
- `CURRENTLY IN GR.12` — done
- Completed / final matric variant (exact string TBD from live portal)
- Repeating / upgrading variant (exact string TBD)
- Any others in the list

#### Page D — "What are you currently doing?" LOV

Navigate to Page D. Open the LOV and record every option. For each option not yet walked:

1. Select the option.
2. Screenshot the full Page D form state.
3. Note: does a new section appear (e.g. employment details, gap-year dates, institution name)?
4. If "previously enrolled at tertiary" appears — select it, screenshot the fields that appear, then **stop** (transfer branch — do not map sub-fields).

Options expected (verify against live LOV — capture the full list):
- Gap year
- Employed / working
- Any others

#### International branch — Page C secondary education type

1. Find the SA / International radio on Page C.
2. Switch to International.
3. Screenshot: which exam-authority options appear, what qualification-type field shows, what extra-sittings fields appear.
4. Record all option values for each new field.

---

## Portal 2 — UP

**Research doc:** `uniflo-api/docs/phase-3/portal-research/up.md`
**Account:** Application ID `T4005778` / `JaneDoe@UP2027`

### Branching fields to target

#### Demographic Details — "Tell us more" (7 options)

Navigate to Demographic Details. Open the "Tell us more" dropdown. Record every option in full. "I am currently still in high school" is done. For each of the remaining options:

1. Select the option.
2. Screenshot the full Demographic Details section.
3. Note: do any fields appear or disappear elsewhere on the page or in later sections?
4. If a "previously enrolled at tertiary" variant appears — screenshot and stop (transfer branch).

The exact labels for all 7 options must be captured from the live LOV; do not assume wording.

#### Secondary Education — Completed matric path

Navigate to Secondary Education. Change:
- **Highest grade completed** → Grade 12
- **Exemption Type** → the completed-matric option (exact label TBD from live LOV)

Screenshot the full Secondary Education section. Note:
- Does Examination Number become mandatory?
- Does the Documentation section change (Grade 11 Results slot removed? Grade 12 certificate slot added)?
- Does any other section unlock or hide?

Capture the full Exemption Type LOV option list.

#### Personal Information — Non-citizen branch

Navigate to Personal Information. Change Citizenship Status to the non-citizen option.

Screenshot: which Country-of-Citizenship field appears, what happens to the SA National ID field, any other downstream changes.

Capture the full Citizenship Status LOV option list.

---

## Portal 3 — Wits

**Research doc:** `uniflo-api/docs/phase-3/portal-research/wits.md`
**Account:** Temporary ID `T1872394` / `JaneDoe@Wits27`

### Branching fields to target

#### Step 3 — Main Activity (5 options)

Navigate to Step 3. The dropdown has 5 options — "School" is done. For each of the remaining four:

1. **Currently upgrading matric** — select, screenshot Step 3 full state, then navigate to Step 4 and screenshot any changes there.
2. **Gap Year** — same.
3. **Employment Or Occupation** — same. Note if employer fields appear.
4. **University** — select, screenshot. This is the transfer branch: note what appears, then stop. Do not map sub-fields.

For each: record exactly which fields appear/disappear on Steps 3 and 4 when the option is active.

#### Step 4 — Current School Status radio

Navigate to Step 4. Change the radio from "Current Grd 12" to "Completed Grd 12 OR Upgrading".

Screenshot the full Step 4 form. Note:
- Does Examination Number become mandatory?
- Does "Copy Grade 11 Subjects" button disappear?
- Do the Grade 12 subject rows change?

#### Step 4 — Secondary education type radio (International branch)

Navigate to Step 4. Switch the radio from "South African" to "International".

Screenshot the full Step 4 form. Capture:
- Country of Origin options (or confirm it is a free-text field)
- International Exam Authority dropdown — all options (8 noted previously; confirm and record full list)
- Qualification type dropdown — all options (9 noted previously; confirm)
- Extra Sittings / additional fields — all options

---

## Portal 4 — UCT

**Research doc:** `uniflo-api/docs/phase-3/portal-research/uct.md`
**Account:** `jane.doe.2027` / `JaneDoe@UCT_2027`, instance `UCT_ONLAPP1428528`

The previous walkthrough was done as completed-matric (2024) / gap-year, so that track is covered. This session maps the remaining branches.

### Branching fields to target

#### Step 7 — Post School Activity (10 options; gap year done)

Navigate back to Step 7. Open the Activity dropdown and record all 10 options. Gap year is done. For each of the remaining 9 options:

1. Select the option.
2. Screenshot the full Step 7 form.
3. Note which sub-fields appear (From date, To date, institution name, employer, description, etc.) and which are required.
4. If a "studying at another institution" variant appears — screenshot the fields, then stop (transfer branch).

Capture the full option list with exact strings.

#### Step 6 — "Applied to UCT before" toggle

Navigate to Step 6. Switch the toggle to Yes.

Screenshot: what sub-fields appear (previous application year? previous student number? reason for reapplication?). Record all field labels and whether they are required.

#### Step 2 — Citizenship (non-SA branch)

Navigate to Step 2. Change Citizenship to a non-SA option.

Screenshot: does a Passport Number field appear? Country of origin? Any changes to the document requirements downstream (Step 14)?

Capture the full Citizenship LOV option list.

#### Step 5 — Leaving year variants

Navigate to Step 5. Check whether changing the school-leaving year to a prior year (e.g. 2023) changes any field labels, validation, or which subject slots are shown. Screenshot before and after.

---

## Portal 5 — Stellenbosch University (Stellies)

**Research doc:** to be created at `uniflo-api/docs/phase-3/portal-research/stellies.md`
**Account:** to be created during the walkthrough

This is a net-new portal. The session has two parts: initial research walkthrough followed immediately by branch mapping.

### Part 1 — Initial walkthrough

Before doing any branch mapping, walk the full portal end-to-end as a "Still in Grade 12" student. Document everything in `stellies.md` following the same format as `uj.md`, `up.md`, `wits.md`, and `uct.md`:

1. Find the application portal URL (check `sun.ac.za` or a dedicated apply subdomain).
2. Document the engine type and page flow.
3. Record all anti-automation measures: captcha type, OTP, session tokens.
4. Walk account creation — screenshot every step, write credentials into `stellies.md` immediately.
5. Walk every form section: field labels, control types, required/optional, every dropdown option list in full.
6. Capture the faculty → programme picker with codes.
7. Document any eligibility gates or validation behaviour.
8. Stop before any final Submit or payment step.

### Part 2 — Branch mapping

Immediately after Part 1 (same session, same account), navigate back to the applicant-type branching field(s) and cover all tracks:

- Completed Grade 12, prior year
- Repeating matric / upgrading marks
- Gap year
- Employed / working
- International applicant
- University transfer — note fields only, do not map sub-fields

Use the same output format as the other portals (append a "Branch mapping (date)" section to `stellies.md`).

Screenshots to `uniflo-api/docs/phase-3/portal-research/screenshots/stellies/`.

---

## Completion checklist

Mark each cell when the branch mapping section is written into the research doc and screenshots saved. Stellies also needs the initial walkthrough column.

| Portal | Initial walkthrough | Completed matric | Repeating / upgrading | Gap year | Employed | International |
|---|---|---|---|---|---|---|
| UJ | done | [ ] | [ ] | [ ] | [ ] | [ ] |
| UP | done | [ ] | [ ] | [ ] | [ ] | [ ] |
| Wits | done | [ ] | [ ] | [ ] | [ ] | [ ] |
| UCT | done (gap year path) | n/a | n/a | done | [ ] | [ ] |
| Stellies | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
