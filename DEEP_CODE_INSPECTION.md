# Deep Code Inspection – Findings & Priorities

## P0 – Critical (crash, data loss, security)
*None identified.*

---

## P1 – Breaking / High likelihood

### 1. RenamerConfig: `desired_case` and `date_locale` unvalidated
- **Where:** `renamer.py` – `RenamerConfig`
- **Why:** CLI restricts values via argparse choices, but programmatic callers can pass e.g. `desired_case="Title Case"` or `date_locale="xyz"`. `convert_case()` then raises `ValueError` deep inside `generate_filename()`; date logic may behave unexpectedly.
- **Fix:** Validate in `RenamerConfig` (e.g. `__post_init__`): `desired_case` in `{"camelCase","kebabCase","snakeCase"}`, `date_locale` in `{"dmy","mdy"}`; raise `ValueError` with a clear message.

### 2. LLM `complete()`: HTTP/response failures only logged generically
- **Where:** `llm.py` – `LocalLLMClient.complete()`
- **Why:** On `resp.raise_for_status()` or `resp.json()` failure we catch `RequestException`/`JSONDecodeError` and return `""`. Callers cannot distinguish “LLM unreachable” from “empty answer”; debugging is harder without status code or body.
- **Fix:** Before returning, log at WARNING with status code and (truncated) response body when status is not 2xx or JSON decode fails.

---

## P2 – Nice-to-have / Robustness

### 3. Renamer: retries incremented twice on `FileExistsError`
- **Where:** `renamer.py` – rename loop
- **Why:** In the `except FileExistsError` block we do `retries += 1`, and the loop end also does `retries += 1`. Each `FileExistsError` consumes two retry slots, so the effective limit is ~50 real conflicts before hitting 100.
- **Fix:** Remove the inner `retries += 1` from the `except FileExistsError` block; keep a single increment at the end of the loop.

### 4. pdf_extract: per-page INFO log volume
- **Where:** `pdf_extract.py` – `_extract_pages()`
- **Why:** For every page we log “Combined extracted N characters from page X of Y” at INFO. Large PDFs produce many lines and can clutter logs.
- **Fix:** Use `logger.debug()` for this message.

### 5. complete_json_with_retry: silent fallback
- **Where:** `llm.py` – `complete_json_with_retry()`
- **Why:** When all retries are exhausted we return `last` (possibly invalid or empty) with no log. Operators have no signal that the result may be poor.
- **Fix:** When leaving the loop without having returned valid JSON, log at WARNING (e.g. “All retries exhausted; using last response as fallback”).

### 6. StructuredLogFormatter: getMessage() can raise
- **Where:** `logging_utils.py` – `StructuredLogFormatter.format()`
- **Why:** If `record.getMessage()` raises (e.g. broken %-formatting or custom message type), the formatter raises and can break logging. We already catch `TypeError`, `ValueError` for the payload build.
- **Fix:** Catch a broader `Exception` around the whole format path and return a safe JSON line with level/message and the exception text.

---

---

## Second pass (defensive / edge cases)

### P2 (continued)

### 7. parse_json_field: None or empty response
- **Where:** `llm.py` – `parse_json_field()`
- **Why:** If a caller passes `None` (e.g. from a future code path), `response.strip()` raises `AttributeError`. Empty string is already handled by later logic but can be short-circuited for clarity.
- **Fix:** At function start: if `response is None` return `None`; if `response.strip()` is empty return `None`.

### 8. chunk_text: empty or whitespace-only text
- **Where:** `text_utils.py` – `chunk_text()`
- **Why:** For empty or whitespace-only `text`, the loop yields one empty chunk `[""]`, which can be sent to the LLM and is useless.
- **Fix:** If `not (text and text.strip())`, return `[]`.

### 9. normalize_keywords: None input
- **Where:** `text_utils.py` – `normalize_keywords()`
- **Why:** If `raw` is `None` (e.g. from a different caller or API evolution), `str(None).split(",")` yields `["None"]`, so `"none"` could appear as a keyword.
- **Fix:** If `raw is None`, return `[]`; extend type hint to `str | list[str] | None`.

---

## Third pass (defensive None / type guards)

### P2 (continued)

### 10. generate_filename: None or non-str pdf_content
- **Where:** `renamer.py` – `generate_filename()`
- **Why:** If a caller passes `None` or a non-string, `extract_date_from_content()` or LLM helpers raise or behave unpredictably.
- **Fix:** At start: if `pdf_content is None or not isinstance(pdf_content, str)`, raise `ValueError("pdf_content must be a non-None string")`.

### 11. pdf_to_text: None filepath
- **Where:** `pdf_extract.py` – `pdf_to_text()`
- **Why:** `Path(None)` becomes a path to a literal file named `"None"`; clearer to short-circuit and return `""`.
- **Fix:** If `filepath is None`, return `""`; extend type hint to `str | Path | None`.

