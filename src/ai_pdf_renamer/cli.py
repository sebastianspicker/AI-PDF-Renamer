from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable

from .logging_utils import setup_logging
from .renamer import RenamerConfig, rename_pdfs_in_directory


def _is_interactive() -> bool:
    """True if stdin is a TTY (interactive prompt is safe)."""
    return sys.stdin.isatty()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Rename PDFs based on their content.")
    p.add_argument(
        "--dir",
        default=None,
        help="Directory containing PDFs (default: ./input_files)",
    )
    p.add_argument(
        "--language", default=None, choices=["de", "en"], help="Prompt language"
    )
    p.add_argument(
        "--case",
        dest="desired_case",
        default=None,
        choices=["camelCase", "kebabCase", "snakeCase"],
        help="Filename case format",
    )
    p.add_argument("--project", default=None, help="Optional project name")
    p.add_argument("--version", default=None, help="Optional version")
    p.add_argument(
        "--prefer-llm",
        dest="prefer_llm_category",
        action="store_true",
        help="When category conflicts, use LLM suggestion instead of heuristic",
    )
    p.add_argument(
        "--date-format",
        dest="date_locale",
        default=None,
        choices=["dmy", "mdy"],
        help="Short date interpretation: dmy (day-month-year) or mdy (month-day-year). Default: dmy",
    )
    return p


def _prompt_choice(
    prompt: str,
    *,
    choices: list[str],
    default: str,
    normalize: Callable[[str], str] | None = None,
) -> str:
    # First occurrence wins when normalized keys collide (e.g. different casing).
    mapping: dict[str, str] = {}
    for c in choices:
        key = normalize(c) if normalize else c
        if key not in mapping:
            mapping[key] = c
    default_key = normalize(default) if normalize else default
    if default_key not in mapping:
        mapping[default_key] = default

    while True:
        try:
            value = input(prompt).strip()
        except EOFError:
            return mapping[default_key]
        if not value:
            return mapping[default_key]
        key = normalize(value) if normalize else value
        if key in mapping:
            return mapping[key]
        print(f"Invalid choice: {value}. Valid choices: {', '.join(choices)}")


def main(argv: list[str] | None = None) -> None:
    setup_logging()

    parser = _build_parser()
    args = parser.parse_args(argv)

    directory = args.dir
    if directory is None:
        if _is_interactive():
            try:
                directory = (
                    input(
                        "Path to the directory with PDFs (default: ./input_files): "
                    ).strip()
                    or "./input_files"
                )
            except EOFError:
                directory = "./input_files"
        else:
            directory = "./input_files"

    directory = (directory or "").strip()
    if not directory:
        raise SystemExit(
            "Error: --dir must be non-empty. Provide a path or set the directory "
            "when prompted."
        )

    language = args.language
    if language is None:
        if _is_interactive():
            language = _prompt_choice(
                "Language (de/en, default: de): ",
                choices=["de", "en"],
                default="de",
                normalize=str.lower,
            )
        else:
            language = "de"

    desired_case = args.desired_case
    if desired_case is None:
        if _is_interactive():
            desired_case = _prompt_choice(
                (
                    "Desired case format (camelCase, kebabCase, snakeCase, "
                    "default: kebabCase): "
                ),
                choices=["camelCase", "kebabCase", "snakeCase"],
                default="kebabCase",
                normalize=str.lower,
            )
        else:
            desired_case = "kebabCase"

    project = args.project
    if project is None:
        if _is_interactive():
            try:
                project = input("Project name (optional): ").strip()
            except EOFError:
                project = ""
        else:
            project = ""

    version = args.version
    if version is None:
        if _is_interactive():
            try:
                version = input("Version (optional): ").strip()
            except EOFError:
                version = ""
        else:
            version = ""

    prefer_llm_category = bool(getattr(args, "prefer_llm_category", False))
    date_locale = getattr(args, "date_locale", None) or "dmy"

    config = RenamerConfig(
        language=language,
        desired_case=desired_case,
        project=project,
        version=version,
        prefer_llm_category=prefer_llm_category,
        date_locale=date_locale,
    )
    try:
        rename_pdfs_in_directory(directory, config=config)
    except (FileNotFoundError, NotADirectoryError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Invalid JSON in data file. Check heuristic_scores.json / "
            f"meta_stopwords.json in the data directory. {exc!s}"
        ) from exc
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc