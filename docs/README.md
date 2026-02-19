# Documentation Index

This directory contains technical and product documentation for **AI-PDF-Renamer**. All documents are in English unless otherwise noted.

---

## Core documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | High-level architecture: domains, components, data flow, key files, external boundaries. |
| [RUNBOOK.md](RUNBOOK.md) | Reproducible setup, lint, test, build, and run commands; environment variables; Ollama 128K, GUI, options. |
| [API.md](API.md) | Public API and library usage (`generate_filename`, `rename_pdfs_in_directory`). |

---

## Product and design

| Document | Description |
|----------|-------------|
| [product-specs/PRD.md](product-specs/PRD.md) | Product goals, requirements, personas. |
| [DESIGN.md](DESIGN.md) | Design notes and key decisions. |
| [PERFORMANCE.md](PERFORMANCE.md) | Performance considerations, 128K context, workers, timeouts. |
| [RECOGNITION-RATE.md](RECOGNITION-RATE.md) | Who leads (heuristic vs. LLM), Qwen-128K usage, recognition-rate improvements. |
| [RELIABILITY.md](RELIABILITY.md) | Reliability and failure handling. |
| [QUALITY_SCORE.md](QUALITY_SCORE.md) | Quality scoring. |

---

## Bugs and execution plans

| Document | Description |
|----------|-------------|
| [../BUGS_AND_FIXES.md](../BUGS_AND_FIXES.md) | Known bugs, required fixes, and improvement notes (repository root). |
| [exec-plans/tech-debt-tracker.md](exec-plans/tech-debt-tracker.md) | Tech-debt tracking and remediation. |

---

## Quick links from repository root

- **Usage and install:** [../README.md](../README.md)
- **Contributing:** [../CONTRIBUTING.md](../CONTRIBUTING.md)
- **Security:** [../SECURITY.md](../SECURITY.md)
- **Agent map:** [../AGENTS.md](../AGENTS.md)
