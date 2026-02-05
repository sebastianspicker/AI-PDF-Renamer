# FINDINGS

## P0 (Critical)
- None identified.

## P1 (High)
- **Empty PDFs are still renamed** (`src/ai_pdf_renamer/pdf_extract.py`, `src/ai_pdf_renamer/renamer.py`).
  - Expected: PDFs with no extractable text should be skipped (or explicitly flagged), not renamed.
  - Actual: `pdf_to_text()` returns the sentinel string `"Content is empty or contains only whitespace."`, which is non-empty; `rename_pdfs_in_directory()` treats it as content and renames the file.
  - Repro: Run against a scanned PDF with no extractable text.
  - Fix strategy: Return empty string for no content or have `rename_pdfs_in_directory()` detect the sentinel and skip; add unit test.
  - Verification: `pytest -q` with a test asserting empty content skips renaming.
  - Status: Addressed in Phase 3 (return empty content; added skip test).

- **Packaged installs can fail to find JSON data files** (`src/ai_pdf_renamer/data_paths.py`, `src/ai_pdf_renamer/renamer.py`).
  - Expected: Installed CLI should locate `heuristic_scores.json` and `meta_stopwords.json` without requiring repo root.
  - Actual: `data_path()` searches for `pyproject.toml`; in site-packages it falls back to CWD, so files are missing unless user runs inside repo or sets `AI_PDF_RENAMER_DATA_DIR`.
  - Impact: `FileNotFoundError` on first run in typical installed usage.
  - Fix strategy: Bundle JSON as package data and load via `importlib.resources` (or document required env var with a hard fail and guidance).
  - Verification: `pytest -q` plus a packaging smoke test or unit test using package data.
  - Status: Addressed in Phase 3 (package data + fallback logic + test).

## P2 (Medium)
- **No handling for non-existent input directory** (`src/ai_pdf_renamer/renamer.py`, `src/ai_pdf_renamer/cli.py`).
  - Expected: Friendly error if the provided directory does not exist or is not a directory.
  - Actual: `Path.iterdir()` raises `FileNotFoundError` and terminates without guidance.
  - Fix strategy: Validate path upfront and raise a clear error; add CLI test.
  - Verification: `pytest -q` with CLI or unit test.
  - Status: Addressed in Phase 3 (validation + CLI exit + tests).

- **Security baseline missing (secret scan / SAST / SCA)** (`.github/workflows/ci.yml`, `docs/RUNBOOK.md`).
  - Expected: Minimal security checks or at least documented runbooks for them.
  - Actual: None configured.
  - Fix strategy: Add minimal GitHub Actions checks (CodeQL or Semgrep, dependency scan, secret scan) or explicitly document a baseline alternative.
  - Verification: CI green with security jobs.
  - Status: Addressed in Phase 2 via `security.yml` + RUNBOOK update (pending CI verification).

- **Test coverage gaps in critical paths** (`src/ai_pdf_renamer/pdf_extract.py`, `src/ai_pdf_renamer/cli.py`, `src/ai_pdf_renamer/renamer.py`).
  - Expected: Tests for PDF extraction edge cases, CLI argument handling, rename collision behavior.
  - Actual: Only heuristics/text/LLM parsing/filename generation are covered.
  - Fix strategy: Add unit tests with monkeypatching for I/O and PDF extraction.
  - Verification: `pytest -q`.
  - Status: Addressed in Phase 3 (rename collision test + CLI missing-dir test + pdf_extract edge cases).

## P3 (Low)
- **Unused `heuristic_patterns.json` alongside `heuristic_scores.json`** (repo root, `src/ai_pdf_renamer/data_paths.py`).
  - Expected: Single source of truth for heuristic rules.
  - Actual: Two files exist; only `heuristic_scores.json` is used by default.
  - Fix strategy: Remove or document the unused file, or add a loader for it.
  - Verification: README/docs updated or tests ensuring correct file is used.
  - Status: Addressed in Phase 3 by documenting legacy status in RUNBOOK.

- **CamelCase conversion can preserve underscores in tokens** (`src/ai_pdf_renamer/text_utils.py`).
  - Expected: CamelCase output should not contain underscores.
  - Actual: `clean_token()` converts whitespace to underscores; `convert_case()` capitalizes tokens but does not split on underscores.
  - Fix strategy: Split tokens on underscores before camelCase conversion or adjust cleaning behavior.
  - Verification: `pytest -q` with a dedicated test.
  - Status: Addressed in Phase 3 (underscore split + test).

- **Interactive input accepts invalid values without validation** (`src/ai_pdf_renamer/cli.py`).
  - Expected: Prompt should re-ask until valid `language`/`desired_case`.
  - Actual: Arbitrary strings are accepted, leading to fallback behavior without user feedback.
  - Fix strategy: Validate in a loop or reuse argparse choices for interactive mode.
  - Verification: `pytest -q` with CLI tests or manual validation.
  - Status: Addressed in Phase 3 (reprompt loop + test).
