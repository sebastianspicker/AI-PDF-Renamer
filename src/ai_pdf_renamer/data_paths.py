from __future__ import annotations

import os
from pathlib import Path

DATA_FILES = {
    "heuristic_patterns.json",
    "heuristic_scores.json",
    "meta_stopwords.json",
}


def project_root(start: Path | None = None) -> Path:
    """
    Best-effort discovery of the repo root for editable/dev runs.
    Falls back to CWD if nothing is found.
    """
    if start is None:
        start = Path(__file__).resolve()

    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def data_dir() -> Path:
    override = os.getenv("AI_PDF_RENAMER_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return project_root(Path(__file__).resolve()).resolve()


def package_data_path(filename: str) -> Path:
    return Path(__file__).resolve().parent / "data" / filename


def data_path(filename: str) -> Path:
    if filename not in DATA_FILES:
        raise ValueError(f"Unsupported data file: {filename}")
    candidate = data_dir() / filename
    if candidate.exists():
        return candidate

    packaged = package_data_path(filename)
    if packaged.exists():
        return packaged

    raise FileNotFoundError(
        f"Data file {filename!r} not found. Looked in: {candidate} and {packaged}. "
        "Set AI_PDF_RENAMER_DATA_DIR to a directory containing the JSON files, "
        "or run from the project root."
    )
