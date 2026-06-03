# Data-model cross-check — portal fields vs. Uniflo schema

> **Cross-check done 2026-06-03** against the SQLModel models in `app/models/` and the API schemas in `app/api/*/schemas.py`. This is the single source of truth behind the "Uniflo mapping" columns in the four portal docs: where a portal field has a home in our schema it's named here; where it doesn't, it's under **App gaps**. Feeds Task 3 (AI field mapping) and tells us which columns/tables Phase 3 still needs.
>
> ⚠️ **Migration state:** the demographic + address-split columns below exist in the models but migrations `c5d4e3f2a1b0` (address split + demographics) and `d6e5f4a3b2c1` (`academic_records.record_type`) are **not yet applied to production** (per CLAUDE.md). The gap-fill below adds `e7f6a5b4c3d2` on top. Run `alembic upgrade head` in prod before an adapter relies on them.

## Implementation status (2026-06-03)
**Done** — migration `e7f6a5b4c3d2` + the API changes that go with it:
- **student_profiles** gained: `title`, `middle_names`, `maiden_name`, `preferred_name`, `is_sa_citizen`; a full **mailing (postal) address block** (`mailing_same_as_residential` + `mailing_street_address/suburb/city/province/postal_code`); `disability_detail` + `disability_assistance`; `current_activity`, `exam_number`, `sport`; `wants_residence` + `preferred_residence`; `applying_nsfas` + `applying_institutional_funding`; the NBT block (`nbt_reference`/`nbt_year`/`nbt_date`); and `redress_factors` (JSONB, UCT). All nullable; none added to the completeness guard. Exposed on `POST`/`PATCH`/`GET /profile` (with `Title` + `CurrentActivity` enums and postal-code / nbt-year validators).
- **`contacts` table + `/contacts` API** (list / upsert / delete) — one per type: `next_of_kin`, `fee_payer`, `guardian`, `emergency`; each with name / relationship / id / email / phone / address.
- **`application_choices` table** — `POST /applications` now accepts `additional_programmes` (choice 1 = `programme`; up to 3 total); list/get return ordered `choices` with a portal-computed `eligible` flag.
- **academic_records.subjects** now carries an optional **`nsc_level` (1–7)** alongside `mark` (the percentage) — unblocks UP.
- **documents** gained the **`GRADE11_RESULTS`** type (UP accepts Gr11 results in lieu of a Gr12 certificate).

**Deferred (design choice — flagged for the team):**
- **Disability** is captured as free-text `disability_detail` + `disability_assistance`, not a structured per-portal taxonomy (UP's category→type cascade, Wits's fixed toggle list). Modelling it as enums needs the confirmed canonical option lists.
- **`redress_factors`** is a loose JSONB blob; if UCT stays in the MVP, normalise it into typed fields (with its own consent).
- **`ApplicationChoice.eligible`** is stored but not computed — it's filled at automation time in Phase 3 (UP/UJ compute eligibility portal-side).

> The per-field tables below are the original gap analysis (kept as rationale). Their "today / no column" notes describe the **pre-migration** state; the status above is what now exists.

## Current schema (what we store today)

### `users`
`id` · `email` · `role` · `created_at` — the applicant's **email lives here, not on the profile**.

### `student_profiles` (1:1 with user)
`id` · `user_id` · `first_name` · `last_name` · `id_number` (unique) · `date_of_birth` · `phone` · `street_address` · `suburb` · `city` · `province` · `postal_code` (**exactly 4 digits**, validated) · `nationality` · `gender` · `home_language` · `religion` · `disability` · `marital_status` · `ethnicity` · `updated_at`.

Enum-constrained (`app/api/profiles/schemas.py`):
- `gender`: **Male / Female only** (HEMIS reporting; no non-binary) — matches all four portals' restricted sets.
- `home_language`: the 11 official languages.
- `religion`: None / Christianity / Islam / Hinduism / Judaism / African Traditional / Buddhism / Other.
- `disability`: **a single value** — None / Visual / Hearing / Physical-mobility / Intellectual / Learning / Mental-health / Other.
- `marital_status`: Single / Married / Divorced / Widowed / Other.
- `ethnicity`: African / Coloured / Indian / Asian / White / Other.
- Required-for-complete: every field above **except `suburb`** (see `REQUIRED_PROFILE_FIELDS`).

### `academic_records` (many per student; **unique per (student_id, record_type)**)
`id` · `student_id` · `record_type` · `institution` (= school name) · `year` · `subjects` (JSONB) · `aggregate`.
- `record_type`: **`grade_11_final` or `grade_12_april` only**.
- `subjects`: list of `{ name, mark (int), custom_name? }` — **one integer mark per subject**, plus optional free-text name for "Other" rows.

### `documents`
`id` · `student_id` · `type` · `storage_path` · `uploaded_at`. `type`: **ID_COPY / MATRIC_RESULTS / TRANSCRIPT / GRADE12_APRIL**.

### `applications`
`id` · `student_id` · `university_id` · **`programme` (single string)** · `application_year` · `status` · `submitted_at` · `updated_at` · `created_at`.

## What maps cleanly (no work needed)
Biographical core — names, `id_number`, `date_of_birth`, `phone`, the street-address block, `postal_code`, `nationality`, `gender`, `home_language`, `religion`, `marital_status`, `ethnicity` — covers the bulk of every portal's personal/contact/demographic pages. School name → `academic_records.institution`; matric year → `.year`; per-subject mark → `subjects[].mark`. ID upload → `documents` ID_COPY (UCT/UP/Wits). Email → `users.email`.

## App gaps — portal fields with no home in the schema

