# Agent map – AI-PDF-Renamer

This file is the **table of contents** for repository knowledge. Use it to find where design, architecture, product, and operations are documented. Do not treat this file as the full manual; follow pointers to the system of record in `docs/`.

## Quick orientation

- **What is this repo?** CLI tool to rename PDFs by content: extract text → heuristics + optional local LLM → deterministic filename (`YYYYMMDD-category-keywords-summary.pdf`).
- **Entry points:** `python ren.py` or `ai-pdf-renamer --dir <path>`; see [README](README.md) and [RUNBOOK](docs/RUNBOOK.md).

## Repository knowledge layout

```text
docs/
├── product-specs/        # Product requirements
│   └── PRD.md
├── exec-plans/           # Execution plans and tech debt
│   ├── active/
│   ├── completed/
│   └── tech-debt-tracker.md
├── ARCHITECTURE.md       # Top-level architecture, workflow (Mermaid), data flow
├── DESIGN.md             # Design overview and key decisions
├── PERFORMANCE.md        # 128K / Qwen3 8B performance (16GB VRAM, 32GB RAM)
├── QUALITY_SCORE.md      # Quality grades per area
├── RELIABILITY.md        # Failure modes and mitigations
├── RUNBOOK.md            # Setup, lint, test, security, troubleshooting
├── API.md                # Public API and library usage
└── RECOGNITION-RATE.md   # Heuristic vs LLM, recognition improvements
```

Root: [BUGS_AND_FIXES.md](BUGS_AND_FIXES.md) – known bugs and required fixes. Security: [SECURITY.md](SECURITY.md).

## Where to look for what

| If you need… | Look here |
|--------------|-----------|
| Product goals, requirements, personas | [docs/product-specs/PRD.md](docs/product-specs/PRD.md) |
| Architecture and data flow | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Design and key decisions | [docs/DESIGN.md](docs/DESIGN.md) |
| Heuristic vs LLM, recognition | [docs/RECOGNITION-RATE.md](docs/RECOGNITION-RATE.md) |
| Known bugs, required fixes, improvements | [BUGS_AND_FIXES.md](BUGS_AND_FIXES.md) |
| Tech debt and execution plans | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md), `docs/exec-plans/active/`, `completed/` |
| Setup, lint, test, security checks | [docs/RUNBOOK.md](docs/RUNBOOK.md) |
| Quality and reliability grades | [docs/QUALITY_SCORE.md](docs/QUALITY_SCORE.md), [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| 128K / Qwen3 8B performance (16GB VRAM, 32GB RAM) | [docs/PERFORMANCE.md](docs/PERFORMANCE.md) |
| Security policy and reporting | [SECURITY.md](SECURITY.md) |

## Conventions for agents

- **Code:** Python 3.13+ (see pyproject.toml). Lint: `ruff format`, `ruff check`. Tests: `pytest -q`. See [docs/RUNBOOK.md](docs/RUNBOOK.md).
- **Data files:** `heuristic_scores.json`, `meta_stopwords.json` in package data or `AI_PDF_RENAMER_DATA_DIR`. Do not allow path traversal in `data_path()`.
- **Boundaries:** Parse/validate at boundaries (e.g. LLM JSON, config); sanitize filenames; no cloud by default. See [docs/DESIGN.md](docs/DESIGN.md).
- **Changes:** For new features or behavior changes, align with [docs/product-specs/PRD.md](docs/product-specs/PRD.md) and [docs/DESIGN.md](docs/DESIGN.md). For bugs, prefer linking or updating [BUGS_AND_FIXES.md](BUGS_AND_FIXES.md) and opening issues.

## Harness engineering alignment

This repo uses a **Harness Engineering**–style layout ([OpenAI Harness Engineering](https://openai.com/index/harness-engineering/)):

- **AGENTS.md** = map, not encyclopedia; ~100 lines with pointers.
- **docs/** = system of record for design, architecture, exec plans.
- **Progressive disclosure:** Start here and in ARCHITECTURE.md; drill into exec-plans and RUNBOOK as needed.
- **Single source of truth:** Prefer versioned, in-repo artifacts over external docs or chat history.
