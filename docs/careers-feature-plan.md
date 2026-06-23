# Careers Feature — Plan ("Andzi phase after 5")

> **STATUS: FINALIZED 2026-06-23 — ready to build.** Research, design, the 11-industry
> taxonomy, the card template, and the full careers catalogue are locked. Every planning
> open question is resolved (see "Resolved decisions"). This is the cross-repo master plan
> (frontend `uniflo-web`, backend `uniflo-api`); the identical doc is committed to both
> repos. No code is written yet — build is **backend-first**, sequenced after Phase 5.

## Context

UniFlo currently helps a student go from **marks → qualifying degrees → application**
(the `/courses` page driven by `GET /recommendations`). The missing first step is
**aspiration**: a Grade 10–12 student often doesn't yet know *what they want to be*,
only *what subjects they take*. This feature adds a **Careers** tab that turns a
student's subject choices into concrete career opportunities, then hands them straight
into the existing degree → apply pipeline.

The tab shows career cards gated on **subjects taken (not marks)** — a student doing
Maths + Physical Sciences sees engineering/science careers; one doing Accounting +
Maths sees finance careers. Each card carries Title, Description, expected
**compensation in ZAR**, and **employability** (market demand + degree pathways).
Because subject-based careers are effectively unbounded, the tab is narrowed by an
**industry filter**. A "Programmes" button on each card (mirroring the Apply button on
degree cards) opens the degrees that lead to that career, grouped by university, each
showing its qualify/borderline status and an Apply handoff.

### Resolved decisions (planning Q&A — all locked)
1. **Curated researched catalogue** — career content (ZAR bands, demand, pathways) is
   researched once and seeded as static data, same pattern as `programmes`. No runtime AI.
2. **Programmes view shows match status** — the per-career degrees view reuses the
   marks engine (`/recommendations` scoring) to badge each degree Qualifies / Borderline
   / Not-yet, plus the existing Apply handoff.
3. **Industry taxonomy LOCKED** — the 11 industries below (user-approved; "ICT" expanded
   to "Information & Communication Technology").
4. **Card template LOCKED** — Software Developer sample approved (see Appendix shape).
5. **Subject gate is `all_of` / `any_of`** (not a flat "all required" list) — see the
   model below. Engineering needs Maths **AND** Physical Sciences; commerce/trades accept
   Maths **OR** Maths Literacy. Resolves the pure-Maths vs Maths-Lit split.
6. **TVET / college-pathway coverage** — RESOLVED (was the last open item). Career →
   programme resolution spans only the 4 seeded research universities (UP/UJ/Wits/UCT).
   Careers whose real path is TVET / nursing-college / apprenticeship (skilled trades,
   registered nurse, some teaching) point their `programme_keywords` at the closest
   university diploma where one exists; when the match set comes back empty, the per-career
   programmes view renders an honest "this path is mainly through a college or
   apprenticeship" note instead of looking broken. Seeding TVET/college institutions is a
   later expansion, explicitly out of scope here.

---

## Architecture

**Data model.** New `careers` catalogue table (curated static data), seeded from JSON
via a script — mirrors `faculties`/`programmes` + `scripts/seed_programmes.py`. A career
is gated to a student by its `subject_rule` (see below) and linked to real degrees by
`programme_keywords` resolved against the active `programmes` catalogue.

**Two endpoints** (both auth'd — they read the signed-in student's record, like
`/recommendations`; nothing to add to the public-route bypass):
- `GET /careers` — returns careers whose `subject_rule` the student's subjects satisfy,
  with all card content. 409 `{code: no_academic_record}` when the student has no record
  (mirrors recommendations). The frontend derives industry chips from the result and
  filters client-side (same pattern as `CoursesView` faculty chips).
- `GET /careers/{id}/programmes` — resolves the career's `programme_keywords` to active
  programmes across all universities, computes each one's match status from the student's
  marks (reusing the recommendations scoring engine), and returns them grouped by
  university for the "Programmes" view.

**Frontend.** New `/careers` route modeled directly on `/courses`: a server-fetched
first paint + a `CareersView` client component with industry filter chips and a card
grid. A `/careers/[id]` sub-route renders the per-university matching degrees with
status badges and Apply. A new sidebar nav item under "Applying".

