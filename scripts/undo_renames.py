#!/usr/bin/env python3
"""
Revert renames from a rename log file (as written by --rename-log).

Usage:
  python scripts/undo_renames.py --rename-log path/to/rename.log [--dry-run]
  ai-pdf-renamer-undo --rename-log path/to/rename.log [--dry-run]
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from ai_pdf_renamer.undo_cli import main
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from ai_pdf_renamer.undo_cli import main

if __name__ == "__main__":
    main()
