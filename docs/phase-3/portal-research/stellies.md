# Stellenbosch University (Stellies) — Portal Research

> **Status: v1 — LIVE pre-account walkthrough (2026-06-27), BLOCKED at account creation by reCAPTCHA.** Net-new portal, no prior research. Driven live via Playwright with the synthetic Jane Doe identity. The **public/pre-login surface is fully documented** (portal URL, engine, the 4-way profile-type gate, the complete New-Applicant signup form + option lists, and the international branch at signup). **Account creation could not be completed** — the signup form is gated by a **Google reCAPTCHA v2 image challenge** that cannot be DOM-decoded or solved programmatically (unlike UP/Wits' filename-encoded captcha). Because every in-application surface (programme picker, the applicant-type wizard sections, the branch tracks) sits behind a logged-in account, **Part 2 (branch mapping inside the application) is blocked** until the reCAPTCHA is solved by a human or via a CAPTCHA-solving service.
>
> **Never submit / never pay** still applies. Nothing was submitted; no account was created.

## Portal URL & entry points

- **Applicant portal (SPA):** `https://student.sun.ac.za/applicant-portal/` → redirects to `https://student.sun.ac.za/applicant-portal/#/auth/login` (hash-routed single-page app).
- **Signup / create profile:** `https://student.sun.ac.za/signup/` (linked from the login page as "I'm new here. **Create a profile**").
- **Public marketing entry:** `www.maties.com` / `student.sun.ac.za` ("Apply" links). The how-to-apply guidance lives at `mlai.sun.ac.za/apply/` and `sun.ac.za/english/maties/Pages/Apply-HowDoIApply.aspx`.

## Engine

- **Serosoft Academia** — footer reads *"World's Leading Educational Management Software"* (Serosoft's product tagline). Version strings: **`Wolverine-R 1.0.100`** (login page) / **`wolverine 1.0.101`** (signup page). "Wolverine" is the release codename.
- **Front end:** an Angular-style SPA (hash routing `#/auth/login`, `formcontrolname` attributes, `ng-*` classes). This is a different engine family from the other four portals (PeopleSoft Fluid for UCT/UP/Wits, ITS Integrator for UJ).
- **Interaction pattern (provisional):** native `<select>` dropdowns and text inputs with stable `id`/`formcontrolname` (e.g. `#Id_Type`, `#Id_Number`, `#Mobile_Number`, `#Primary_Citizenship`). No LOV popups seen on the signup surface. Some inputs are `readonly` until focused (`onfocus="this.removeAttribute('readonly')"`, e.g. `#Mobile_Number`) — the adapter must focus before filling.

## Anti-automation measures ⚠️ — HARD BLOCKER

- **Google reCAPTCHA v2 ("I'm not a robot")** on **both** the login page **and** the signup form. Site key `6LdfEe0UAAAAADE2Iqf_wK79R5C9`.
- **Confirmed live (2026-06-27):** clicking the "I'm not a robot" checkbox under Playwright immediately triggers an **image challenge** (the `…/recaptcha/api2/bframe` iframe, "expires in two minutes" — a 300×150 grid challenge), i.e. Google's risk analysis flags the automated session and does **not** grant a silent pass.
- This is **not** DOM-decodable (UP/Wits embed the answer in the captcha image filenames; reCAPTCHA does not). It cannot be solved with the techniques used on the other portals. Options to unblock account creation are: (a) a human solves the reCAPTCHA once to create the account; (b) integrate a third-party reCAPTCHA-solving service; (c) run non-headless with a residential/known-good browser profile and hope for a silent pass (unreliable). **None of these were in scope for this research session.**
- **Email OTP:** expected at/after account creation (the Gmail connector was enabled specifically for this), but **unverified** — the flow never reached the post-Create step because reCAPTCHA gates the Create button. The OTP mechanism therefore remains TBD.

## Account model

- **Self-created profile**, then login with **APP/ID + Password** (+ reCAPTCHA). "Forgot Password?" link present. Password policy link present on signup (`Please click here to Password Policy`).
- **Profile-type gate (signup, 4 options — radio):**
  1. **New Applicant** — "For applicants applying to Stellenbosch University for the first time." ← the school-leaver path.
  2. **All Stellenbosch Business School Applicants** — current/returning/new, specifically for the SU Business School.
  3. **Returning SU Student Application** — previously studied at SU, not currently registered.
  4. **Current SU Student | Staff** — currently enrolled students and staff.
- Selecting **New Applicant** reveals the full profile-creation form (below). UI is bilingual (English / Afrikaans toggle).

## Application window

- **2027 intake:** electronic applications open **1 April**, general deadline **31 July** (per `sun.ac.za` how-to-apply guidance + the page's Application Deadlines panel). Early application advised; space is limited.

## Signup form — New Applicant (live-captured 2026-06-27)

All fields are `*` required unless noted. Native `<select>` unless stated.

| Field | Control | Options / notes |
|---|---|---|
| **Title** | dropdown | Adv, Capt, Dr, Lt Col, Miss, Mr, Mrs, Ms, Mx, Past, Prof, Rev, Reverend |
| **Name(s) / Given Name(s)** | text | |
| **Surname / Family Name** | text | |
| **Date of Birth** | 3 dropdowns | Year (1940–2026), Month (Jan…Dec), Day (populates after Year+Month) |
| **Country of Citizenship** | dropdown | ~200-country list, default **South African**. **Branch trigger** — see below. |
| **Gender** | dropdown | Male, Female, Nonbinary |
| **ID Type** | dropdown (`#Id_Type`) | South African ID, Passport, Permanent Residence Permit, Temporary Asylum Seeker, Refugee, Temporary Study Visa. **Disabled & locked to "South African ID" when Country of Citizenship = South African**; **enabled when citizenship ≠ South African.** |
| **ID Type Number** | text (`#Id_Number`) | the ID / passport / permit number |
| **Email Address** + **Confirm Email Address** | text ×2 | must match |
| **Mobile Number** | country-code dropdown + text (`#Mobile_Number`) | code list defaults **South Africa +27**; number field is `readonly` until focused |
| **Correspondence Language** | dropdown | Afrikaans, English |
| **Password** + **Confirm Password** | password ×2 | policy link present |
| **reCAPTCHA** | widget | "I'm not a robot" — **blocks Create** (see anti-automation) |
| Buttons | | **Create** / **Reset** |

## Branch mapping — what was reachable

### Track: International applicant — **CAPTURED at signup** ✅

**Trigger field:** **Country of Citizenship** (signup form, `#Primary_Citizenship`).
**Behaviour (verified live):** with citizenship = **South African**, the **ID Type** dropdown (`#Id_Type`) is **disabled** and locked to "South African ID". Changing citizenship to a non-SA country (tested: **Zimbabwe**) **enables** ID Type and resets it to "Select", exposing the full document-type list: **South African ID, Passport, Permanent Residence Permit, Temporary Asylum Seeker, Refugee, Temporary Study Visa**. Resetting citizenship back to South African re-locks it to "South African ID".
**Adapter implication:** for Stellenbosch the international/non-SA branch is driven at **profile creation**, not inside the application — set Country of Citizenship first, then choose the matching ID Type (passport/permit/asylum/refugee/study-visa) and enter the corresponding document number. The asylum/refugee/study-visa options also cover those residency sub-types.
**Screenshots (local only, not committed):** `stellies-signup-form-newapplicant.png`, `stellies-signup-profile-type-gate.png`.

### Tracks: Completed matric / Repeating / Gap year / Employed — **BLOCKED** ⛔

These are application-form (post-login) branches — the school-activity / matric-status fields, the programme picker, and the per-applicant-type sections live **inside the wizard that opens only after a profile is created and you log in**. Account creation is blocked by reCAPTCHA, so **none of these four tracks could be reached or mapped** this session. They remain TODO, contingent on a human-solved reCAPTCHA (or a solving service) to create the test account.

## Open questions / to verify (all gated on account creation)

- [ ] **reCAPTCHA** — needs a human solve (or solver service) to create the Jane Doe test account. Hard blocker for headless automation; confirmed image-challenge, not DOM-decodable. **Document the decision: is Stellenbosch in scope for the bot at all given reCAPTCHA on both login and signup?**
- [ ] **Email OTP** at/after Create — mechanism unverified (never reached). Gmail connector is ready (`unknown.user.jane.doe@gmail.com`) for when the account can be created.
- [ ] **Application wizard** — page flow, step count, engine-specific interaction pattern (Serosoft Academia), programme/faculty picker, eligibility gating. All TBD.
- [ ] **Branch tracks** Completed matric / Repeating / Gap year / Employed — TBD inside the application.
- [ ] **Document uploads & submit/pay** screens — TBD.

## Session notes (2026-06-27)

- No account created, nothing submitted, no payment.
- Engine confirmed Serosoft Academia "Wolverine"; reCAPTCHA confirmed on login **and** signup with a live image-challenge trigger.
- International-branch-at-signup captured (Country of Citizenship → ID Type unlock).
- Screenshots kept **local only** (not committed) per the project convention: `stellies-signup-form-newapplicant.png`, `stellies-signup-profile-type-gate.png`, `stellies-signup-recaptcha-challenge.png`.
