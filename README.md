# AI-PDF-Renamer

Rename PDFs based on extracted text, heuristic scoring, and an optional local LLM. The tool inspects PDF content, proposes a category/keywords/summary, and builds a deterministic filename such as:

```
YYYYMMDD-category-keywords-summary.pdf
```

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Requirements](#requirements)
4. [Quickstart](#quickstart)
5. [Configuration](#configuration)
6. [Usage](#usage)
7. [How It Works](#how-it-works)
8. [Development](#development)
9. [Testing](#testing)
10. [Validation (build / run / test)](#validation-build--run--test)
11. [Security](#security)
12. [Troubleshooting](#troubleshooting)
13. [Known issues and fixes](#known-issues-and-fixes)
14. [Potential Improvements](#potential-improvements)

## Overview

Many PDF documents are poorly named (e.g., `Scan0001.pdf`). This tool:

1. Extracts text from PDFs using PyMuPDF.
2. Scores regex-based heuristic categories from `heuristic_scores.json`.
3. Optionally queries a local LLM for summary, keywords, and a suggested category.
4. Combines heuristic + LLM categories (heuristics win when present).
5. Filters prompt artifacts via `meta_stopwords.json`.
6. Renames PDFs to include date, category, keywords, and short summary tokens.

If a document is large (e.g., >15k characters), the text is chunked and summarized in parts before a final summary is produced.

## Features

- Heuristic scoring with weighted regex rules.
- Local LLM support via HTTP POST for summaries, keywords, and categories.
- Chunking for large PDFs.
- Flexible naming (kebab/camel/snake case).
- Meta stopword filtering.
- Collision-safe renaming (suffixes `_1`, `_2`, ...).

## Requirements

- Python 3.10+
- `requests`
- `pymupdf` (for PDF extraction)
- Optional: `tiktoken` (better token counting)
- Optional local LLM endpoint listening on `http://127.0.0.1:11434/v1/completions`

## Quickstart

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

## Configuration

### Data files
The renamer expects these JSON files:

- `heuristic_scores.json` (regex rules + scores)
- `meta_stopwords.json` (tokens to remove from filenames)
- `heuristic_patterns.json` (legacy; currently unused by code)

By default, the package ships with these files. You can override the location via:

- `AI_PDF_RENAMER_DATA_DIR` (directory containing the JSON files)
- `AI_PDF_RENAMER_STRUCTURED_LOGS=1` (or `true`/`yes`) to log one JSON object per line for CI/monitoring

### Local LLM endpoint
By default the client uses:

- `http://127.0.0.1:11434/v1/completions`

If your endpoint differs, update `LocalLLMClient` in `src/ai_pdf_renamer/llm.py`.

## Usage

Run interactively:

```bash
python ren.py
```

Or via installed CLI:

```bash
ai-pdf-renamer --dir ./input_files
```

**Parameters**

| Parameter   | Required | Default (non-interactive) | Description                    |
| ----------- | -------- | ------------------------- | ------------------------------ |
| `--dir`     | Recommended | `./input_files`        | Directory containing PDFs. Must be non-empty. |
| `--language` | No     | `de`                     | Prompt language: `de` or `en`. |
| `--case`    | No       | `kebabCase`              | Filename case: `camelCase`, `kebabCase`, `snakeCase`. |
| `--project` | No       | (empty)                  | Optional project name.         |
| `--version` | No       | (empty)                  | Optional version.             |
| `--prefer-llm` | No    | off                      | When category conflicts, use LLM category instead of heuristic. |
| `--date-format` | No   | `dmy`                    | Short date interpretation: `dmy` (day-month-year) or `mdy` (month-day-year). |

Interactive inputs (when running with a TTY): directory path, language, case, project, version. If a value is not provided, the CLI prompts for it.

**Non-interactive / CI**

When stdin is not a TTY (e.g. in CI, cron, or scripts), the CLI does not prompt. All optional parameters use the defaults above. Always pass `--dir` with an explicit path to avoid accidentally using the current directory.

Example:

```bash
ai-pdf-renamer --dir /path/to/pdfs --language de --case kebabCase
```

If the target directory does not exist or `--dir` is empty, the CLI exits with a clear error.

## How It Works

1. **Extract PDF text**
   - Uses PyMuPDF to collect text from multiple extraction modes.
2. **Optional chunking**
   - Large text is split into overlapping chunks; partial summaries are merged.
3. **Heuristic category**
   - Regex patterns are scored; the highest score wins.
4. **LLM summaries & keywords**
   - Prompts request JSON-only responses; retries increase temperature.
5. **Filename generation**
   - Final filename includes: date, optional project/version, category, keywords, summary tokens.

**Date detection:** The tool looks for dates in the document (e.g. `YYYY-MM-DD` or `DD.MM.YYYY`). It assumes **DMY (day-month-year)** for short numeric formats like `31.12.2024`; ISO `YYYY-MM-DD` is preferred and unambiguous. Invalid calendar dates (e.g. `2024-02-30`) fall back to today's date.

## Development

```bash
ruff format .
ruff check .
pytest -q
```

## Testing

```bash
pytest -q
```

## Validation (build / run / test)

From the project root:

```bash
# Install with dev and PDF extras
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e '.[dev,pdf]'

# Lint and test (same as CI)
ruff format --check .
ruff check .
pytest -q

# Optional: build wheel/sdist
python -m pip install -U build
python -m build

# Run the tool (interactive or with args)
python ren.py
# or: ai-pdf-renamer --dir ./input_files --language en --case kebabCase
```

## Security

- This tool can send document text to an LLM endpoint. Use a local endpoint if you need data to stay on-device.
- CI includes security checks:
  - CodeQL (SAST)
  - Dependency Review (PR-only)
  - `pip-audit` (SCA)
  - TruffleHog (secret scanning)

See `docs/RUNBOOK.md` for runbook commands and `SECURITY.md` for reporting guidance.

## Troubleshooting

- **`RuntimeError: PyMuPDF is required for PDF extraction`**
  - Install PDF dependencies: `python -m pip install -e '.[pdf]'`
- **Empty or low-quality LLM output**
  - Verify your local LLM endpoint is running and returns JSON with the expected key.
- **Data files not found**
  - Ensure the JSON files exist in the package or set `AI_PDF_RENAMER_DATA_DIR`.

## Known issues and fixes

For a detailed list of known bugs, required fixes, and improvements, see **[BUGS_AND_FIXES.md](BUGS_AND_FIXES.md)**.

Summary:

1. **LLM variability**
   - Some local LLMs return non-JSON or partial answers (e.g. wrapped in code fences or with leading prose). The tool tries to extract the first JSON object from the response and falls back to heuristics if parsing fails.
2. **False positives in regex (heuristic category)**
   - Categories can be assigned by regex heuristics that match text unintentionally; when both heuristic and LLM suggest a category, the heuristic wins. Tune `heuristic_scores.json` (path and format described in [Configuration](#configuration)) to reduce mismatches.
3. **Very large PDFs**
   - Chunking helps, but large scanned PDFs may still yield partial summaries.
4. **Date extraction**
   - Date parsing is heuristic; DMY is assumed for short formats. Invalid dates fall back to today. See [How It Works](#how-it-works) for details.

## Potential Improvements

1. Better chunking/context handling for long documents.
2. Multi-language heuristic rule sets (per-locale JSON files).
3. Parallel processing for large directories.
4. Optional metadata export (CSV/JSON) before renaming.
