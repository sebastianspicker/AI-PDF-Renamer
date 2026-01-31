from __future__ import annotations

from ai_pdf_renamer.llm import parse_json_field


def test_parse_json_field_string() -> None:
    assert parse_json_field('{"summary":"Hello"}', key="summary") == "Hello"


def test_parse_json_field_list() -> None:
    assert parse_json_field('{"keywords":["A","B"]}', key="keywords") == ["A", "B"]


def test_parse_json_field_invalid_returns_none() -> None:
    assert parse_json_field("not json", key="summary") is None


def test_parse_json_field_sanitizes_quotes() -> None:
    # Unescaped quotes inside value should be fixed by sanitizer.
    raw = '{"summary":"He said "hello" today"}'
    assert parse_json_field(raw, key="summary") == 'He said "hello" today'
