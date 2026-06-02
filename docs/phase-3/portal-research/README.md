# Portal Research Index

Target portals for Phase 3 automation. All docs must be reviewed and signed off before Task 2 (adapter scaffolding) starts.

| University | File | Engine | Captcha/OTP | Status |
|---|---|---|---|---|
| University of Cape Town (UCT) | [uct.md](uct.md) | PeopleSoft/Oracle | Email OTP at signup ⚠️ | 📝 draft — needs review |
| University of the Witwatersrand (Wits) | [wits.md](wits.md) | PeopleSoft/Oracle | 6-char security code ⚠️ | 📝 draft — needs review |
| University of Pretoria (UP) | [up.md](up.md) | PeopleSoft/Oracle | Security code ⚠️ | 📝 draft — needs review |
| University of Johannesburg (UJ) | [uj.md](uj.md) | ITS Integrator | **None** ✅ | 📝 draft — needs review |

Each draft was reformatted from dictated walkthroughs + Notion screenshots. They carry `_TBD_` / **[VERIFY]** placeholders and an "Open questions" list for the gaps still to confirm against the live portals. The original dictation is preserved as an appendix in each file.

## Blocker check (per plan)

- **UCT / Wits / UP** all gate account creation behind a captcha or email OTP — flag at the Sunday sync before week 10. The runtime's OCR/inbox-read reliability decides whether they stay in the MVP target list.
- **UJ has no captcha** → strongest candidate for the **first adapter** (Task 4).

## Conventions

- **Credentials are never committed.** Test-account logins live in Bitwarden (Phase 3 plan §3); the docs link the Bitwarden entry, nothing more.
- **Screenshots** live in Notion (presigned links expire). TODO per file: export PNGs into `screenshots/<slug>/` and reference them.

## Sign-off

Both partners must review and approve every research doc in the PR before Task 2 starts.

- [ ] UCT — reviewed
- [ ] Wits — reviewed
- [ ] UP — reviewed
- [ ] UJ — reviewed
