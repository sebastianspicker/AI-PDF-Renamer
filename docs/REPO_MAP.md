# REPO_MAP

## Overview
Single-package Python CLI that renames PDFs based on text extraction, heuristic scoring, and an optional local LLM.

## Top-Level Structure
- `src/ai_pdf_renamer/`: Library and CLI implementation.
- `ren.py`: Script entry (legacy/standalone runner).
- `tests/`: Pytest unit tests for heuristics, text utils, LLM parsing, and filename generation.
- `*.json`: Heuristic rules and stopwords used by the renamer.
- `.github/workflows/ci.yml`: CI for lint + tests across Python 3.10-3.13.

## Entry Points
- CLI: `ai_pdf_renamer.cli:main` (installed via console script `ai-pdf-renamer`).
- Legacy script: `ren.py` (invokes library functions).

## Key Modules
- `src/ai_pdf_renamer/renamer.py`
  - Core flow: extract date, summarize, keywords, category resolution, token cleanup, filename generation.
  - Directory rename loop with conflict suffixing.
- `src/ai_pdf_renamer/pdf_extract.py`
  - Lazy import of PyMuPDF and text extraction per page.
  - Token-limit shrink for large PDFs.
- `src/ai_pdf_renamer/llm.py`
  - Local LLM client (HTTP POST), JSON parsing/sanitization, prompt retries.
- `src/ai_pdf_renamer/heuristics.py`
  - Load regex rules, compute best category, combine LLM + heuristic categories.
- `src/ai_pdf_renamer/text_utils.py`
  - Date extraction, chunking, token cleanup, case conversion, stopword filtering.
- `src/ai_pdf_renamer/data_paths.py`
  - Resolve data directory and validate expected data files.
- `src/ai_pdf_renamer/logging_utils.py`
  - Console and file logging setup.

## Data Files
- `heuristic_scores.json`: Regex rules with categories and scores.
- `heuristic_patterns.json`: (Present but not currently loaded by default code.)
- `meta_stopwords.json`: Stopword list used for filename token cleanup.

## Tests
- `tests/test_renamer_generate_filename.py`: Filename assembly logic with monkeypatched LLM.
- `tests/test_heuristics.py`: Scoring and category combination.
- `tests/test_text_utils.py`: Date parsing, chunking validation, token utilities.
- `tests/test_llm_parsing.py`: JSON parsing and sanitizer coverage.

## Hotspots / Risk Areas
- LLM JSON parsing and retry logic in `llm.py`.
- PDF extraction and token truncation in `pdf_extract.py`.
- Filename assembly and token normalization in `renamer.py`.

## External Dependencies
- `requests` (LLM HTTP client).
- `pymupdf` (optional, PDF extraction).
- `tiktoken` (optional, token counting).
