from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

from .data_paths import data_path
from .heuristics import HeuristicScorer, combine_categories, load_heuristic_rules
from .llm import (
    LocalLLMClient,
    get_document_category,
    get_document_keywords,
    get_document_summary,
    get_final_summary_tokens,
)
from .pdf_extract import pdf_to_text
from .text_utils import (
    Stopwords,
    clean_token,
    convert_case,
    extract_date_from_content,
    normalize_keywords,
    split_to_tokens,
    subtract_tokens,
)

logger = logging.getLogger(__name__)


def load_meta_stopwords(path: str | Path) -> Stopwords:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    words = {str(w).lower() for w in data.get("stopwords", []) if str(w).strip()}
    return Stopwords(words=words)


@lru_cache(maxsize=1)
def default_stopwords() -> Stopwords:
    return load_meta_stopwords(data_path("meta_stopwords.json"))


@lru_cache(maxsize=1)
def default_heuristic_scorer() -> HeuristicScorer:
    return HeuristicScorer(load_heuristic_rules(data_path("heuristic_scores.json")))


@dataclass(frozen=True)
class RenamerConfig:
    language: str = "de"
    desired_case: str = "kebabCase"
    project: str = ""
    version: str = ""


def generate_filename(
    pdf_content: str,
    *,
    config: RenamerConfig,
    llm_client: LocalLLMClient | None = None,
    heuristic_scorer: HeuristicScorer | None = None,
    stopwords: Stopwords | None = None,
    override_category: str | None = None,
    today: date | None = None,
) -> str:
    """
    Constructs the final filename:
    - date (YYYYMMDD)
    - optional project
    - category (heuristic + optional LLM)
    - keywords (<=3)
    - short summary tokens (<=5)
    - optional version
    """
    llm_client = llm_client or LocalLLMClient()
    stopwords = stopwords or default_stopwords()
    heuristic_scorer = heuristic_scorer or default_heuristic_scorer()

    # Date
    date_str = extract_date_from_content(pdf_content, today=today).replace("-", "")

    # LLM: summary -> keywords
    summary = get_document_summary(llm_client, pdf_content, language=config.language)
    raw_keywords = (
        get_document_keywords(llm_client, summary, language=config.language) or []
    )
    keywords = normalize_keywords(raw_keywords)

    # Category: override > heuristic + LLM
    if override_category is not None:
        category = override_category
    else:
        cat_llm = get_document_category(
            llm_client,
            summary=summary,
            keywords=keywords,
            language=config.language,
        )
        cat_heur = heuristic_scorer.best_category(pdf_content)
        category = combine_categories(cat_llm, cat_heur)

    # Short summary tokens for filename
    final_summary_tokens = (
        get_final_summary_tokens(
            llm_client,
            summary=summary,
            keywords=keywords,
            category=category,
            language=config.language,
        )
        or []
    )

    # Filter stopwords and clean
    category_tokens = stopwords.filter_tokens(split_to_tokens(category))
    keyword_tokens = stopwords.filter_tokens(keywords)[:3]
    summary_tokens = stopwords.filter_tokens(final_summary_tokens)[:5]

    # Avoid repetition (category -> keywords -> summary)
    category_clean = [clean_token(t) for t in category_tokens]
    keyword_clean = [clean_token(t) for t in keyword_tokens]
    summary_clean = [clean_token(t) for t in summary_tokens]

    keyword_clean = subtract_tokens(keyword_clean, category_clean)
    summary_clean = subtract_tokens(summary_clean, category_clean + keyword_clean)

    project = (config.project or "").strip()
    version = (config.version or "").strip()
    if project.lower() == "default":
        project = ""
    if version.lower() == "default":
        version = ""

    if config.desired_case == "camelCase":
        tokens: list[str] = [date_str]
        tokens += split_to_tokens(project) if project else []
        tokens += category_clean
        tokens += keyword_clean
        tokens += summary_clean
        tokens += split_to_tokens(version) if version else []
        return convert_case(tokens, "camelCase")

    parts: list[str] = [date_str]
    if project:
        parts.append(convert_case(split_to_tokens(project), config.desired_case))
    parts.append(convert_case(category_clean, config.desired_case))
    if keyword_clean:
        parts.append(convert_case(keyword_clean, config.desired_case))
    if summary_clean:
        parts.append(convert_case(summary_clean, config.desired_case))
    if version:
        parts.append(convert_case(split_to_tokens(version), config.desired_case))

    filename = "-".join(p for p in parts if p)
    filename = "-".join(x for x in filename.split("-") if x)
    return filename


def rename_pdfs_in_directory(
    directory: str | Path,
    *,
    config: RenamerConfig,
) -> None:
    path = Path(directory)
    files = [
        p
        for p in path.iterdir()
        if p.is_file() and p.suffix.lower() == ".pdf" and not p.name.startswith(".")
    ]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for file_path in files:
        logger.info("Processing file: %s", file_path)
        content = pdf_to_text(file_path)
        if not content.strip():
            logger.info("PDF appears to be empty. Skipping.")
            continue

        new_base = generate_filename(content, config=config)
        base = new_base
        counter = 1
        target = file_path.with_name(new_base + file_path.suffix)
        while target.exists():
            new_base = f"{base}_{counter}"
            target = file_path.with_name(new_base + file_path.suffix)
            counter += 1

        os.rename(file_path, target)
        logger.info("Renamed '%s' to '%s'", file_path.name, target.name)
