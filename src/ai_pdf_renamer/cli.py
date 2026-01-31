from __future__ import annotations

import argparse

from .logging_utils import setup_logging
from .renamer import RenamerConfig, rename_pdfs_in_directory


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
    return p


def main(argv: list[str] | None = None) -> None:
    setup_logging()

    parser = _build_parser()
    args = parser.parse_args(argv)

    directory = args.dir
    if directory is None:
        directory = (
            input("Path to the directory with PDFs (default: ./input_files): ").strip()
            or "./input_files"
        )

    language = args.language
    if language is None:
        language = input("Language (de/en, default: de): ").strip().lower() or "de"

    desired_case = args.desired_case
    if desired_case is None:
        desired_case = (
            input(
                "Desired case format (camelCase, kebabCase, snakeCase, "
                "default: kebabCase): "
            ).strip()
            or "kebabCase"
        )

    project = args.project
    if project is None:
        project = input("Project name (optional): ").strip()

    version = args.version
    if version is None:
        version = input("Version (optional): ").strip()

    config = RenamerConfig(
        language=language,
        desired_case=desired_case,
        project=project,
        version=version,
    )
    rename_pdfs_in_directory(directory, config=config)
