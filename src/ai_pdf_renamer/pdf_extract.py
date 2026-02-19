from __future__ import annotations

import logging
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# PDF metadata date format: D:YYYYMMDDHHmmss... or D:YYYYMMDD
_PDF_DATE_PREFIX = re.compile(r"^D:(\d{4})(\d{2})(\d{2})")

# Minimum extracted characters below which we try OCR (image-only PDFs).
MIN_CHARS_BEFORE_OCR = 50

# Optimized for Qwen3 8B 128K context: reserve ~8K tokens for prompt + response.
CONTEXT_128K_MAX_CONTENT_TOKENS = 120_000

# Cached tiktoken encoding to avoid repeated get_encoding() in _shrink_to_token_limit.
_tiktoken_encoding: Any = None


def _token_count(text: str) -> int:
    global _tiktoken_encoding
    try:
        import tiktoken

        if _tiktoken_encoding is None:
            _tiktoken_encoding = tiktoken.get_encoding("cl100k_base")
        return len(_tiktoken_encoding.encode(text))
    except Exception:
        # Fallback heuristic: ~4 chars per token for typical text.
        return max(1, len(text) // 4)


def _shrink_to_token_limit(text: str, *, max_tokens: int) -> str:
    while _token_count(text) > max_tokens and len(text) > 200:
        new_len = int(len(text) * 0.9)
        # Prefer cut at last space to avoid mid-word truncation
        chunk = text[:new_len]
        last_space = chunk.rfind(" ")
        if last_space > len(text) // 2:
            new_len = last_space
        text = text[:new_len]
    return text


def pdf_to_text(
    filepath: str | Path | None,
    *,
    max_tokens: int = CONTEXT_128K_MAX_CONTENT_TOKENS,
    max_pages: int = 0,
) -> str:
    """
    Extracts text from a PDF via PyMuPDF (fitz). Import is done lazily so that
    core functionality can be tested without optional deps installed.
    """
    if filepath is None:
        return ""
    try:
        import fitz  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("PyMuPDF is required for PDF extraction. Install with: pip install -e '.[pdf]'") from exc

    path = Path(filepath)
    try:
        doc = fitz.open(path)
    except Exception as exc:
        logger.error("Error opening file %s: %s", path, exc)
        return ""

    page_count = getattr(doc, "page_count", 0) or 0
    if max_pages > 0:
        page_count = min(page_count, max_pages)
    try:
        pieces = _extract_pages(doc, path, max_pages=max_pages)
    finally:
        closer = getattr(doc, "close", None)
        if callable(closer):
            closer()

    content = "\n".join(pieces).strip()
    if not content:
        if page_count > 0:
            logger.warning(
                "No text extracted from %s (%s page(s)). File may be encrypted, image-only, or "
                "extraction failed for all pages.",
                path,
                page_count,
            )
        return ""

    return _shrink_to_token_limit(content, max_tokens=max_tokens)


def _ocr_language_code(lang: str) -> str:
    """Map config language (de/en) to Tesseract/OCRmyPDF language code."""
    if (lang or "").strip().lower() == "en":
        return "eng"
    return "deu"


def pdf_to_text_with_ocr(
    filepath: str | Path | None,
    *,
    max_tokens: int = CONTEXT_128K_MAX_CONTENT_TOKENS,
    max_pages: int = 0,
    min_chars_for_ocr: int = MIN_CHARS_BEFORE_OCR,
    language: str = "de",
) -> str:
    """
    Extract text from a PDF; if too little text is found and OCRmyPDF is
    available, run OCR first then extract. Requires optional dependency
    ocrmypdf and system Tesseract. Falls back to non-OCR extraction on
    missing dependency or OCR failure.
    """
    text = pdf_to_text(
        filepath,
        max_tokens=max_tokens,
        max_pages=max_pages,
    )
    if not filepath or len(text.strip()) >= min_chars_for_ocr:
        return text

    try:
        import ocrmypdf
    except ImportError:
        logger.warning(
            "OCR requested but ocrmypdf not installed. Install with: pip install -e '.[ocr]' (and install Tesseract)."
        )
        return text

    path = Path(filepath)
    if not path.exists() or not path.is_file():
        return text

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix="ai_pdf_renamer_ocr_") as f:
            tmp = Path(f.name)
        ocrmypdf.ocr(
            str(path),
            str(tmp),
            language=_ocr_language_code(language),
        )
        text_ocr = pdf_to_text(tmp, max_tokens=max_tokens, max_pages=max_pages)
        if text_ocr.strip():
            logger.info("OCR produced %s chars for %s", len(text_ocr.strip()), path.name)
            return text_ocr
    except Exception as exc:
        logger.warning("OCR failed for %s: %s. Using original extraction.", path, exc)
    finally:
        if tmp is not None and tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    return text


