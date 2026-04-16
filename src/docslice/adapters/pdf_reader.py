"""Adapter - extract text from PDF via PyMuPDF (fitz).

Fundamentacao: Percival & Gregory, Architecture Patterns, Cap. 2.g.
'What Is a Port and What Is an Adapter, in Python?'

Isolated I/O: swapping PyMuPDF for pdfplumber changes only this file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import fitz

from docslice.log import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)


def extract_pdf(path: Path) -> str:
    """Extract text from all pages of a PDF file.

    Args:
        path: Path to the PDF file.

    Returns:
        Raw text concatenated from all pages, separated by newlines.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If PyMuPDF cannot open the file.
    """
    from pathlib import Path as _Path

    p = _Path(path)
    if not p.exists():
        msg = f"PDF file not found: {path}"
        raise FileNotFoundError(msg)

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
    logger.info("PDF extraction complete: %d pages, %d with text", total, len(pages))
    return "\n".join(pages)
