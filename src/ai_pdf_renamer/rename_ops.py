"""
Rename and filename-sanitization helpers.

Extracted from renamer to keep collision/sanitize logic in one place.
"""

from __future__ import annotations

import errno
import logging
import os
import re
import shutil
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

# Path separators and control characters (incl. NUL) that must not appear in filenames.
FILENAME_UNSAFE_RE = re.compile(r"[\x00-\x1f\x7f/\\:*?\"<>|]")

# Reserved names on Windows (case-insensitive). Avoid using as base name to prevent EINVAL on rename.
FILENAME_RESERVED_WIN = frozenset(
    {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
)

# Max retries for rename when target exists. After this, fail with clear message.
MAX_RENAME_RETRIES = 20


def sanitize_filename_base(name: str) -> str:
    """Remove path separators and control chars; ensure non-empty; avoid Windows reserved names."""
    if not name or not name.strip():
        return "unnamed"
    safe = FILENAME_UNSAFE_RE.sub("", name.strip())
    safe = safe.strip() or "unnamed"
    if safe.upper() in FILENAME_RESERVED_WIN:
        return f"{safe}_"
    return safe


def apply_single_rename(
    file_path: Path,
    base: str,
    *,
    plan_file_path: Path | str | None,
    plan_entries: list[dict[str, str]] | None,
    dry_run: bool,
    backup_dir: Path | str | None,
    on_success: Callable[[Path, Path, str], None] | None = None,
) -> tuple[bool, Path]:
    """
    Apply rename for one file: collision loop, backup, optional plan.
    Returns (success, final_target).

    Uses rename as the existence check to reduce TOCTOU. On FileExistsError, tries next suffix.
    EXDEV (cross-fs): best-effort copy+unlink.
    """
    suffix = file_path.suffix
    current_base = base
    target = file_path.with_name(base + suffix)
    counter = 0
    for attempt in range(MAX_RENAME_RETRIES):
        # Skip existing targets to avoid overwriting (os.rename replaces on Unix).
        while target.exists():
            counter += 1
            current_base = f"{base}_{counter}"
            target = file_path.with_name(current_base + suffix)
        try:
            if plan_file_path:
                if plan_entries is not None:
                    plan_entries.append({"old": str(file_path), "new": str(target)})
                logger.info("Plan: %s -> %s", file_path.name, target.name)
                return (True, target)
            if not dry_run:
                if backup_dir:
                    backup_path = Path(backup_dir) / file_path.name
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, backup_path)
                os.rename(file_path, target)
                if on_success is not None:
                    on_success(file_path, target, current_base)
            return (True, target)
        except FileExistsError:
            counter += 1
            current_base = f"{base}_{counter}"
            target = file_path.with_name(current_base + suffix)
            if attempt == MAX_RENAME_RETRIES - 1:
                logger.error(
                    "Rename failed after %d attempts (target already exists): %s -> %s",
                    MAX_RENAME_RETRIES,
                    file_path,
                    target,
                )
                raise OSError(
                    errno.EEXIST,
                    f"Could not rename {file_path.name}: target exists and collision suffix limit "
                    f"({MAX_RENAME_RETRIES}) reached. Move or rename conflicting files and retry.",
                ) from None
        except OSError as e:
            if getattr(errno, "ENAMETOOLONG", None) is not None and e.errno == errno.ENAMETOOLONG:
                raise OSError(
                    e.errno,
                    f"Filename too long for filesystem: {target.name!r}. "
                    "Shorten project/version or content-derived parts.",
                ) from e
            if e.errno == errno.EXDEV:
                if dry_run:
                    return (True, target)
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
                if on_success is not None:
                    on_success(file_path, target, current_base)
                return (True, target)
            raise
    raise RuntimeError(f"Rename failed after {MAX_RENAME_RETRIES} attempts for {file_path.name}")  # defensive
