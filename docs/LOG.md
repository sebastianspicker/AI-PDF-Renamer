# LOG

## 2026-02-03
- Phase 0: Created initial `RUNBOOK.md` and `REPO_MAP.md` for onboarding.
- Phase 1: Read-only analysis completed; findings documented in `docs/FINDINGS.md`.
- Phase 2: Added security baseline workflow and updated RUNBOOK security section.
- Phase 2: Expanded `.gitignore` for caches and editor/OS artifacts.
- Phase 3: Fixed empty-PDF rename behavior and added unit test; pytest green.
- Phase 3: Bundled JSON data files with package and added fallback + test.
- Phase 3: Added directory validation with CLI-friendly error and tests.
- Phase 3: Added rename-collision suffix test; coverage improved.
- Phase 3: Added pdf_extract edge-case tests; coverage improved.
- Phase 3: Fixed camelCase conversion to drop underscores; added test.
- Phase 3: Added interactive prompt validation loop with test coverage.
- Phase 3: Documented `heuristic_patterns.json` as legacy/unused in RUNBOOK.
- Phase 4: Rewrote README in English with required sections and security notes.
- Phase 4: Added SECURITY.md and linked from README.
- Phase 4: Updated CONTRIBUTING to link security/runbook guidance.
- Phase 5: Final verification run (ruff format --check, ruff check, pytest).
- Phase 5: Ran local `pip-audit` (PASS) and TruffleHog v2 CLI (no findings reported).
- Phase 5: Cleaned repo caches and expanded `.gitignore` (env/version managers/logs).
