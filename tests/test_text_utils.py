from __future__ import annotations

from datetime import date

import pytest

from ai_pdf_renamer.text_utils import (
    chunk_text,
    convert_case,
    extract_date_from_content,
    extract_structured_fields,
    normalize_keywords,
    subtract_tokens,
    tokens_similar,
)


def test_extract_date_from_content_ymd() -> None:
    assert extract_date_from_content("Hello 2024-01-09 world", today=date(2000, 1, 1)) == "2024-01-09"


def test_extract_date_from_content_dmy() -> None:
    assert extract_date_from_content("Hello 9.1.2024 world", today=date(2000, 1, 1)) == "2024-01-09"


def test_extract_date_from_content_fallback_today() -> None:
    assert extract_date_from_content("No dates here", today=date(2022, 12, 31)) == "2022-12-31"


def test_extract_date_stand_and_month_year() -> None:
    assert (
        extract_date_from_content(
            "Stand: 18.02.2025\nFooter 2020",
            today=date(2000, 1, 1),
        )
        == "2025-02-18"
    )
    assert (
        extract_date_from_content(
            "January 2025",
            today=date(2000, 1, 1),
        )
        == "2025-01-01"
    )
    assert (
        extract_date_from_content(
            "Februar 2024",
            today=date(2000, 1, 1),
        )
        == "2024-02-01"
    )


def test_extract_date_prefer_leading_chars() -> None:
    # Document date in header; footer has different date
    text = "Rechnung 15.03.2024\n" + "x" * 5000 + "\nGedruckt am 01.01.2020"
    assert (
        extract_date_from_content(
            text,
            today=date(2000, 1, 1),
            prefer_leading_chars=8000,
        )
        == "2024-03-15"
    )
    # When leading region has a date, we use it (so footer date ignored)
    text2 = "Gedruckt 01.01.2020\n" + "y" * 5000 + "\nRechnung 15.03.2024"
    assert (
        extract_date_from_content(
            text2,
            today=date(2000, 1, 1),
            prefer_leading_chars=200,
        )
        == "2020-01-01"
    )
    # Leading 10000 chars contains both; first match wins (2020-01-01)
    assert (
        extract_date_from_content(
            text2,
            today=date(2000, 1, 1),
            prefer_leading_chars=10000,
        )
        == "2020-01-01"
    )


def test_chunk_text_validation() -> None:
    with pytest.raises(ValueError):
        chunk_text("abc", chunk_size=0, overlap=0)
    with pytest.raises(ValueError):
        chunk_text("abc", chunk_size=10, overlap=10)


def test_normalize_keywords_filters_placeholders() -> None:
    assert normalize_keywords("a, ..., na, b, w1, c") == ["a", "b", "c"]


def test_subtract_tokens_removes_similar() -> None:
    assert subtract_tokens(["invoice", "foo"], ["invoice"]) == ["foo"]


def test_convert_case_kebab_and_camel() -> None:
    assert convert_case(["Hello", "World"], "kebabCase") == "hello-world"
    assert convert_case(["Hello", "World"], "camelCase") == "helloWorld"


def test_convert_case_camel_splits_underscores() -> None:
    assert convert_case(["foo_bar", "baz"], "camelCase") == "fooBarBaz"


def test_tokens_similar_prefix_tolerance() -> None:
    assert tokens_similar("invoice", "invoice")
    assert tokens_similar("invoice", "invoi")
    assert tokens_similar("invoi", "invoice")
    assert not tokens_similar("invoice", "receipt")


def test_extract_structured_fields_invoice_id() -> None:
    text = "Rechnungsnummer: INV-2025-001\nBetrag: 1.234,56 EUR"
    out = extract_structured_fields(text)
    assert out["invoice_id"] == "INV-2025-001"
    assert out["amount"]
    assert "1234" in out["amount"] or "1.234" in out["amount"]


def test_extract_structured_fields_empty() -> None:
    assert extract_structured_fields("") == {
        "invoice_id": "",
        "amount": "",
        "company": "",
    }
    assert extract_structured_fields(None) == {
        "invoice_id": "",
        "amount": "",
        "company": "",
    }
