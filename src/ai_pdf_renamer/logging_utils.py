from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(
    *, log_file: str | Path = "error.log", level: int = logging.INFO
) -> None:
    root = logging.getLogger()
    root.setLevel(level)

    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        root.addHandler(console_handler)

    if not any(isinstance(h, logging.FileHandler) for h in root.handlers):
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        root.addHandler(file_handler)
