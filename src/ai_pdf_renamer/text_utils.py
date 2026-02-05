from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

_DATE_RE_YMD = re.compile(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b")
_DATE_RE_DMY = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b")


def extract_date_from_content(content: str, *, today: date | None = None) -> str:
    """
    Searches the text for date formats (YYYY-MM-DD or DD.MM.YYYY) and returns
    'YYYY-MM-DD'. If no date is found (or parsing fails), returns today's date.
    """
    if today is None:
        today = date.today()

    match = _DATE_RE_YMD.search(content)
    if match:
        year, month, day = match.groups()
        try:
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        except ValueError:
            pass

    match = _DATE_RE_DMY.search(content)
    if match:
        day, month, year = match.groups()
        try:
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        except ValueError:
            pass

    return today.strftime("%Y-%m-%d")


def chunk_text(text: str, *, chunk_size: int = 8000, overlap: int = 1000) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be < chunk_size")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def tokens_similar(token_a: str, token_b: str) -> bool:
    a = token_a.lower()
    b = token_b.lower()
    if a == b:
        return True
    if (a.startswith(b) or b.startswith(a)) and abs(len(a) - len(b)) <= 2:
        return True
    return False


def subtract_tokens(
    main_tokens: Iterable[str], remove_tokens: Iterable[str]
) -> list[str]:
    remove = [t for t in (rt.strip() for rt in remove_tokens) if t]
    result: list[str] = []
    for token in (t.strip() for t in main_tokens):
        if not token:
            continue
        if any(tokens_similar(token, rt) for rt in remove):
            continue
        result.append(token)
    return result


def normalize_keywords(raw: str | list[str]) -> list[str]:
    if isinstance(raw, list):
        tokens = raw
    else:
        tokens = [t.strip() for t in raw.split(",")]

    filtered: list[str] = []
    for token in tokens:
        t = token.strip()
        if not t:
            continue
        if t.lower() in {"...", "…", "na", "xxx", "w1", "w2"}:
            continue
        filtered.append(t)
    return filtered[:7]


def clean_token(text: str) -> str:
    """
    Normalizes a token for filenames:
    - trims whitespace
    - replaces German umlauts
    - removes forbidden characters
    - converts whitespace to underscores
    - lowercases
    """
    text = text.strip()
    if not text:
        return "na"
    text = (
        text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    )
    text = re.sub(r'[\\/:*?"<>|]', "", text)
    text = re.sub(r"\s+", "_", text)
    return text.lower()


def convert_case(tokens: Iterable[str], desired_case: str) -> str:
    words = [w for w in (clean_token(t) for t in tokens) if w and w != "na"]
    if desired_case == "camelCase":
        split_words: list[str] = []
        for word in words:
            split_words.extend([w for w in word.split("_") if w])
        words = split_words
    if not words:
        return ""

    if desired_case == "camelCase":
        first = words[0].lower()
        rest = "".join(w.capitalize() for w in words[1:])
        return first + rest
    if desired_case == "snakeCase":
        return "_".join(w.lower() for w in words)
    # default: kebabCase
    return "-".join(w.lower() for w in words)


@dataclass(frozen=True)
class Stopwords:
    words: set[str]

    def filter_tokens(self, tokens: Iterable[str]) -> list[str]:
        out: list[str] = []
        for token in tokens:
            t = token.strip()
            if not t:
                continue
            if t.lower() in self.words:
                continue
            out.append(t)
        return out


def split_to_tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[\s,_-]+", text) if t]
