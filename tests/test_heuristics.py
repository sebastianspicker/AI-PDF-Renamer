from __future__ import annotations

import re

from ai_pdf_renamer.heuristics import (
    HeuristicRule,
    HeuristicScorer,
    combine_categories,
    normalize_llm_category,
)


def test_heuristic_scorer_best_category() -> None:
    rules = [
        HeuristicRule(pattern=re.compile("invoice", re.IGNORECASE), category="invoice", score=2.0),
        HeuristicRule(pattern=re.compile("receipt", re.IGNORECASE), category="receipt", score=5.0),
    ]
    scorer = HeuristicScorer(rules=rules)
    assert scorer.best_category("This is an invoice and a receipt") == "receipt"


def test_heuristic_scorer_best_category_with_confidence() -> None:
    rules = [
        HeuristicRule(pattern=re.compile("invoice", re.IGNORECASE), category="invoice", score=2.0),
        HeuristicRule(pattern=re.compile("receipt", re.IGNORECASE), category="receipt", score=5.0),
    ]
    scorer = HeuristicScorer(rules=rules)
    cat, best, runner_cat, runner_score = scorer.best_category_with_confidence("This is an invoice and a receipt")
    assert cat == "receipt"
    assert best == 5.0
    assert runner_cat == "invoice"
    assert runner_score == 2.0


def test_heuristic_scorer_min_score_gap_returns_unknown() -> None:
    rules = [
        HeuristicRule(pattern=re.compile("invoice", re.IGNORECASE), category="invoice", score=2.0),
        HeuristicRule(pattern=re.compile("receipt", re.IGNORECASE), category="receipt", score=2.0),
    ]
    scorer = HeuristicScorer(rules=rules)
    cat, best, runner_cat, runner_score = scorer.best_category_with_confidence("invoice and receipt", min_score_gap=1.0)
    assert cat == "unknown"
    assert best == 0.0
    assert runner_cat == "unknown"
    assert runner_score == 0.0


def test_heuristic_scorer_language_filter() -> None:
    rules = [
        HeuristicRule(
            pattern=re.compile("rechnung", re.IGNORECASE),
            category="invoice",
            score=4.0,
            language="de",
        ),
        HeuristicRule(
            pattern=re.compile("invoice", re.IGNORECASE),
            category="invoice",
            score=4.0,
            language="en",
        ),
    ]
    scorer = HeuristicScorer(rules=rules)
    assert scorer.best_category("Rechnung", language="de") == "invoice"
    assert scorer.best_category("Rechnung", language="en") == "unknown"
    assert scorer.best_category("invoice", language="en") == "invoice"
    assert scorer.best_category("invoice", language="de") == "unknown"


def test_combine_categories_prefers_llm_by_default() -> None:
    """When prefer_llm=True (config default), on conflict use LLM."""
    assert combine_categories("invoice", "unknown") == "invoice"
    assert combine_categories("invoice", "receipt", prefer_llm=True) == "invoice"


def test_combine_categories_prefer_heuristic_when_asked() -> None:
    """With prefer_llm=False, heuristic wins on conflict."""
    assert combine_categories("invoice", "receipt", prefer_llm=False) == "receipt"


def test_normalize_llm_category() -> None:
    """LLM output is mapped to heuristic vocabulary."""
    aliases = {"rechnung": "invoice", "lohnabrechnung": "payslip", "invoice": "invoice"}
    assert normalize_llm_category("Rechnung", _aliases=aliases) == "invoice"
    assert normalize_llm_category("invoice", _aliases=aliases) == "invoice"
    assert normalize_llm_category("Lohnabrechnung", _aliases=aliases) == "payslip"
    assert normalize_llm_category("unknown", _aliases=aliases) == "unknown"
    assert normalize_llm_category("something_else", _aliases=aliases) == "something_else"


def test_combine_categories_parent_match_uses_heuristic() -> None:
    """LLM parent + heuristic child (or vice versa) -> agreement, use heuristic."""
    parent_map = {"motor_insurance": "insurance", "health_insurance": "insurance"}
    assert (
        combine_categories(
            "insurance",
            "motor_insurance",
            category_parent_map=parent_map,
        )
        == "motor_insurance"
    )
    assert (
        combine_categories(
            "motor_insurance",
            "motor_insurance",
            category_parent_map=parent_map,
        )
        == "motor_insurance"
    )


def test_combine_categories_min_heuristic_score_prefers_llm() -> None:
    assert (
        combine_categories(
            "contract",
            "invoice",
            heuristic_score=1.0,
            min_heuristic_score=2.0,
        )
        == "contract"
    )
    assert (
        combine_categories(
            "contract",
            "invoice",
            heuristic_score=3.0,
            min_heuristic_score=2.0,
        )
        == "invoice"
    )


def test_combine_categories_keyword_overlap_favors_llm_when_higher() -> None:
    """With use_keyword_overlap, higher overlap with LLM category -> pick LLM."""
    context = "Kfz Versicherung premium motor insurance document"
    assert (
        combine_categories(
            "motor_insurance",
            "invoice",
            context_for_overlap=context,
            use_keyword_overlap=True,
        )
        == "motor_insurance"
    )


