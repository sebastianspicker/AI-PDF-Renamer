from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HeuristicRule:
    pattern: re.Pattern[str]
    category: str
    score: float


def load_heuristic_rules(path: str | Path) -> list[HeuristicRule]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rules: list[HeuristicRule] = []
    raw_patterns = data.get("patterns", [])
    if not isinstance(raw_patterns, list):
        raw_patterns = []

    for entry in raw_patterns:
        regex = entry.get("regex")
        category = entry.get("category")
        score = entry.get("score")
        if not isinstance(regex, str) or not isinstance(category, str):
            continue
        try:
            compiled = re.compile(regex)
        except re.error as exc:
            logger.warning("Invalid regex skipped: %r (%s)", regex, exc)
            continue
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            score_f = 0.0
        rules.append(HeuristicRule(pattern=compiled, category=category, score=score_f))

    return rules


@dataclass(frozen=True)
class HeuristicScorer:
    rules: list[HeuristicRule]

    def best_category(self, text: str) -> str:
        scores: dict[str, float] = {}
        for rule in self.rules:
            if rule.pattern.search(text):
                scores[rule.category] = scores.get(rule.category, 0.0) + rule.score

        if not scores:
            return "unknown"

        best_cat = max(scores, key=scores.get)
        logger.info("Heuristic scoring result: %s. Best: %s", scores, best_cat)
        return best_cat


def combine_categories(cat_llm: str, cat_heuristic: str) -> str:
    if cat_heuristic == "unknown":
        return cat_llm
    if cat_llm in {"document", "unknown", "na", ""}:
        return cat_heuristic
    if cat_llm != cat_heuristic:
        logger.info(
            "Conflict: LLM category=%s, Heuristic=%s. Prioritizing heuristic.",
            cat_llm,
            cat_heuristic,
        )
        return cat_heuristic
    return cat_llm
