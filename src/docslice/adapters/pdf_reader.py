"""Adapter - extract text from PDF via pymupdf4llm with fitz fallback.

Fundamentacao: Percival & Gregory, Architecture Patterns, Cap. 2.g.
'What Is a Port and What Is an Adapter, in Python?'

Strategy: pymupdf4llm produces Markdown with preserved structure
(headings, lists, tables) - ideal for LLM ingestion of figure-heavy
books. On any failure (corrupt PDF, version mismatch, layout edge
case) we fall back to plain fitz extraction so the pipeline never
breaks. FileNotFoundError stays outside the try/except: input bugs
must not be hidden by the fallback.

Both backends share the same MuPDF C core, so AGPL licensing is
unchanged. Isolated I/O: swapping backends changes only this file.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pymupdf4llm

from docslice.log import get_logger

logger = get_logger(__name__)


def extract_pdf(path: Path) -> str:
    """Extract text from a PDF, preferring Markdown structure when possible.

    Tries pymupdf4llm first (preserves headings, lists, tables as Markdown).
    On any exception, logs a warning and falls back to plain fitz
    page-by-page extraction.

    Args:
        path: Path to the PDF file.

    Returns:
        Extracted text. Markdown-flavoured on the happy path, plain
        text on fallback. Both are valid input for downstream cleanup
        and splitting.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If both extraction backends fail.
    """
    p = Path(path)
    if not p.exists():
        msg = f"PDF file not found: {path}"
        raise FileNotFoundError(msg)

    try:
        return _extract_via_pymupdf4llm(p)
    except Exception as exc:  # noqa: BLE001 - any failure triggers fallback
        logger.warning(
            "pymupdf4llm extraction failed (%s: %s). Falling back to plain fitz.",
            type(exc).__name__,
            exc,
        )
        return _extract_via_fitz(p)


def _extract_via_pymupdf4llm(path: Path) -> str:
    """Extract via pymupdf4llm.to_markdown - preserves document structure.

    OCR is intentionally disabled (use_ocr=False) because:
      - Auto-OCR was running on ~half of figure-heavy pages, taking
        16+ minutes for a 1,300-page book - inviable at the 30k-page
        scale this project targets. OCR is roughly 1,000x slower than
        native text extraction (per pymupdf4llm's own README).
      - OCR output on covers and photo plates was garbage that would
        pollute downstream LLM indexing more than it helps.
      - Image-only pages (covers, plates, scanned manuscripts) return
        empty strings here - acceptable: downstream cleanup ignores
        empty content via .strip() checks.

    ignore_images=True silences '==> picture omitted <==' markers that
    pymupdf4llm injects by default - pure noise for our use case.
    """
    logger.info("Extracting PDF via pymupdf4llm: %s", path)
    # str() wrap: pymupdf4llm has no stubs, return type is Any under
    # mypy. Explicit str() narrows it without `# type: ignore`.
    text: str = str(
        pymupdf4llm.to_markdown(
            str(path),
            use_ocr=False,
            ignore_images=True,
            show_progress=True,
        )
    )
    logger.info("pymupdf4llm extraction complete: %d chars", len(text))
    return text


def _extract_via_fitz(path: Path) -> str:
    """Extract via plain fitz - page-by-page text, no structure."""
    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        msg = f"Cannot open PDF: {path}"
        raise RuntimeError(msg) from exc

    pages: list[str] = []
    total = len(doc)
    for i, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            pages.append(text)
        if (i + 1) % 500 == 0:
            logger.info("Extracted %d / %d pages", i + 1, total)

    doc.close()
    logger.info("Fitz extraction complete: %d pages, %d with text", total, len(pages))
    return "\n".join(pages)
