"""Normalize extracted text - structural preservation, no visual noise.

Fundamentacao: Ramalho, Fluent Python, Cap. 4.
'Unicode Text Versus Bytes.'

Preserves: paragraphs, titles, chapter breaks.
Removes: repeated whitespace, page headers/footers, form-feed noise.

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
