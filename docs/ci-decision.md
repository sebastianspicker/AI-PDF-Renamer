# CI Decision

## Decision
FULL CI.

## Rationale
- The repo contains executable Python code plus unit tests and lint rules that can run fully offline.
- The workflows do not require production secrets or access to live infrastructure.
- Security checks add value for a public repo and are inexpensive for this code size.

## What Runs Where
- `CI` runs on push to `main` and on all `pull_request` events: lint and pytest across Python 3.10–3.13.
- `Security` runs on push, `pull_request`, weekly `schedule`, and `workflow_dispatch`: CodeQL, pip-audit, TruffleHog.
- Dependency Review runs on `pull_request` only.

## CI Threat Model
- Fork PRs are untrusted. We only use `pull_request` (never `pull_request_target`).
- No secrets are required for PR checks; jobs run with read-only repo access.
- `GITHUB_TOKEN` permissions are least-privilege by default, with `security-events: write` scoped to CodeQL only.
- Secret scanning runs in diff mode for PR/push events and in filesystem mode for scheduled/manual runs to avoid flaky history scanning.

## If We Later Want More
- Add dependency lock files (pip-tools or uv) for fully deterministic resolution.
- Add optional integration tests that require `pymupdf` or a local LLM endpoint behind `workflow_dispatch` or a self-hosted runner.
- Add a scheduled full git-history TruffleHog scan (git mode) once per week if history coverage is required.