def test_combine_categories_keyword_overlap_favors_heuristic_when_higher() -> None:
    """With use_keyword_overlap, higher overlap with heuristic -> pick heuristic."""
    context = "Rechnung Rechnungsnummer invoice total"
    assert (
        combine_categories(
            "motor_insurance",
            "invoice",
            context_for_overlap=context,
            use_keyword_overlap=True,
        )
        == "invoice"
    )


def test_combine_categories_keyword_overlap_tie_keeps_heuristic() -> None:
    """When overlap is equal, heuristic wins."""
    context = "document summary"
    assert (
        combine_categories(
            "contract",
            "invoice",
            context_for_overlap=context,
            use_keyword_overlap=True,
        )
        == "invoice"
    )


def test_get_display_category_specific() -> None:
    """specific: return category as-is."""
    rules = [
        HeuristicRule(
            pattern=re.compile("x", re.IGNORECASE),
            category="motor_insurance",
            score=1.0,
            parent="insurance",
        ),
    ]
    scorer = HeuristicScorer(rules=rules)
    assert scorer.get_display_category("motor_insurance", "specific") == "motor_insurance"
    assert scorer.get_display_category("invoice", "specific") == "invoice"


def test_get_display_category_with_parent() -> None:
    """with_parent: parent_category when parent set."""
    rules = [
        HeuristicRule(
            pattern=re.compile("x", re.IGNORECASE),
            category="motor_insurance",
            score=1.0,
            parent="insurance",
        ),
    ]
    scorer = HeuristicScorer(rules=rules)
    assert scorer.get_display_category("motor_insurance", "with_parent") == "insurance_motor_insurance"
    assert scorer.get_display_category("invoice", "with_parent") == "invoice"


def test_get_display_category_parent_only() -> None:
    """parent_only: return parent when set."""
    rules = [
        HeuristicRule(
            pattern=re.compile("x", re.IGNORECASE),
            category="motor_insurance",
            score=1.0,
            parent="insurance",
        ),
    ]
    scorer = HeuristicScorer(rules=rules)
    assert scorer.get_display_category("motor_insurance", "parent_only") == "insurance"
    assert scorer.get_display_category("invoice", "parent_only") == "invoice"


def test_top_n_categories() -> None:
    """top_n_categories returns up to n categories by score."""
    rules = [
        HeuristicRule(pattern=re.compile("a", re.IGNORECASE), category="cat_a", score=3.0),
        HeuristicRule(pattern=re.compile("b", re.IGNORECASE), category="cat_b", score=2.0),
        HeuristicRule(pattern=re.compile("c", re.IGNORECASE), category="cat_c", score=1.0),
    ]
    scorer = HeuristicScorer(rules=rules)
    top = scorer.top_n_categories("a b c", n=3)
    assert top == ["cat_a", "cat_b", "cat_c"]
    assert scorer.top_n_categories("a b c", n=2) == ["cat_a", "cat_b"]
    assert scorer.top_n_categories("", n=5) == []


def test_all_categories() -> None:
    """all_categories returns frozenset of rule categories."""
    rules = [
        HeuristicRule(pattern=re.compile("x", re.IGNORECASE), category="invoice", score=1.0),
        HeuristicRule(pattern=re.compile("y", re.IGNORECASE), category="receipt", score=1.0),
    ]
    scorer = HeuristicScorer(rules=rules)
    assert scorer.all_categories() == frozenset({"invoice", "receipt"})


def test_combine_categories_sibling_uses_heuristic() -> None:
    """Sibling categories (same parent) -> use heuristic."""
    parent_map = {
        "motor_insurance": "insurance",
        "health_insurance": "insurance",
    }
    assert (
        combine_categories(
            "health_insurance",
            "motor_insurance",
            category_parent_map=parent_map,
        )
        == "motor_insurance"
    )


def test_combine_categories_high_confidence_override() -> None:
    """When score and gap above threshold, use heuristic; else normal resolution."""
    assert (
        combine_categories(
            "contract",
            "invoice",
            heuristic_score=6.0,
            heuristic_gap=3.0,
            heuristic_override_min_score=5.0,
            heuristic_override_min_gap=2.0,
        )
        == "invoice"
    )
    # Below threshold: no override; prefer_llm=False -> heuristic wins
    assert (
        combine_categories(
            "contract",
            "invoice",
            heuristic_score=4.0,
            heuristic_gap=3.0,
            heuristic_override_min_score=5.0,
            heuristic_override_min_gap=2.0,
        )
        == "invoice"
    )


def test_combine_categories_heuristic_score_weight() -> None:
    """Heuristic score weight can tip overlap tie toward heuristic."""
    context = "document text"
    # Without weight: tie -> heuristic. With weight: heuristic gets bonus.
    assert (
        combine_categories(
            "invoice",
            "receipt",
            context_for_overlap=context,
            use_keyword_overlap=True,
            heuristic_score=10.0,
            heuristic_score_weight=0.1,
        )
        == "receipt"
    )
