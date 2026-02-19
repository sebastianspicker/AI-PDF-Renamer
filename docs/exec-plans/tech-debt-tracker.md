# Tech debt tracker

Canonical list of technical debt and planned remediation. For full bug/fix detail see [BUGS_AND_FIXES.md](../../BUGS_AND_FIXES.md).

## Source of truth

- **Bugs and required fixes:** [BUGS_AND_FIXES.md](../../BUGS_AND_FIXES.md) (labels: bug, enhancement, operational, security). Detailed findings are tracked there or in GitHub issues.
- **Quality and reliability:** [QUALITY_SCORE.md](../QUALITY_SCORE.md), [RELIABILITY.md](../RELIABILITY.md).

## Tech debt categories

| Category | Description | Where tracked |
|----------|-------------|---------------|
| Critical | TOCTOU rename, LLM response parsing crash, proxy security | BUGS_AND_FIXES §14, §15, §16 |
| High | Collision suffix races, unbounded retry, EXDEV non-atomic, LLM JSON salvage, PDF extraction swallows errors, response must start with `{`, snakeCase delimiter | BUGS_AND_FIXES §17–§24 |
| Medium/Low | Case/argparse duplication, filename length/reserved names, date locale, token limits, logging | BUGS_AND_FIXES summary |

## Execution plans

- **active/** – Plans currently in progress (add markdown files per initiative).
- **completed/** – Closed plans (move from active when done; keep for history).

When opening a new multi-step initiative (e.g. “Add heuristic-only mode” or “Harden LLM parsing”), add a short exec plan under `active/` with goal, steps, and progress, and link from here if useful.
