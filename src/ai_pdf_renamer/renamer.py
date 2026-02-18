from __future__ import annotations

import errno
import json
import logging
import os
import re
import shutil
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

# Path separators and control characters (incl. NUL) that must not appear in filenames.
_FILENAME_UNSAFE_RE = re.compile(r"[\x00-\x1f\x7f/\\:*?\"<>|]")


def _sanitize_filename_base(name: str) -> str:
    """Remove path separators and control chars; ensure non-empty."""
    if not name or not name.strip():
        return "unnamed"
    safe = _FILENAME_UNSAFE_RE.sub("", name.strip())
    return safe.strip() or "unnamed"


logger = logging.getLogger(__name__)


def load_meta_stopwords(path: str | Path) -> Stopwords:
    path_obj = Path(path)
    try:
        raw = path_obj.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(
            f"Could not read data file {path_obj.name!r}: {exc!s}"
        ) from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in data file {path_obj.name!r}. {exc!s}"
        ) from exc
    raw = data.get("stopwords", [])
    if not isinstance(raw, list):
        raw = []
    words = {str(w).lower() for w in raw if str(w).strip()}
    return Stopwords(words=words)


@lru_cache(maxsize=32)
def _stopwords_cached(path_str: str) -> Stopwords:
    return load_meta_stopwords(Path(path_str))


def default_stopwords() -> Stopwords:
    return _stopwords_cached(str(data_path("meta_stopwords.json")))


@lru_cache(maxsize=32)
def _heuristic_scorer_cached(path_str: str) -> HeuristicScorer:
    return HeuristicScorer(load_heuristic_rules(Path(path_str)))


def default_heuristic_scorer() -> HeuristicScorer:
    return _heuristic_scorer_cached(str(data_path("heuristic_scores.json")))


_VALID_DESIRED_CASES = frozenset({"camelCase", "kebabCase", "snakeCase"})
_VALID_DATE_LOCALES = frozenset({"dmy", "mdy"})


@dataclass(frozen=True)
class RenamerConfig:
    language: str = "de"
    desired_case: str = "kebabCase"
    project: str = ""
    version: str = ""
    prefer_llm_category: bool = False
    date_locale: str = "dmy"

    def __post_init__(self) -> None:
        if self.desired_case not in _VALID_DESIRED_CASES:
            raise ValueError(
                f"desired_case must be one of {sorted(_VALID_DESIRED_CASES)}, "
                f"got {self.desired_case!r}"
            )
        loc = (self.date_locale or "dmy").strip().lower()
        if loc not in _VALID_DATE_LOCALES:
            raise ValueError(
                f"date_locale must be one of {sorted(_VALID_DATE_LOCALES)}, "
                f"got {self.date_locale!r}"
            )


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
    if pdf_content is None or not isinstance(pdf_content, str):
        raise ValueError("pdf_content must be a non-None string")
    llm_client = llm_client or LocalLLMClient()
    stopwords = stopwords or default_stopwords()
    heuristic_scorer = heuristic_scorer or default_heuristic_scorer()

    # Date
    date_str = extract_date_from_content(
        pdf_content, today=today, date_locale=config.date_locale
    ).replace("-", "")

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
        category = combine_categories(
            cat_llm, cat_heur, prefer_llm=config.prefer_llm_category
        )

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

    sep = "_" if config.desired_case == "snakeCase" else "-"
    filename = sep.join(p for p in parts if p)
    filename = sep.join(x for x in filename.split(sep) if x)
    return filename


def rename_pdfs_in_directory(
    directory: str | Path,
    *,
    config: RenamerConfig,
) -> None:
    dir_str = str(directory).strip()
    if not dir_str:
        raise ValueError(
            "Directory path must be non-empty. Use --dir or provide when prompted."
        )
    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(f"Directory does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    files = [
        p
        for p in path.iterdir()
        if p.is_file() and p.suffix.lower() == ".pdf" and not p.name.startswith(".")
    ]

    def _mtime_key(p: Path) -> float:
        try:
            return p.stat().st_mtime
        except OSError:
            return 0.0

    files.sort(key=_mtime_key, reverse=True)

    renamed_count = 0
    skipped_count = 0
    failed_count = 0

    for file_path in files:
        logger.info("Processing file: %s", file_path)
        try:
            content = pdf_to_text(file_path)
        except Exception as exc:
            logger.exception("Failed to extract text from %s: %s", file_path, exc)
            failed_count += 1
            continue
        if not content.strip():
            try:
                size = file_path.stat().st_size
            except OSError:
                size = 0
            if size > 0:
                logger.warning(
                    "PDF appears empty but has %s bytes; "
                    "extraction may have failed: %s",
                    size,
                    file_path,
                )
            else:
                logger.info("PDF appears to be empty. Skipping.")
            skipped_count += 1
            continue

        try:
            new_base = _sanitize_filename_base(
                generate_filename(content, config=config)
            )
        except Exception as exc:
            logger.exception("Failed to generate filename for %s: %s", file_path, exc)
            failed_count += 1
            continue

        try:
            base = new_base
            counter = 1
            target = file_path.with_name(new_base + file_path.suffix)
            max_rename_retries = 100
            retries = 0
            renamed_this = False
            while retries < max_rename_retries:
                while target.exists():
                    new_base = f"{base}_{counter}"
                    target = file_path.with_name(new_base + file_path.suffix)
                    counter += 1
                try:
                    os.rename(file_path, target)
                    renamed_this = True
                    break
                except FileExistsError:
                    counter += 1
                    target = file_path.with_name(f"{base}_{counter}" + file_path.suffix)
                except OSError as e:
                    if (
                        getattr(errno, "ENAMETOOLONG", None) is not None
                        and e.errno == errno.ENAMETOOLONG
                    ):
                        raise OSError(
                            e.errno,
                            f"Filename too long for filesystem: {target.name!r}. "
                            "Shorten project/version or content-derived parts.",
                        ) from e
                    if e.errno == errno.EXDEV:
                        try:
                            shutil.copy2(file_path, target)
                        except OSError as copy_err:
                            if target.exists():
                                try:
                                    target.unlink()
                                except OSError:
                                    pass
                            raise copy_err
                        try:
                            file_path.unlink()
                        except OSError as unlink_err:
                            try:
                                target.unlink()
                            except OSError:
                                pass
                            raise OSError(
                                f"Cross-filesystem rename: copied to {target}, "
                                f"could not remove source {file_path}: {unlink_err}"
                            ) from unlink_err
                        renamed_this = True
                        break
                    raise
                retries += 1
            if not renamed_this:
                logger.error(
                    "Skipping %s: could not rename after %s attempts "
                    "(target exists or contention)",
                    file_path.name,
                    max_rename_retries,
                )
                failed_count += 1
                continue
            renamed_count += 1
            logger.info("Renamed '%s' to '%s'", file_path.name, target.name)
        except Exception as exc:
            logger.exception("Failed to process %s: %s", file_path, exc)
            failed_count += 1

    if not files:
        logger.info("No PDFs found in %s", path)
    else:
        logger.info(
            "Summary: %s file(s) processed, %s renamed, %s skipped, %s failed",
            len(files),
            renamed_count,
            skipped_count,
            failed_count,
        )