def _parse_pdf_date(value: str | None) -> date | None:
    """Parse PDF metadata date string (D:YYYYMMDD...) to date. Returns None if invalid or missing."""
    if not value or not isinstance(value, str):
        return None
    m = _PDF_DATE_PREFIX.match(value.strip())
    if not m:
        return None
    try:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(y, mo, d)
    except (ValueError, TypeError):
        return None


def get_pdf_metadata(filepath: str | Path | None) -> dict[str, Any]:
    """
    Read PDF metadata (Title, Author, CreationDate, ModDate) without extracting text.
    Returns dict with keys: title (str), author (str), creation_date (YYYY-MM-DD or None),
    mod_date (YYYY-MM-DD or None). Empty dict on error or missing PyMuPDF.
    """
    result: dict[str, Any] = {
        "title": "",
        "author": "",
        "creation_date": None,
        "mod_date": None,
    }
    if not filepath:
        return result
    try:
        import fitz  # type: ignore[import-not-found]
    except Exception:
        return result
    path = Path(filepath)
    try:
        doc = fitz.open(path)
    except Exception as exc:
        logger.debug("Could not open PDF for metadata %s: %s", path, exc)
        return result
    try:
        meta = doc.metadata or {}
        result["title"] = (meta.get("title") or "").strip()
        result["author"] = (meta.get("author") or "").strip()
        for key, out_key in (
            ("creationDate", "creation_date"),
            ("modDate", "mod_date"),
        ):
            d = _parse_pdf_date(meta.get(key))
            result[out_key] = d.strftime("%Y-%m-%d") if d else None
    finally:
        closer = getattr(doc, "close", None)
        if callable(closer):
            closer()
    return result


def _extract_pages(doc: Any, path: Path, *, max_pages: int = 0) -> list[str]:
    pieces: list[str] = []
    limit = min(doc.page_count, max_pages) if max_pages > 0 else doc.page_count
    for page_number in range(limit):
        try:
            page = doc[page_number]
        except Exception as exc:
            logger.error("Error accessing page %s in %s: %s", page_number, path, exc)
            continue

        # Prefer single strategy to avoid triple text (text + blocks + rawdict overlap)
        page_text = ""
        try:
            page_text = (page.get_text("text") or "").strip()
        except Exception as exc:
            logger.warning(
                "Page %s get_text('text') failed in %s: %s",
                page_number,
                path,
                exc,
            )
        if not page_text:
            try:
                blocks = page.get_text("blocks") or []
                page_text = " ".join(b[4] for b in blocks if len(b) > 4 and str(b[4]).strip()).strip()
            except Exception as exc:
                logger.warning(
                    "Page %s get_text('blocks') failed in %s: %s",
                    page_number,
                    path,
                    exc,
                )
        if not page_text:
            try:
                rawdict = page.get_text("rawdict") or {}
                parts = []
                for block in rawdict.get("blocks", []):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            t = span.get("text", "")
                            if t and t.strip():
                                parts.append(t.strip())
                page_text = " ".join(parts)
            except Exception as exc:
                logger.warning(
                    "Page %s get_text('rawdict') failed in %s: %s",
                    page_number,
                    path,
                    exc,
                )

        combined = page_text
        if combined:
            pieces.append(combined)
            logger.debug(
                "Combined extracted %s characters from page %s of %s",
                len(combined),
                page_number,
                path,
            )
        else:
            logger.info("Page %s in %s yields no text.", page_number, path)

    return pieces
