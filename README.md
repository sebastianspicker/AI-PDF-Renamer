# AI-PDF-Renamer
A PDF Renamer with Heuristics and Local LLM. This repository contains a Python script that automatically renames PDF files based on their **content**. It leverages both **heuristics** (regex-based scoring) and a **local LLM** (Language Model) to generate summaries, keywords, and categories. For large PDFs, the script can **split** (chunk) the text and summarize each part separately, merging them into a final summary.

## Table of Contents

1. [Overview](#overview)  
2. [Features](#features)  
3. [Requirements](#requirements)  
4. [Installation](#installation)  
5. [Configuration](#configuration)  
6. [Usage](#usage)  
7. [How It Works](#how-it-works)  
8. [Known Issues](#known-issues)  
9. [Potential Improvements](#potential-improvements)  

## Overview

Many PDF documents are poorly named (e.g., `Scan0001.pdf`). This script:

1. **Extracts Text** from PDFs using [PyMuPDF](https://pymupdf.readthedocs.io).  
2. **Heuristically Determines Categories** by matching regular expressions (regex) with assigned scores (in `heuristic_scores.json`).  
3. **Queries a Local LLM** to produce short text summaries, keywords, and an alternative category suggestion.  
4. **Combines** the heuristic-based category with the AI-based category (the heuristic category has higher priority if not `unknown`).  
5. **Filters** out meta-words (like `summary`, `schlüsselwörter`, etc.) via a `meta_stopwords.json`.  
6. **Renames** PDFs to include the inferred date, category, keywords, and final short summary.  

If a file is very large (e.g., >15k characters), the text is chunked, partially summarized, and the partial summaries are merged into one final summary. This ensures the entire PDF is considered rather than truncating the text.

## Features

- **Heuristic Scoring**: Each regex pattern has a numeric weight. If a PDF matches multiple patterns, scores add up. The pattern with the highest total score determines the heuristic category.  
- **Local LLM Support**: Summaries, keywords, and categories are fetched by sending prompts to a local LLM endpoint (HTTP `POST`).  
- **Chunking**: Large PDFs are split into overlapping chunks to avoid losing important text. Each chunk is summarized, and partial summaries merge into a final overview.  
- **Flexible Naming**: The final filename includes:
  - **Date** (extracted from the PDF text or defaults to today’s date).  
  - **Project/Version** parameters (optional).  
  - **Category** (heuristic + AI).  
  - **Keywords** and final short summary tokens.  
- **Meta Word Filtering**: Removes prompt-specific words like `“zusammenfassung”`, `“json”`, `“schlüsselwörter”` from the filename.

## Requirements

- **Python 3.10+**
- **requests** (for calling the local LLM)
- **PyMuPDF (pymupdf / fitz)** (for PDF text extraction)
- Optional: **tiktoken** (better token counting for truncation)
- **A local LLM** endpoint listening on `http://127.0.0.1:11434/v1/completions`

## Quickstart (venv)

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip

# Install dev tooling + PDF extraction
python -m pip install -e '.[dev,pdf]'

# Optional: better token counting
# python -m pip install -e '.[tokens]'
```

You also need a local service providing JSON completions via HTTP POST. If you do not have a local LLM, adapt the code to another endpoint or an online API.

## Installation
1. Clone or download this repository.
2. Place your PDF files into a subfolder, e.g., `./input_files/`.
3. Ensure you have the supporting JSON files in the project root:
   - `heuristic_scores.json` (regex-based rules + scoring)
   - `meta_stopwords.json` (words to remove from final filenames)
4. Install dependencies (editable install recommended):

```bash
python -m pip install -e '.[pdf]'
```

## Configuration
`heuristic_scores.json`
Holds the score-based regex patterns. Each entry has:
```json
{
  "regex": "(?i)\\barbeitsvertrag\\b",
  "category": "arbeitsvertrag",
  "score": 4.5
}
```
Multiple entries let you handle many categories. The script tallies matches and picks the category with the highest total score.

`meta_stopwords.json`
Specifies words or tokens you never want in filenames (e.g., `"zusammenfassung"`, `"json"`, etc.).
```json
{
  "stopwords": [
    "schlüsselwörter",
    "zusammenfassung",
    "json",
    "beispiel"
  ]
}
```
### Local LLM Endpoint
- The script calls `POST http://127.0.0.1:11434/v1/completions` by default.
- Modify `get_field(prompt, temperature=0.0)` if your endpoint differs.

## Usage
1. Run the script (interactive):

```bash
python ren.py
```

or via the installed CLI:

```bash
ai-pdf-renamer --dir ./input_files
```

2. Interactive Inputs:
   - Directory path (default: `./input_files`)
   - Language (`de` or `en`)
   - Desired case (`kebabCase`, `camelCase`, or `snakeCase`)
   - Project (optional)
   - Version (optional)
3. Process:
   - The script reads `.pdf` files from the chosen folder.
   - It extracts text, detects categories (heuristics + AI), obtains summaries and keywords, filters meta-words, then generates a new filename.
   - The new filename has the format:
     ```css
     YYYYMMDD-category-keywords-summary.pdf
     ```
  - If a file with that name already exists, it appends `_1`, `_2`, etc.

## How It Works
1. Extract PDF Text
   Using PyMuPDF:
   ```python
    doc = fitz.open(filepath)
    # combine page text via doc[page].get_text(...)
   ```
2. Optional Chunking
   If the text is large (e.g., > 15,000 characters), it is split into chunks with overlap. Each chunk is summarized; partial summaries are merged into one final summary.
3. Heuristic Category
   Regex patterns from `heuristic_scores.json` are matched. The script sums their scores and picks the top-scoring category, unless none match (→ `unknown`).
4. LLM Summaries & Keywords
   The script sends 1–4 prompts for summary, keywords, category, etc. If JSON parsing fails, it tries fallback prompts with a higher temperature.
5. Filename Generation
   A final function `generate_filename` combines:
   - Extracted date
   - (Optional) project + version
   - Category
   - Up to 3 keywords
   - Up to 5 final summary tokens
  - Meta stopwords get filtered before the final naming.

## Development

Run quality checks:

```bash
ruff check .
ruff format .
pytest -q
```
  
## Known Issues
1. Local LLM Variability
   Depending on how your local LLM is set up, it may return non-JSON or partial answers. The script attempts four fallback prompts, but sometimes it still fails ('na').
2. False Positives in Regex
   Certain PDFs might contain text that coincidentally matches a category pattern. The script could misclassify. Adjust your heuristic_scores.json carefully.
3. Very Large PDFs
   Although chunking is implemented, extremely large PDFs could still take a long time to process. The chunked approach is more robust, but might still produce partial/inconsistent summaries if the text is heavily scanned or OCR-based.
4. Date Extraction
   The date extraction might catch misleading date-like strings (e.g., random references in the text) and rename the PDF incorrectly. You can improve or customize this with more advanced date-detection logic.

## Potential Improvements
1. Better Chunking/Context
   The script currently merges partial summaries with minimal context. More advanced chunking solutions (e.g., providing brief overlap in each chunk’s prompt) or more sophisticated summarization could yield better results.
2. Multi-Language Patterns
   If you support multiple languages, you might create additional or separate `heuristic_scores_XX.json` files with localized patterns. Then choose them based on user input.
3. Parallel Processing
   For large directories, each PDF could be handled in parallel or asynchronously, potentially speeding up the overall process.
4. Storing Metadata
   If you want to store more than a filename (e.g., a CSV of all summarized info, categories, etc.), add a step to output the results before renaming.
5. Advanced Redundancy Checks
   The script tries to remove duplicate tokens in the final name. Additional logic (e.g., fuzzy matching or morphological checks) could refine the final tokens.
