from __future__ import annotations

import re

from ai_pdf_renamer.heuristics import HeuristicRule, HeuristicScorer, combine_categories


def test_heuristic_scorer_best_category() -> None:
    rules = [
        HeuristicRule(
            pattern=re.compile("invoice", re.IGNORECASE), category="invoice", score=2.0
        ),
        HeuristicRule(
            pattern=re.compile("receipt", re.IGNORECASE), category="receipt", score=5.0
        ),
    ]
    scorer = HeuristicScorer(rules=rules)
    assert scorer.best_category("This is an invoice and a receipt") == "receipt"


def test_combine_categories_prefers_heuristic_when_available() -> None:
    assert combine_categories("invoice", "unknown") == "invoice"
    assert combine_categories("invoice", "receipt") == "receipt"