### Identity / names
| Portal field | Needed by | Today | Recommendation |
|---|---|---|---|
| **Title** (Mr/Mrs/Ms/Dr…) | UJ, UCT, Wits, UP | — | add `title` to student_profiles |
| **Middle name(s)** | UCT, Wits, UP | only first/last | add `middle_names` (or accept packing into first_name) |
| **Maiden name** | UJ, UCT | — | low priority (optional everywhere) |
| **Preferred name** | UCT, UP | — | add `preferred_name` (prints on UCT student card — ask the student) |
| **Initials** | UJ | derivable | derive from names |
| **Citizenship status** (SA-citizen Y/N + citizenship code) | UJ, UCT, UP | `nationality` (free string) | semantics differ; consider `is_sa_citizen` and keep `nationality` |

### People — the biggest gap (no table exists for any of these)
| Portal field | Needed by | Notes |
|---|---|---|
| **Next of kin** (name, mobile, relationship, email, address) | UJ, Wits, (UCT guardian) | Wits enforces NOK email **and** mobile ≠ applicant |
| **Account / fee payer** (name, address, email) | UJ, UCT | UJ requires the payer's **full address re-entered** — no "same as student" |
| **Parent/Guardian** (title, name, ID, relationship, email, phone, address) | UCT | under-18 ⇒ P/G + fee payer; 18+ ⇒ fee payer only |
| **Emergency contact** (distinct from NOK) | Wits | "same as NOK" toggle, but may differ |
→ Recommend a small **`contacts`** table (type = nok / fee_payer / guardian / emergency) rather than columns.

### Addresses
| Portal field | Needed by | Today | Recommendation |
|---|---|---|---|
| **Postal address** (when ≠ street) | UJ, UCT, Wits | single address only | most offer "same as"; add a postal block only if we support a differing one |
| **Domicilium (legal-notices) address** | Wits | — | usually = residential; Wits-specific |

### Schooling / marks
| Portal field | Needed by | Today | Recommendation |
|---|---|---|---|
| **NSC level (1–7) _and_ percentage** per subject | UP | `mark` is one int | **JSONB can't hold both** — add `nsc_level` alongside `mark` (= percentage) |
| **Subject order** (school-report order) | UP ("same order as report") | JSONB list order | preserve write order; treat as significant |
| **Subject qualifier** (NSC/NCV/ISC/DR) | UJ | — | UJ LOV-tags subjects; map our name → UJ's qualified entry at fill time |
| **Examination number** | Wits, UP | — | add optional `exam_number` |
| **Examining authority / province of schooling** | Wits, UP | — | derivable from school; low priority |
| **Grade 11 results as a _document_** | UP, Wits | doc types lack a "Grade 11 results" type | UP accepts Gr11 results **or** Gr12 cert — add a `GRADE11_RESULTS` doc type |

### Application-level
| Portal field | Needed by | Today | Recommendation |
|---|---|---|---|
| **Multiple programme choices** (ordered) | UJ 2, UCT 2, Wits 3, UP 2 | `programme` = **one string** | model choices (array or `application_choices` rows); **the AI must pick portal-eligible choices** (UP rejects ineligible at selection; UJ tags ELIGIBLE-Y) |
| **Residence interest** (+ preferred residence) | UJ, UP, Wits | — | add `wants_residence` (+ optional preference) |
| **NSFAS / funding intent** | UCT, UP, Wits | — | add funding-intent flag(s) |
| **Current activity** ("in Grade 12 / School / still in high school") | UJ, Wits, UP, UCT | — | derive from the latest academic_record, or add `current_activity` |
| **Disability detail** (category + type + needs-assistance) | UP, Wits, UCT | `disability` = one enum | enrich: category + type + assistance (UP modal; Wits long toggle list; UCT support detail) |
| **NBT reference + year + exam date** | UCT | — | **student does NBT themselves** (decision below) — we only **capture & relay**; add `nbt_reference` / `nbt_year` / `nbt_date` (or a small NBT block) |
| **UCT redress factors** (parents' apartheid classification, parents'/grandparents' education, child-support grant, social pension, mother's first language) | UCT | — | UCT-only; bundle into a UCT extras block if UCT stays in scope |
| **Sport** | Wits (optional) | — | low priority |
| **UJ 5-digit PIN** | UJ | — | **portal secret, not profile** — store with the account secret in Bitwarden / a secrets store, never in the profile DB |

## Cross-cutting decisions (2026-06-03)
- **Consent screens are shown to the student, never auto-accepted.** Covers UJ's POPI Act (entry gate) + Application Agreement (submit), Wits's Indemnity & Undertaking, UCT's Terms & Conditions, and UP's Declaration. The runtime pauses, surfaces each consent doc (link + short summary), records the student's explicit acceptance, then lets the bot tick the box and continue.
- **UCT NBT is out of automation scope.** The student registers for and writes the NBT on the separate `nbtests.uct.ac.za` portal themselves; Uniflo only **captures the NBT reference (+ year/date)** and feeds it into Step 10 — no bot account on the NBT portal.

## Highest-impact follow-ups for Task 3
1. **`contacts` table** (NOK / fee-payer / guardian / emergency) — unblocks UJ, Wits, UCT.
2. **Multi-choice applications** — every portal takes 2–3 ordered programme choices; we store one string.
3. **Richer subject shape** — add `nsc_level` alongside the percentage in each subject — unblocks UP marks (UCT's Gr11 final + Gr12-April map to the existing record types).
4. **`title`, `preferred_name`, `middle_names`, disability detail, residence + funding intent** on the profile.
