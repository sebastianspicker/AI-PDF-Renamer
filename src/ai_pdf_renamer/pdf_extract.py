from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _token_count(text: str) -> int:
    try:
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # Fallback heuristic: ~4 chars per token for typical text.
        return max(1, len(text) // 4)


def _shrink_to_token_limit(text: str, *, max_tokens: int) -> str:
    while _token_count(text) > max_tokens and len(text) > 200:
        text = text[: int(len(text) * 0.9)]
    return text


def pdf_to_text(filepath: str | Path, *, max_tokens: int = 15000) -> str:
    """
    Extracts text from a PDF via PyMuPDF (fitz). Import is done lazily so that
    core functionality can be tested without optional deps installed.
    """
    try:
        import fitz  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "PyMuPDF is required for PDF extraction. "
            "Install with: pip install -e '.[pdf]'"
        ) from exc

    path = Path(filepath)
    try:
        doc = fitz.open(path)
    except Exception as exc:
        logger.error("Error opening file %s: %s", path, exc)
        return ""

    pieces: list[str] = []
    for page_number in range(doc.page_count):
        try:
            page = doc[page_number]
        except Exception as exc:
            logger.error("Error accessing page %s in %s: %s", page_number, path, exc)
            continue

        page_bits: list[str] = []

        try:
            page_bits.append(page.get_text("text"))
        except Exception:
            pass

        try:
            blocks = page.get_text("blocks") or []
            page_bits.append(
                " ".join(b[4] for b in blocks if len(b) > 4 and str(b[4]).strip())
            )
        except Exception:
            pass

        try:
            rawdict = page.get_text("rawdict") or {}
            for block in rawdict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        t = span.get("text", "")
                        if t and t.strip():
                            page_bits.append(t)
        except Exception:
            pass

        combined = " ".join(t.strip() for t in page_bits if t and t.strip()).strip()
        if combined:
            pieces.append(combined)
            logger.info(
                "Combined extracted %s characters from page %s of %s",
                len(combined),
                page_number,
                path,
            )
        else:
            logger.info("Page %s in %s yields no text.", page_number, path)

    content = "\n".join(pieces).strip()
    if not content:
        return ""

    return _shrink_to_token_limit(content, max_tokens=max_tokens)
