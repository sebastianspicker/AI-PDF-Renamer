# Public API and library usage

This document describes the parts of the package that are intended for use as a stable library API. Other modules and helpers may change without notice.

## Stable entry points

Import from `ai_pdf_renamer.renamer`:

- **`rename_pdfs_in_directory(directory, config, files_override=None)`** – Process a directory (or a fixed list of PDFs when `files_override` is set). Extracts text, generates filenames, and renames files according to `config`. Use `config.dry_run=True` to avoid applying renames.
- **`generate_filename(pdf_content, config, llm_client, heuristic_scorer, stopwords, override_category=None)`** – Compute the proposed base filename and metadata for a single PDF’s text. Returns `(base_filename, metadata_dict)`. Does not touch the filesystem or call the LLM if `config.use_llm` is `False`. Optional `pdf_metadata` (from `pdf_extract.get_pdf_metadata`) and `today` are supported for date fallback.
- **`RenamerConfig`** – Dataclass of all options (language, case, paths, LLM/heuristic flags, etc.). Pass the same config to both functions for consistent behaviour.

These names and signatures are kept stable; new optional parameters may be added with defaults.

## Using only filename generation (no renaming)

To get proposed filenames without renaming files:

1. Build a `RenamerConfig` with the desired options (e.g. `language`, `desired_case`, `use_llm`).
2. Load or create `HeuristicScorer` (e.g. via `load_heuristic_rules_for_language` and `HeuristicScorer` from `ai_pdf_renamer.heuristics`), and `Stopwords` (e.g. via `load_meta_stopwords` from `ai_pdf_renamer.text_utils`). For `use_llm=True` you need a `LocalLLMClient` from `ai_pdf_renamer.llm`.
3. Extract PDF text (e.g. with `pdf_to_text` from `ai_pdf_renamer.pdf_extract`).
4. Call `generate_filename(pdf_content, config=config, ...)`. Optional: pass `pdf_metadata=get_pdf_metadata(path)` from `ai_pdf_renamer.pdf_extract` for date fallback when content has no date.

Example (heuristic-only, no LLM):

```python
from pathlib import Path
from ai_pdf_renamer.renamer import RenamerConfig, generate_filename
from ai_pdf_renamer.heuristics import load_heuristic_rules_for_language, HeuristicScorer
from ai_pdf_renamer.text_utils import load_meta_stopwords
from ai_pdf_renamer.pdf_extract import pdf_to_text

config = RenamerConfig(use_llm=False, language="de", desired_case="kebabCase")
# Use paths to your heuristic_scores.json and meta_stopwords.json (or package data)
rules = load_heuristic_rules_for_language(Path("path/to/heuristic_scores.json"), "de")
scorer = HeuristicScorer(rules=rules)
stopwords = load_meta_stopwords("path/to/meta_stopwords.json")
content = pdf_to_text(Path("doc.pdf"))
base_name, meta = generate_filename(content, config, None, scorer, stopwords)
# base_name is the proposed filename without extension; meta has category, summary, keywords.
```

## Versioning

The package follows semantic versioning. The public API described above is stable within a major version; breaking changes will be signalled by a major version bump.
