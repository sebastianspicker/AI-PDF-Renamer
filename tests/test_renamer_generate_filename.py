from __future__ import annotations

import re
from datetime import date

from ai_pdf_renamer.heuristics import HeuristicRule, HeuristicScorer
from ai_pdf_renamer.renamer import RenamerConfig, generate_filename
from ai_pdf_renamer.text_utils import Stopwords


def test_generate_filename_stopwords_and_dedup(monkeypatch) -> None:
    import ai_pdf_renamer.renamer as renamer_mod

    monkeypatch.setattr(
        renamer_mod, "get_document_summary", lambda *a, **k: "Some summary"
    )
    monkeypatch.setattr(
        renamer_mod,
        "get_document_keywords",
        lambda *a, **k: ["invoice", "summary", "tax"],
    )
    monkeypatch.setattr(renamer_mod, "get_document_category", lambda *a, **k: "invoice")
    monkeypatch.setattr(
        renamer_mod,
        "get_final_summary_tokens",
        lambda *a, **k: ["invoice", "payment", "json"],
    )

    scorer = HeuristicScorer(
        rules=[
            HeuristicRule(
                pattern=re.compile("invoice", re.IGNORECASE),
                category="invoice",
                score=10,
            )
        ]
    )
    stopwords = Stopwords(words={"summary", "json"})

    name = generate_filename(
        "Invoice dated 2024-01-09",
        config=RenamerConfig(language="de", desired_case="kebabCase"),
        llm_client=object(),  # unused due to monkeypatching
        heuristic_scorer=scorer,
        stopwords=stopwords,
        today=date(2000, 1, 1),
    )

    assert name == "20240109-invoice-tax-payment"


def test_generate_filename_camel_case(monkeypatch) -> None:
    import ai_pdf_renamer.renamer as renamer_mod

    monkeypatch.setattr(renamer_mod, "get_document_summary", lambda *a, **k: "x")
    monkeypatch.setattr(
        renamer_mod, "get_document_keywords", lambda *a, **k: ["Foo Bar"]
    )
    monkeypatch.setattr(
        renamer_mod, "get_document_category", lambda *a, **k: "My Category"
    )
    monkeypatch.setattr(
        renamer_mod, "get_final_summary_tokens", lambda *a, **k: ["Baz"]
    )

    name = generate_filename(
        "2024-02-01",
        config=RenamerConfig(language="de", desired_case="camelCase"),
        llm_client=object(),
        heuristic_scorer=HeuristicScorer(rules=[]),
        stopwords=Stopwords(words=set()),
        today=date(2000, 1, 1),
    )
    assert name.startswith("20240201")
    assert "MyCategory" in name
