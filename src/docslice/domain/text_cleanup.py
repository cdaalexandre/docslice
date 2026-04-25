"""Normalize extracted text - structural preservation, no visual noise.

Fundamentacao: Ramalho, Fluent Python, Cap. 4.
'Unicode Text Versus Bytes.'

Preserves: paragraphs, titles, chapter breaks.
Removes: repeated whitespace, page headers/footers, form-feed noise,
pymupdf4llm picture markers.

Logica pura. Nao conhece APIs, nao faz I/O.
"""

from __future__ import annotations

import re


def normalize_text(raw: str) -> str:
    """Normalize raw extracted text for downstream LLM consumption.

    Steps:
        1. Normalize line endings to LF.
        2. Remove form-feed characters.
        3. Strip trailing whitespace per line.
        4. Collapse runs of 3+ blank lines into 2 (paragraph boundary).
        5. Collapse runs of spaces/tabs within a line into a single space.
        6. Strip leading/trailing whitespace from the whole text.

    Args:
        raw: Raw text from a PDF or EPUB extractor.

    Returns:
        Cleaned text with structural breaks preserved.
    """
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\f", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[^\S\n]+", " ", text)
    return text.strip()


def remove_page_markers(text: str) -> str:
    """Remove common page number patterns from extracted text.

    Matches patterns like '  42  ', '- 42 -', 'Page 42', standalone numbers.

    Args:
        text: Text potentially containing page markers.

    Returns:
        Text with page markers removed.
    """
    text = re.sub(r"^\s*-?\s*\d{1,5}\s*-?\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[Pp]age\s+\d+\s*$", "", text, flags=re.MULTILINE)
    return text


def remove_picture_markers(text: str) -> str:
    """Remove pymupdf4llm picture markers from extracted text.

    pymupdf4llm injects two kinds of markers when its layout module
    classifies a region as a picture:

      - "**==> picture [WxH] intentionally omitted <==**"
      - "**----- Start of picture text -----**" / "End of picture text"

    The Start/End wrappers are removed but text between them is kept -
    it may contain figure captions or text extracted from inside the
    image. Pure noise inside (e.g. "$$" from cover scans) survives but
    will typically be ignored as a low-signal chunk downstream.

    Args:
        text: Text potentially containing pymupdf4llm picture markers.

    Returns:
        Text with picture markers removed.
    """
    # "**==> picture [WxH] intentionally omitted <==**" - removed entirely.
    # The pattern matches inline (not anchored) so it also strips markers
    # embedded inside markdown tables that use <br> separators.
    text = re.sub(
        r"\*\*==>\s*picture\s+\[\d+\s*x\s*\d+\]\s+intentionally\s+omitted\s*<==\*\*",
        "",
        text,
    )
    # Wrapper markers around extracted image-text - drop the wrappers,
    # keep whatever is between them.
    text = re.sub(r"\*\*-{3,}\s*Start of picture text\s*-{3,}\*\*", "", text)
    text = re.sub(r"\*\*-{3,}\s*End of picture text\s*-{3,}\*\*", "", text)
    return text
