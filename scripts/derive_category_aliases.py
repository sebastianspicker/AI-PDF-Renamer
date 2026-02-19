#!/usr/bin/env python3
"""
Derive suggested category aliases from heuristic_scores.json.

Reads patterns (regex, category), extracts word-like tokens from regex strings,
and outputs a JSON fragment that can be merged into category_aliases.json.
Review output before merging: regex tokens can be noisy.

Usage:
  python scripts/derive_category_aliases.py [path_to_heuristic_scores.json]
  # Or from repo root with package:
  PYTHONPATH=src python scripts/derive_category_aliases.py

Output: JSON object with "aliases" key (alias -> category). Merge manually
into category_aliases.json or use for review.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _tokenize_regex(regex: str) -> list[str]:
    """Extract word-like tokens from a regex string (literals, alternations)."""
    # Remove (?i) and similar prefixes
    s = re.sub(r"^\s*\(\?[a-z]*\)\s*", "", regex)
    # Split by \b, \\, |, parentheses, etc., keep sequences of letters (and _)
    tokens = re.findall(r"[a-zA-Z\u00c0-\u024f_]+", s)
    return [t for t in tokens if len(t) >= 2 and t.lower() not in ("true", "false")]


def derive_aliases(patterns: list[dict]) -> dict[str, str]:
    """Build alias -> category from pattern regex/category. Later rules override."""
    aliases: dict[str, str] = {}
    for entry in patterns:
        regex = entry.get("regex")
        category = entry.get("category")
        if not isinstance(regex, str) or not isinstance(category, str):
            continue
        category_norm = category.strip().lower().replace(" ", "_")
        for token in _tokenize_regex(regex):
            key = token.lower().replace(" ", "_")
            if key and key != category_norm:
                aliases[key] = category_norm
    return aliases


def main() -> int:
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        try:
            from ai_pdf_renamer.data_paths import data_path

            path = data_path("heuristic_scores.json")
        except Exception as e:
            print(
                "Usage: derive_category_aliases.py [path_to_heuristic_scores.json]",
                file=sys.stderr,
            )
            print(f"Error: {e}", file=sys.stderr)
            return 1
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 1
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    patterns = data.get("patterns", [])
    if not isinstance(patterns, list):
        print("Expected 'patterns' array in JSON", file=sys.stderr)
        return 1
    aliases = derive_aliases(patterns)
    print(json.dumps({"aliases": aliases}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
