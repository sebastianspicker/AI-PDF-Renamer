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


def data_path(filename: str) -> Path:
    if filename not in DATA_FILES:
        raise ValueError(f"Unsupported data file: {filename}")
    return data_dir() / filename