### Industry taxonomy (LOCKED — 11)
Engineering & Built Environment · Information & Communication Technology · Health &
Medicine · Finance, Accounting & Business · Law & Justice · Natural & Physical Sciences ·
Agriculture & Environment · Education & Social Sciences · Creative, Media & Design ·
Commerce, Tourism & Hospitality · Skilled Trades.

---

## Backend (`uniflo-api`) — do first

### 1. Model + migration
- New `app/models/career.py` — `Career(SQLModel, table=True)`, table `careers`:
  `id`, `slug` (unique), `title`, `industry` (str), `description` (text), `compensation`
  (JSONB: `{entry, mid, senior, currency: "ZAR", display}`), `employability` (JSONB:
  `{demand, outlook, pathways, employment_note}`), `subject_rule` (JSONB — the gate, see
  below), `recommended_subjects` (JSONB list of canonical NSC names, optional),
  `programme_keywords` (JSONB list), `is_active` (bool), `created_at`/`updated_at`.
  Follow the JSONB column style already in `app/models/programme.py`.
- **Subject gate model (`subject_rule`)** — a flat "all required" list is too blunt:
  Engineering needs Maths **AND** Physical Sciences (both), while Commerce and trades
  accept Maths **OR** Maths Literacy. So the gate is
  `{all_of: [<subjects, every one required>], any_of: [<subjects, at least one required>]}`.
  A career is shown when `all_of ⊆ student_subjects` **and** (`any_of` empty **or**
  `any_of ∩ student_subjects ≠ ∅`). Both default to `[]`. This is what makes the cards
  genuinely "match the subjects the student already takes" — and correctly separates pure
  **Mathematics** from **Mathematical Literacy** (distinct NSC subjects), gating Maths-Lit
  students out of engineering/medicine/actuarial while still surfacing commerce/trades.
- New Alembic migration `add_careers_table`, revising from head **`c1856b74cc36`**.
  Additive + reversible. Apply to prod via the Python API (`command.upgrade()`), **never
  the `.exe`** — and only on the user's explicit go-ahead (⚠️ `.env` = PROD DB).
- Register `Career` in `app/models/__init__.py` if models are aggregated there.

### 2. API module `app/api/careers/`
- `schemas.py` — `CompensationOut`, `EmployabilityOut`, `CareerRead` (all card fields),
  `CareersListResponse`; `CareerProgrammeMatch` (extends the `ProgrammeMatch` shape with
  `university_id`/`university_name`) and `CareerProgrammesResponse` (grouped by university).
- `service.py`:
  - `list_careers(session, user_id, intake_year?)` — resolve the student's best-available
    record via the existing `recommendations.service._best_available_record`; extract the
    student's subject-name set; return active careers passing the `subject_rule` gate
    (`all_of ⊆ subjects` and `any_of ∩ subjects ≠ ∅` when `any_of` non-empty). 409 when no
    record.
  - `list_career_programmes(session, user_id, career_id, intake_year?)` — load the career;
    for each university, load its active programmes (`_load_active_programmes`), keep those
    matching `programme_keywords` (token/substring matcher — keep deterministic; model on
    `app/automation/adapters/uct.best_option_match`), compute the university's APS from the
    record subjects per its `scoring_method`, and `evaluate()` each match. Reuse
    `app/api/recommendations/scoring.py` (`compute_aps`, `evaluate`, `aps_margin_for`) and
    `service.py` helpers (`_load_faculties`, `_load_active_programmes`, `_APS_MAX`).
- `router.py` — `GET /careers`, `GET /careers/{id}/programmes`, rate-limited like the
  recommendations/universities routers; `user_id = request.state.user["sub"]`.
- Register the router in `app/main.py`.

