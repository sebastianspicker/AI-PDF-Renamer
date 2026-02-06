# CI Audit

## Inventory
- `CI` workflow: push to `main` and `pull_request`. Runs Ruff format check, Ruff lint, pytest across Python 3.10–3.13.
- `Security` workflow: push, `pull_request`, weekly schedule, and manual dispatch. Runs CodeQL, Dependency Review (PR only), pip-audit, and TruffleHog.

## Recent Failures (from GitHub Actions run history)
- 2026-02-05: `Security` workflow failed on job `TruffleHog (Secret Scan)` step `Scan`.
- 2026-02-05: `CI` workflow succeeded.

## Root Cause And Fix Plan
| Workflow | Failure | Root Cause | Fix Plan | Risk | Verify |
| --- | --- | --- | --- | --- | --- |
| Security | TruffleHog job failed on push | The job used a shallow checkout with a diff-based scan. TruffleHog needs access to the base commit range; with `fetch-depth: 1` it can fail. Logs are not accessible via the public API without admin rights, but a filesystem scan shows no verified secrets in the repo. | Fetch full history in the TruffleHog job and use explicit commit SHAs for PR and push events. Provide a fallback filesystem scan for initial commits and scheduled/manual runs. | Low. Full history fetch is small for this repo. | `docker run --rm -v "$PWD:/repo" trufflesecurity/trufflehog:3.92.5 filesystem /repo --only-verified` and re-run the workflow. |