### 12. HeuristicScorer.best_category: None or non-str text
- **Where:** `heuristics.py` – `best_category()`
- **Why:** `rule.pattern.search(None)` raises `TypeError`.
- **Fix:** If `text is None or not isinstance(text, str)`, return `"unknown"`.

### 13. extract_date_from_content: None or non-str content
- **Where:** `text_utils.py` – `extract_date_from_content()`
- **Why:** `_DATE_RE_YMD.search(None)` or attribute access on `None` raises.
- **Fix:** If `content is None or not isinstance(content, str)`, set `content = ""` so the rest returns today.

### 14. split_to_tokens: None or non-str text
- **Where:** `text_utils.py` – `split_to_tokens()`
- **Why:** `re.split(..., None)` raises.
- **Fix:** If `text is None or not isinstance(text, str)`, return `[]`; extend type hint to `str | None`.

### 15. get_document_summary: None or non-str pdf_content
- **Where:** `llm.py` – `get_document_summary()`
- **Why:** `pdf_content.strip()` raises if `pdf_content` is `None`.
- **Fix:** If `pdf_content is None or not isinstance(pdf_content, str)`, return `"na"`.

### 16. parse_json_field: non-str response
- **Where:** `llm.py` – `parse_json_field()`
- **Why:** If a caller passes e.g. `bytes` or `int`, `response.strip()` may raise or behave oddly.
- **Fix:** After the `None` check, if `not isinstance(response, str)`, return `None`.

---

## Fourth pass (performance, python-performance-optimization)

### P2 Performance

### 17. pdf_extract: repeated tiktoken.get_encoding()
- **Where:** `pdf_extract.py` – `_token_count()`
- **Why:** `_shrink_to_token_limit()` calls `_token_count()` in a loop. Each call does `tiktoken.get_encoding("cl100k_base")`, which is expensive. The encoding is immutable and can be reused.
- **Fix:** Cache the encoding in a module-level variable; set it on first successful use so subsequent calls reuse it.

### 18. llm: no connection reuse for HTTP
- **Where:** `llm.py` – `LocalLLMClient.complete()`
- **Why:** Each `requests.post()` opens a new TCP connection. One PDF triggers many LLM calls (summary, keywords, category, final_summary); reusing a session reduces latency and load.
- **Fix:** Use a `requests.Session()` per `base_url` (module-level cache), and call `session.post(..., trust_env=False)` so connections are pooled.

---

## Fifth pass (Python-pro: type-safe, tooling)

### P2 Typing & tooling

### 19. No static type checking
- **Where:** `pyproject.toml`
- **Why:** Without mypy, type hints are not validated; regressions and API misuse can go unnoticed.
- **Fix:** Add `mypy>=1.11.0` to dev deps and `[tool.mypy]` with `python_version = "3.13"`, `strict = true`; override `ignore_missing_imports = true` for optional modules `fitz`, `tiktoken`.

### 20. pdf_extract: untyped doc and _tiktoken_encoding
- **Where:** `pdf_extract.py` – `_extract_pages(doc, ...)`, `_tiktoken_encoding`
- **Why:** `doc` is the fitz document (optional dep); module-level mutable is untyped. Strict mypy will flag or infer Any.
- **Fix:** Add `from typing import Any`; type `doc: Any`, `_tiktoken_encoding: Any = None`.

### 21. extract_date_from_content: signature accepts None at runtime but type says str
- **Where:** `text_utils.py` – `extract_date_from_content(content: str, ...)`
- **Why:** We guard `if content is None or not isinstance(content, str)`; the signature should reflect that `content` may be None for defensive callers.
- **Fix:** Use `content: str | None` in the signature.

### 22. data_path: filename not constrained at type level
- **Where:** `data_paths.py` – `data_path(filename: str)`
- **Why:** Only certain filenames are valid; we raise at runtime. A Literal type documents and enforces valid names at type-check time.
- **Fix:** Define `DataFileName = Literal["heuristic_patterns.json", "heuristic_scores.json", "meta_stopwords.json"]`, type `DATA_FILES` as `frozenset[str]`, and use `data_path(filename: DataFileName)`.

---

## Summary
- **P0:** 0
- **P1:** 2 (fixed)
- **P2:** 18 (previous passes) + 4 (Python-pro) = 22  

**Status:** All listed fixes have been implemented.

---

## Final verification (latest pass)

A full re-read of `renamer.py`, `llm.py`, `pdf_extract.py`, `text_utils.py`, `cli.py`, `heuristics.py`, `data_paths.py`, and `logging_utils.py` was performed. No additional P0/P1/P2 issues were found; all 22 items above are present in the codebase. Tests and lint pass.
