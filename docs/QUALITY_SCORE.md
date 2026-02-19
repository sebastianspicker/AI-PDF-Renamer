# Quality score – AI-PDF-Renamer

Grading of product domains and technical areas. Used to track gaps and prioritize improvements. Update when significant work is done in an area.

## Scale

- **A** – Meets product and Harness expectations; minimal known gaps.
- **B** – Solid with documented limitations or small tech debt.
- **C** – Known gaps or debt; improvements planned.
- **D** – Significant gaps or risk; should be addressed soon.

## Domain scores

| Domain | Grade | Notes |
|--------|-------|--------|
| **CLI / config** | B | Interactive and non-interactive; empty --dir and EOF handled. Help text vs default behavior can be aligned (BUGS §11). |
| **PDF extraction** | C | Works; exceptions swallowed in _extract_pages (BUGS §9, §22). Empty vs failed extraction not always distinguishable. |
| **Heuristics** | B | Regex scoring and combine with LLM documented; false positives possible, tuning is operator responsibility. |
| **LLM client** | C | JSON parsing strict (must start with `{`); choices/text guarded; salvage can corrupt (BUGS §20); `--no-llm` available for heuristic-only; proxy risk (BUGS §16). |
| **Filename generation** | B | Sanitization, collision suffix, EXDEV path; length/reserved names and snakeCase delimiter issues (BUGS §12, §24). |
| **Rename / FS** | B | TOCTOU mitigated (rename-as-check); retry capped at 20 with clear error; EXDEV non-atomic (BUGS §18, §19). Single-process assumption documented. |
| **Data files** | B | data_path whitelist; clear FileNotFoundError; malformed JSON can still traceback at CLI (BUGS §6). |
| **Tests** | B | Unit tests for heuristics, text_utils, llm parsing, pdf_extract, renamer generate_filename, data_paths, cli. No E2E with real LLM. |
| **Docs / Harness** | A | README, RUNBOOK, ARCHITECTURE, DESIGN, exec-plans, BUGS_AND_FIXES, AGENTS.md; progressive disclosure in place. |

## Cross-cutting

| Area | Grade | Notes |
|------|-------|--------|
| **Security** | B | Local LLM only; proxy and reporting documented. No secrets in repo. |
| **Observability** | B | Structured logging; runbook; no metrics/APM. |
| **Agent legibility** | A | AGENTS.md map, docs/ layout, core-beliefs, ARCHITECTURE. |

## How to update

- After addressing items in BUGS_AND_FIXES, re-grade the affected domain.
- When adding a new domain (e.g. optional cloud adapter), add a row and grade it.
- Keep notes concise; link to BUGS_AND_FIXES or issues for detail.
