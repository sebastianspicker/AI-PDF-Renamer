# CI

## Workflows
- `CI` runs on push to `main` and on all `pull_request` events. It lints with Ruff and runs pytest across Python 3.10–3.13.
- `Security` runs on push, `pull_request`, weekly schedule, and manual dispatch. It runs CodeQL, pip-audit, and TruffleHog. Dependency Review runs only on PRs.

## Local Run
Prerequisites: Python 3.10+, pip, and a virtual environment.

Commands:
- `make install-dev`
- `make ci`
- `make lint`
- `make test`

Security checks locally:
- `pip-audit -r requirements.txt`
- `docker run --rm -v "$PWD:/repo" trufflesecurity/trufflehog:3.92.5 filesystem /repo --only-verified`
- CodeQL requires the CodeQL CLI and GitHub setup; run it only if needed.

## Secrets And Permissions
- No secrets are required for CI or Security workflows on PRs.
- If future jobs need secrets, guard them with `if: secrets.NAME != ''` and restrict them to `push` on the default branch or `workflow_dispatch`.

## Extending CI
- Keep Actions pinned to a stable major version (commit SHA).
- Add `timeout-minutes` and use the existing `concurrency` groups.
- Prefer `actions/setup-python` with pip caching and use lock files if added later.
