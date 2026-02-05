from __future__ import annotations

from datetime import date

import pytest

from ai_pdf_renamer.text_utils import (
    chunk_text,
    convert_case,
    extract_date_from_content,
    normalize_keywords,
    subtract_tokens,
    tokens_similar,
)


def test_extract_date_from_content_ymd() -> None:
    assert (
        extract_date_from_content("Hello 2024-01-09 world", today=date(2000, 1, 1))
        == "2024-01-09"
    )


def test_extract_date_from_content_dmy() -> None:
    assert (
        extract_date_from_content("Hello 9.1.2024 world", today=date(2000, 1, 1))
        == "2024-01-09"
    )


def test_extract_date_from_content_fallback_today() -> None:
    assert (
        extract_date_from_content("No dates here", today=date(2022, 12, 31))
        == "2022-12-31"
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
