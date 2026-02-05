# DECISIONS

## 2026-02-03: Pin GitHub Actions by SHA
- Context: Reduce supply-chain risk in CI workflows.
- Decision: Pin all GitHub Actions used in CI/security workflows to immutable commit SHAs.
- Consequences: Requires periodic maintenance to update SHAs when bumping action versions.
