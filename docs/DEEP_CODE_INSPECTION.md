# Deep Code Inspection

Systematic review of the AI-PDF-Renamer codebase. Findings are prioritised by severity (P0 critical, P1 breaking, P2 nice-to-have) and by likelihood.

---

## P0 – Critical

| # | Location | Issue | Why it can happen | Status |
|---|----------|--------|-------------------|--------|
| 1 | `renamer.py` | Empty or invalid filename from `generate_filename` could lead to basename `.pdf` or path injection. | All parts (date, category, keywords, summary) could theoretically be empty after cleaning; or control chars in tokens. | **Fixed:** `_sanitize_filename_base()` ensures non-empty name and strips path/control chars. |
| 2 | `renamer.py` | Control characters (e.g. NUL) or path separators in generated filename. | LLM or heuristic output could contain such chars; `clean_token` does not remove all control chars. | **Fixed:** Same sanitizer removes `\x00-\x1f`, `\x7f`, `/`, `\`, etc. |

---

## P1 – Breaking

| # | Location | Issue | Why it can happen | Status |
|---|----------|--------|-------------------|--------|
| 3 | `renamer.py` | `OSError(ENAMETOOLONG)` when generated filename is too long. | Long project/version or many keywords/summary tokens; filesystem path limits. | **Fixed:** Catch `errno.ENAMETOOLONG` and raise with clear message. |
| 4 | `renamer.py`, `heuristics.py` | `read_text()` can raise `OSError` (permission, deleted file). | File removed or permissions changed between `data_path()` and read; NFS/network. | **Fixed:** Catch `OSError` and re-raise as `ValueError` with filename. |
| 5 | `cli.py` | `input()` raises `EOFError` when stdin is closed. | Non-TTY (cron, pipeline, CI) or user Ctrl+D. | **Fixed:** `try/except EOFError` on all interactive `input()` and directory prompt; return defaults. |
| 6 | Filename safety | Control characters in final basename. | See P0#2. | **Fixed:** Central sanitizer. |
| 7 | `llm.py` | `data.get("choices", [{}])[0]` can be non-dict or missing; `.get("text")` then raises `AttributeError`. | LLM API returns `choices: [null]`, `choices: ["x"]`, or non-list. | **Fixed:** Guard with `isinstance(choices, list)`, `isinstance(first_choice, dict)`; use `str(text).strip()`. |

---

## P2 – Nice-to-have

| # | Location | Issue | Why it can happen | Status |
|---|----------|--------|-------------------|--------|
| 8 | `logging_utils.py` | `StructuredLogFormatter.format()` could raise on non-serialisable log content. | Exception objects with cycles or custom attributes in `exc_info`. | **Fixed:** `try/except (TypeError, ValueError)` with fallback JSON message. |
| 9 | `renamer.py` | Imports were placed after a helper (style/maintainability). | Refactor had left package imports in the middle of the file. | **Fixed:** All imports moved to top. |
| 10 | `data_paths.py` | `AI_PDF_RENAMER_DATA_DIR` with only whitespace could yield a odd path. | Env set to `" "` or `"  "`. | **Fixed:** `(os.getenv(...) or "").strip()` so empty/whitespace is ignored. |
| 11 | `llm.py` | Redundant `import re` inside `_sanitize_json_string_value`. | Historical; `re` already imported at module level. | **Fixed:** Removed inner import. |
| 12 | `text_utils.py` | `date_locale.lower()` would fail if `date_locale` is `None`. | Programmatic call with `date_locale=None`; CLI always passes string. | **Fixed:** Use `(date_locale or "dmy").lower()`. |
| 13 | `text_utils.py` | `normalize_keywords(raw)`: if `raw` is list with non-strings (e.g. int from LLM), `token.strip()` raises. | Malformed or non-compliant LLM JSON. | **Fixed:** Use `str(x).strip()` for list elements and `str(raw).split(",")` for string. |

---

## Not changed (by design)

- **KeyboardInterrupt:** Not caught; user abort is intended.
- **path.iterdir() OSError:** Propagates to CLI; message is acceptable.
- **data_path(filename):** Only exact names from `DATA_FILES` allowed; no path traversal.
- **generate_filename empty:** Date part is always present; sanitizer still enforces non-empty base.

---

## Definition of Done

All listed P0, P1, and P2 items have been addressed in code. Tests and lint pass.
