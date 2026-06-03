# Portal Research Index

Target portals for Phase 3 automation. All docs must be reviewed and signed off before Task 2 (adapter scaffolding) starts.

| University | File | Engine | Captcha/OTP | Choices | Fee | Status |
|---|---|---|---|---|---|---|
| University of Cape Town (UCT) | [uct.md](uct.md) | PeopleSoft Fluid | Email OTP at signup ⚠️ | 2 (Faculty→Qual→Major) | _none seen_ | ✅ video-verified draft |
| University of the Witwatersrand (Wits) | [wits.md](wits.md) | PeopleSoft Fluid | 6-char image captcha ⚠️ | 3 (by code) | R100 **after** submit | ✅ video-verified draft |
| University of Pretoria (UP) | [up.md](up.md) | PeopleSoft OAP | Case-sensitive captcha ⚠️ | 2 (eligibility-gated) | R300 **in** flow | ✅ video-verified draft |
| University of Johannesburg (UJ) | [uj.md](uj.md) | ITS Integrator | **None** ✅ | 2 (eligibility-tagged) | _later/out-of-band_ | ✅ video-verified draft |

Each doc is **v2 — rebuilt frame-by-frame from the screen-recording walkthroughs** (`uct/wits/up/uj.mp4`), enriched with exact field labels, control types, required flags, dropdown/LOV option lists, and per-step flow. Sample PII from the videos is deliberately omitted. Remaining `_TBD_`/**[VERIFY]** items + an "Open questions" list are at the foot of each file. The original dictation is preserved as an appendix.

## Cross-cutting findings

- **Drive mechanism locked: approach C (accessibility-tree primary)** — target visible labels/roles, not CSS. UJ leans on a generic `select_from_lov(label, target_text)` helper for its ITS "List of Values" popups; the three PeopleSoft portals are mostly native dropdowns + a few modal pickers (postcode lookup, school search, subject/file-attachment modals).
- **Submit screens captured for all four; only the post-submit *success* page remains.** Screenshots gave the final submit step per portal (UCT Step 16 Terms & Conditions + **Submit**; Wits **Submit Application to the University**; UP **Apply** + full Payment methods; UJ agreement + 5-digit PIN + **I Accept** + **Submit Application**). The literal page shown *after* clicking submit (the `verify_submission()` success marker) is still `_TBD_` — but each portal exposes a reliable signal to key off meanwhile: a **status flip** (UP "Must still verify & apply" clears; UCT step status), an **emailed acknowledgement / applicant number** (UCT), or a **person/student number** (Wits).
- **NBT (UCT only):** a **separate portal** (`nbtests.uct.ac.za`) with its own account + test booking produces the NBT reference Step 10 needs — a second automation surface; decide whether the bot attempts it or the student does.
- **UP & UJ pre-compute programme eligibility** from entered marks (UP rejects ineligible choices at selection; UJ tags choices "ELIGIBLE TO APPLY-Y") — a useful confidence signal.
- **Payment never blocks submission the same way:** Wits = R100 after submit; UP = R300 inside the flow (card or EFT+proof); UCT = none seen; UJ = out-of-band. Relay fee details to the student; don't auto-pay.

## Blocker check (per plan)

- **UCT / Wits / UP** all gate account creation behind a captcha or email OTP — flag at the Sunday sync before week 10. The runtime's OCR/inbox-read reliability decides whether they stay in the MVP target list.
- **UJ has no captcha** → strongest candidate for the **first adapter** (Task 4).

## Conventions

- **Credentials are never committed.** Test-account logins live in Bitwarden (Phase 3 plan §3); the docs link the Bitwarden entry, nothing more.
- **Screenshots:** frames were extracted locally from each `*.mp4` to `Videos/Uniflo/<slug>_frames/` (not committed). TODO per file: export the key page shots into `screenshots/<slug>/` and reference them.

## Sign-off

Both partners must review and approve every research doc in the PR before Task 2 starts.

- [ ] UCT — reviewed
- [ ] Wits — reviewed
- [ ] UP — reviewed
- [ ] UJ — reviewed
