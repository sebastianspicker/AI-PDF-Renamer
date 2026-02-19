# Design overview – AI-PDF-Renamer

Short design summary. For structure see [ARCHITECTURE.md](ARCHITECTURE.md).

## Design goals

1. **Content-based naming:** Filenames reflect date, category, keywords, and summary derived from PDF text.
2. **Local-first:** Optional local LLM; no cloud dependency; proxy disabled for LLM client so data stays on-device.
3. **Deterministic and safe:** Same inputs → same filename shape; sanitized basenames; collision suffixes; no path injection.
4. **Scriptable and clear:** CLI flags for non-interactive use; clear errors for config and data; EOF-safe prompts.

## Key decisions

- **Heuristics + LLM:** Heuristic category from regex (heuristic_scores.json) is combined with LLM category; heuristic wins unless `--prefer-llm`. This keeps predictable categories for known document types while allowing LLM to suggest for ambiguous content.
- **Chunking:** Large documents are chunked before summarization so the LLM sees bounded context; partial summaries are merged.
- **Data files in repo:** heuristic_scores.json and meta_stopwords.json are versioned; path override via `AI_PDF_RENAMER_DATA_DIR`. Only allowed filenames are resolved (no path traversal).
- **Single-directory batch:** One process, one directory per run; concurrency and TOCTOU are documented limitations.

## Out of scope

- Cloud LLM; GUI; PDF content editing; automatic backup of original names; multi-process safety guarantees.

## References

- [ARCHITECTURE.md](ARCHITECTURE.md) – Components and data flow.
- [BUGS_AND_FIXES.md](../BUGS_AND_FIXES.md) – Known issues and required fixes.
