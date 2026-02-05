# RUNBOOK

This runbook documents reproducible commands for setup, checks, and tests.

## Prerequisites
- Python 3.10+ (CI runs 3.10, 3.11, 3.12, 3.13).
- A local LLM endpoint that accepts JSON completions at `http://127.0.0.1:11434/v1/completions` (optional but required for real renaming).

## Environment
- Optional: `AI_PDF_RENAMER_DATA_DIR` to point to a directory containing:
  - `heuristic_scores.json`
  - `heuristic_patterns.json` (legacy; currently unused by code)
  - `meta_stopwords.json`

## Setup (venv)
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev,pdf]'
```

Optional token counting support:
```bash
python -m pip install -e '.[tokens]'
```

## Fast Loop (recommended)
```bash
ruff check .
pytest -q
```

## Format
```bash
ruff format .
```

## Lint
```bash
ruff check .
```

## Tests
```bash
pytest -q
```

## Typecheck / Static checks
- Not configured.

## Build (optional)
If you want a wheel/sdist, install build tooling and run:
```bash
python -m pip install -U build
python -m build
```

## Security Checks
- Secret scanning (CI): TruffleHog in `.github/workflows/security.yml`.
  - Optional local (pip `trufflehog` v2 CLI): `trufflehog --regex --entropy 1 --repo_path . .`
  - Note: The CI workflow uses the TruffleHog v3 action, which has a different CLI.
- SAST (CI): CodeQL in `.github/workflows/security.yml`.
- SCA/Dependency scanning (CI): `pip-audit -r requirements.txt`.
  - Optional local: `python -m pip install -U pip-audit` then `pip-audit -r requirements.txt`.
- Dependency Review (CI, PR-only): GitHub Dependency Review action.

## Troubleshooting
- `RuntimeError: PyMuPDF is required for PDF extraction`:
  - Ensure `python -m pip install -e '.[pdf]'` was run.
- Empty or low-quality LLM output:
  - Verify the local LLM endpoint is running and returns JSON with the expected key.
- Data files not found:
  - Ensure the JSON files exist at repo root or set `AI_PDF_RENAMER_DATA_DIR`.