### 3. Seed data + script
- New `scripts/seed_careers.py` modeled on `scripts/seed_programmes.py` (idempotent
  upsert on `slug`, `--allow-stale` not needed since careers aren't intake-year bound).
- New `data/careers/careers.json` (or one file per industry) — the **curated researched
  catalogue** (Appendix below): for each career, real SA ZAR salary bands
  (entry/mid/senior), current market demand + outlook, degree/internship/postgrad
  pathways, the `subject_rule` (exact canonical NSC names from
  `uniflo-web/lib/constants/nsc-subjects.ts`), and `programme_keywords` chosen to resolve
  against the seeded UP/UJ/Wits/UCT programme names.
- **Subject names are pre-verified.** Every subject token in the Appendix gate resolves to
  a canonical entry in `nsc-subjects.ts` as of finalization (e.g. `Maths` → `Mathematics`,
  `Maths Lit` → `Mathematical Literacy`, `EGD` → `Engineering Graphics and Design`). The
  seed JSON must use the **full canonical names**, not the Appendix shorthand.

### 4. Tests
- `tests/test_careers_endpoints.py` — TestClient + mocked service + patched JWT (the
  `tests/conftest.py` pattern): list gated by subjects, 409 no-record, industry content
  round-trips, programmes-by-career returns per-university matches with status.
- `tests/test_careers_matching.py` — pure unit tests for the keyword→programme matcher and
  the `subject_rule` gate (`all_of`/`any_of`, no DB), using synthetic subject sets.
- Update `CLAUDE.md` migration head + chain.

---

## Frontend (`uniflo-web`) — after backend deploys

1. **Regen types**: `npx openapi-typescript http://localhost:8000/openapi.json -o
   lib/api/schema.d.ts` once the backend is deployed (never hand-write API types).
2. `lib/api/careers.ts` — thin typed wrappers (re-export generated shapes + `getCareers`,
   `careerProgrammesPath`/`getCareerProgrammes`), mirroring `lib/api/recommendations.ts`.
   Reuse `MATCH_STATUS_BADGE` for the status badges.
3. `app/(app)/careers/page.tsx` — server-fetch first paint exactly like
   `app/(app)/courses/page.tsx` (`serverApiGet` + Supabase session token; surface 409 as
   `initialNoRecord`), then render `CareersView`.
4. `components/careers/careers-view.tsx` — client component: industry filter **chips**
   (lift the scrollable-chips pattern from `components/courses/courses-view.tsx`), derive
   industries from the result, card grid, the "add your subjects" empty state reused from
   `CoursesView`'s `noRecord` card.
5. `components/careers/career-card.tsx` — Title, Description, Compensation (ZAR),
   Employability (demand + pathways), and a bottom-right **"Programmes"** button placed/
   styled exactly like `CourseCard`'s Apply CTA (`mt-auto self-end`, `ArrowRight`) → routes
   to `/careers/[id]`.
6. `app/(app)/careers/[id]/page.tsx` + `components/careers/career-programmes-view.tsx` —
   per-university matching degrees with Qualifies/Borderline/Not-yet badges (reuse
   `CourseCard` or its badge), each wired to the existing Apply handoff: `useSelection`
   (`add`/`update`) → `router.push("/applications/new")`, copied from `CoursesView.handleApply`.
   When the match set is empty (TVET/college-only career), render the college/apprenticeship
   pathway note instead of an empty grid (resolved decision #6).
7. `components/layout/sidebar.tsx` — add `{ href: "/careers", label: "Careers", icon: … }`
   to the **"Applying"** `NAV_GROUPS` entry (e.g. a `Briefcase`/`Compass` lucide icon).
8. A Vitest for `CareersView` industry filtering + `CareerCard` rendering (mirrors existing
   component tests). Run `lint && format:check && tsc --noEmit && test && build` before PR.

---

## Cross-repo sequencing
**Backend first** (model → migration → endpoints → seed → tests → PR → deploy →
`command.upgrade()` on the user's go-ahead), **then** regen types and build the frontend.
One feature branch per repo with the same name (`feature/careers`); reference the sibling
PR in each description. Per-task write-ups under `uniflo-api/docs/` and `uniflo-web/docs/`
following the phase pattern. This planning doc is on `feature/careers-plan` in both repos;
the build branches come later.

---

## Verification (end-to-end, no live portals)
- Migration applied; `careers` table present; existing tables untouched.
- `GET /careers` for a student with Maths + Physical Sciences returns engineering/science
  careers and **omits** finance-only careers; a student with no record gets 409.
- Industry chips filter the grid client-side; each card shows ZAR compensation +
  employability content verbatim from the seed.
- "Programmes" on a career opens per-university degrees with correct match badges; Apply
  pushes into `/applications/new` with the programme + year prefilled. A TVET/college-only
  career shows the college/apprenticeship note rather than an empty grid.
- Backend `pytest` + `ruff` green; frontend `lint`/`format:check`/`tsc`/`test`/`build` green.
- Exercised on desktop **and** mobile viewport (sidebar drawer + chips).

---

## Research findings (validated June 2026 — sources below)
- **Demand (Xpatweb Critical Skills Survey 2025 / SA Critical Skills List):** Engineering
  hardest to hire (38% of firms struggle, up from 23%); ICT shortage 22% (data scientists,
  software engineers, data analysts); healthcare (nurses + specialists) acute; artisans
  rising sharply (22%, esp. electricians, millwrights, instrumentation).
- **Subject prerequisites (validated against UCT/UP/Wits/SU admission docs):** Engineering
  requires **Mathematics + Physical Sciences** (60–70%, pure Maths not Maths-Lit); MBChB
  requires **Mathematics + Physical Sciences + Life Sciences + English** (Level 5–6, Life
  Sciences legally required at ~half the schools); BCom/Commerce accepts **Mathematics OR
  Mathematical Literacy** (but the CA(SA)/actuarial streams effectively need pure Maths).
  → confirms the `all_of`/`any_of` gate and the pure-Maths vs Maths-Lit split.
- **Indicative ZAR pay anchors (2025/26):** software dev R20k→R100k/mo; CA(SA) ~R765k/yr
  (top ~R1.28m); actuary ~R1.41m/yr (top ~R2.7m); GP R44k–R135k/mo (public→private);
  registered nurse ~R24.5k/mo; civil engineer ~R305k–R720k+/yr; attorney R250k→R1.5m/yr;
  electrician R17k–R38k/mo; teacher ~R12k–R23k/mo; graphic designer R12k–R42k/mo; ag
  scientist ~R46k/mo. Figures vary by source/sector → cards show **ranges** with a
  "indicative; varies by employer, city, sector" disclaimer; never presented as guarantees.

Sources: OfferZen developer salary reports; Xpatweb 2025 Critical Skills Survey; SA
Critical Skills List 2025/26; PayScale/Glassdoor/ERI (ZA) for CA, actuary, doctor, nurse,
attorney, electrician, teacher, graphic designer, agricultural scientist; UCT/UP/Wits/SU
NSC admission-requirement documents (engineering, MBChB, commerce).

---

## Appendix — careers catalogue blueprint (seed content, FINAL)

Gate shorthand: **ALL[…]** = every subject required (`all_of`); **ANY[…]** = at least one
required (`any_of`); **OPEN** = no subject gate (industry filter narrows). Subjects use
canonical NSC names — the shorthand here (`Maths` = Mathematics, `Maths Lit` =
Mathematical Literacy, `EGD` = Engineering Graphics and Design) **must be expanded to the
full canonical name in the seed JSON**. Pay = indicative ZAR ranges (entry→senior).
`keywords` resolve to seeded UP/UJ/Wits/UCT programmes.

**Engineering & Built Environment**
- Civil Engineer — ALL[Maths, Physical Sciences] — R25k→R65k+/mo — `civil engineering`
- Mechanical Engineer — ALL[Maths, Physical Sciences] — R25k→R70k+/mo — `mechanical engineering`
- Electrical/Electronic Engineer — ALL[Maths, Physical Sciences] — R28k→R75k+/mo — `electrical engineering, electronic`
- Architect — ALL[Maths] +rec Visual Arts/EGD/Design — R18k→R55k/mo — `architecture, architectural`
- Quantity Surveyor — ALL[Maths] +rec Accounting/EGD — R22k→R60k/mo — `quantity surveying`
- Urban & Regional Planner — ANY[Geography, Maths] — R20k→R55k/mo — `urban planning, town planning`

**Information & Communication Technology**
- Software Developer — ALL[Maths] — R20k→R100k/mo — `computer science, information technology, informatics, software, data science`
- Data Scientist / Analyst — ALL[Maths] — R25k→R90k/mo — `data science, statistics, computer science, information systems`
- Cybersecurity Specialist — ALL[Maths] — R25k→R85k/mo — `computer science, information technology`
- Network & Systems Engineer — ANY[Maths, Maths Lit, Information Technology] — R18k→R60k/mo — `information technology, information systems`
- IT Support Technician — ANY[Information Technology, Computer Applications Technology, Maths, Maths Lit] — R12k→R35k/mo — `information technology`

**Health & Medicine**
- Medical Doctor (MBChB) — ALL[Maths, Physical Sciences, Life Sciences] — R44k→R135k/mo — `mbchb, medicine, surgery`
- Pharmacist — ALL[Maths, Physical Sciences] +rec Life Sciences — R30k→R70k/mo — `pharmacy`
- Physiotherapist — ALL[Life Sciences] +rec Physical Sciences — R25k→R55k/mo — `physiotherapy`
- Registered Nurse — ALL[Life Sciences] — R18k→R45k/mo — `nursing` ⚠️ mainly nursing-college path
- Dietitian — ALL[Life Sciences] +rec Physical Sciences — R20k→R45k/mo — `dietetics, nutrition`
- Dentist — ALL[Maths, Physical Sciences, Life Sciences] — R40k→R110k/mo — `dental, dentistry, oral`

**Finance, Accounting & Business**
- Chartered Accountant CA(SA) — ALL[Maths] +rec Accounting — ~R765k→R1.28m/yr — `accounting, chartered accountant`
- Actuary — ALL[Maths] +rec Physical Sciences — ~R1.41m→R2.7m/yr — `actuarial, statistics, mathematical sciences`
- Investment / Financial Analyst — ALL[Maths] +rec Economics/Accounting — R25k→R90k/mo — `finance, investment, economics`
- Economist — ANY[Maths, Maths Lit] +rec Economics — R25k→R80k/mo — `economics, econometrics`
- Accountant / Bookkeeper — ANY[Accounting, Maths, Maths Lit] — R15k→R45k/mo — `accounting, financial`
- Entrepreneur / Business Manager — ANY[Business Studies, Accounting, Economics, Maths, Maths Lit] — R15k→R80k/mo — `business management, entrepreneurship`

**Law & Justice**
- Attorney / Advocate — OPEN +rec History/languages — R20k→R125k/mo — `llb, law`
- Legal Advisor / Corporate Counsel — OPEN — R30k→R90k/mo — `llb, law`
- Paralegal — OPEN — R12k→R30k/mo — `paralegal, legal`
- Forensic Investigator — ANY[Life Sciences, Maths, Maths Lit] — R18k→R50k/mo — `forensic, criminology, law`

**Natural & Physical Sciences**
- Chemist — ALL[Physical Sciences] +rec Maths — R22k→R60k/mo — `chemistry, chemical sciences`
- Biologist / Life Scientist — ALL[Life Sciences] +rec Maths — R20k→R55k/mo — `biological sciences, biology`
- Physicist — ALL[Maths, Physical Sciences] — R25k→R70k/mo — `physics, physical sciences`
- Environmental Scientist — ANY[Life Sciences, Geography] — R20k→R55k/mo — `environmental science`
- Geologist — ANY[Geography, Physical Sciences] +rec Maths — R25k→R80k/mo — `geology, earth science`
- Microbiologist / Biochemist — ALL[Life Sciences, Physical Sciences] — R22k→R60k/mo — `biochemistry, microbiology`

**Agriculture & Environment**
- Agricultural Scientist / Agronomist — ANY[Agricultural Sciences, Life Sciences] +rec Maths — R20k→R55k/mo — `agriculture, agricultural sciences, agronomy`
- Veterinarian — ALL[Maths, Physical Sciences, Life Sciences] — R30k→R80k/mo — `veterinary`
- Animal Scientist — ALL[Life Sciences] +rec Agricultural Sciences — R20k→R50k/mo — `animal science`
- Farm / Agribusiness Manager — ANY[Agricultural Sciences, Agricultural Management Practices, Business Studies, Economics] — R18k→R60k/mo — `agricultural management, agribusiness`
- Conservation Scientist — ANY[Life Sciences, Geography, Agricultural Sciences] — R18k→R50k/mo — `conservation, nature, wildlife, environmental`

**Education & Social Sciences**
- Subject Teacher (Maths/Science) — ANY[Maths, Physical Sciences, Life Sciences] — R18k→R45k/mo — `education, teaching`
- Foundation / General Teacher — OPEN — R15k→R40k/mo — `education, teaching, foundation phase`
- Psychologist — ANY[Life Sciences] — R25k→R70k/mo — `psychology`
- Social Worker — OPEN — R15k→R40k/mo — `social work`
- Sociologist / Political Scientist — OPEN +rec History/Geography — R18k→R55k/mo — `social science, political science, sociology`

**Creative, Media & Design**
- Graphic / UX Designer — ANY[Visual Arts, Design, Information Technology, Computer Applications Technology] — R12k→R45k/mo — `graphic design, visual communication, design, multimedia`
- Journalist / Media Practitioner — OPEN +rec languages — R14k→R45k/mo — `journalism, media studies, communication`
- Filmmaker / Animator — ANY[Visual Arts, Dramatic Arts, Design, Information Technology] — R14k→R55k/mo — `film, motion picture, animation, multimedia`
- Fine / Visual Artist — ANY[Visual Arts, Design] — R10k→R40k/mo — `fine art, visual arts`
- Musician / Sound Engineer — ANY[Music] +rec Physical Sciences — R12k→R45k/mo — `music, sound`

**Commerce, Tourism & Hospitality**
- Marketing / Brand Manager — ANY[Business Studies, Economics, Maths, Maths Lit] — R18k→R70k/mo — `marketing, business`
- Supply Chain / Logistics Manager — ANY[Maths, Maths Lit, Business Studies, Economics] — R20k→R65k/mo — `logistics, supply chain, transport`
- Hospitality / Hotel Manager — ANY[Hospitality Studies, Tourism, Consumer Studies, Business Studies] — R15k→R50k/mo — `hospitality, hotel`
- Tourism / Travel Manager — ANY[Tourism, Geography, Business Studies] — R14k→R45k/mo — `tourism, travel`
- Human Resources Manager — OPEN +rec Business Studies — R20k→R65k/mo — `human resource, industrial psychology`

**Skilled Trades** ⚠️ *primary path is TVET + apprenticeship + trade test; the Programmes
button maps to the closest university engineering diplomas where they exist (e.g. UJ) and
otherwise shows a "college/apprenticeship" pathway note (resolved decision #6).*
- Electrician — ANY[Electrical Technology, Maths, Maths Lit, Technical Mathematics] — R17k→R38k/mo — `electrical engineering`
- Millwright / Fitter & Turner — ANY[Mechanical Technology, Engineering Graphics and Design, Maths, Technical Mathematics] — R18k→R45k/mo — `mechanical engineering`
- Boilermaker / Welder — ANY[Mechanical Technology, Engineering Graphics and Design, Technical Mathematics, Maths Lit] — R15k→R40k/mo — `mechanical engineering, fabrication`
- Plumber — ANY[Civil Technology, Maths, Maths Lit] — R14k→R35k/mo — `civil engineering, building`
- Diesel / Auto Mechanic — ANY[Mechanical Technology, Maths, Maths Lit] — R14k→R38k/mo — `mechanical engineering, automotive`

---

## Status
- **Industry taxonomy: LOCKED** (11 industries; "ICT" = Information & Communication Technology).
- **Card template: LOCKED** (Software Developer sample approved).
- **Careers catalogue: FINAL** — full set in the Appendix (~5 careers × 11 industries ≈ 55).
  Subject tokens verified against `nsc-subjects.ts`; ZAR ranges sourced (see Research).
- **TVET / college-pathway coverage: RESOLVED** (decision #6 — empty-match careers render a
  college/apprenticeship note; seeding TVET institutions is a later, out-of-scope expansion).
- **All planning open questions resolved.** Ready to build, backend-first, after Phase 5.
