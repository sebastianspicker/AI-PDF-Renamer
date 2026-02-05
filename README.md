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
10. [Security](#security)
11. [Troubleshooting](#troubleshooting)
12. [Known Issues](#known-issues)
13. [Potential Improvements](#potential-improvements)

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

Interactive inputs:
- Directory path (default: `./input_files`)
- Language (`de` or `en`)
- Desired case (`kebabCase`, `camelCase`, `snakeCase`)
- Project (optional)
- Version (optional)

If the target directory does not exist, the CLI exits with a clear error.

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

## Security

- This tool can send document text to an LLM endpoint. Use a local endpoint if you need data to stay on-device.
- CI includes security checks:
  - CodeQL (SAST)
  - Dependency Review (PR-only)
  - `pip-audit` (SCA)
  - TruffleHog (secret scanning)

See `docs/RUNBOOK.md` for commands and details, and `SECURITY.md` for reporting guidance.

## Troubleshooting

- **`RuntimeError: PyMuPDF is required for PDF extraction`**
  - Install PDF dependencies: `python -m pip install -e '.[pdf]'`
- **Empty or low-quality LLM output**
  - Verify your local LLM endpoint is running and returns JSON with the expected key.
- **Data files not found**
  - Ensure the JSON files exist in the package or set `AI_PDF_RENAMER_DATA_DIR`.

## Known Issues

1. **LLM variability**
   - Some local LLMs return non-JSON or partial answers. The code retries with fallback prompts but may still return `na`.
2. **False positives in regex**
   - PDFs might match category patterns unintentionally; tune `heuristic_scores.json` as needed.
3. **Very large PDFs**
   - Chunking helps, but large scanned PDFs may still yield partial summaries.
4. **Date extraction**
   - Date parsing is heuristic and can pick misleading date strings.

## Potential Improvements

1. Better chunking/context handling for long documents.
2. Multi-language heuristic rule sets (per-locale JSON files).
3. Parallel processing for large directories.
4. Optional metadata export (CSV/JSON) before renaming.
