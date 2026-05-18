"""Normalize extracted text - structural preservation, no visual noise.

Fundamentacao: Ramalho, Fluent Python, Cap. 4.
'Unicode Text Versus Bytes.'

Preserves: paragraphs, titles, chapter breaks, real markdown tables.
Removes: repeated whitespace, page headers/footers, form-feed noise,
pymupdf4llm picture markers, pymupdf-layout pseudo-tables (rows
classified as a table with no real header separator).

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


# XML 1.0 valid control chars: TAB (0x09), LF (0x0A), CR (0x0D).
# Everything else in the C0 control range (0x00-0x08, 0x0B, 0x0C,
# 0x0E-0x1F) is rejected by lxml when python-docx builds the document
# XML tree, raising "All strings must be XML compatible: Unicode or
# ASCII, no NULL bytes or control characters". Corrupt PDFs (e.g.
# broken JPX image streams) routinely leak these bytes into extracted
# text via pymupdf4llm.
_XML_ILLEGAL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def strip_control_chars(text: str) -> str:
    """Remove XML-illegal C0 control characters from text.

    Preserves TAB, LF, CR. Strips everything else in the 0x00-0x1F
    range. Required to keep downstream XML-based writers (python-docx,
    future EPUB output) from raising "All strings must be XML
    compatible: Unicode or ASCII, no NULL bytes or control characters".

    Apply *after* `normalize_text` so the form-feed to newline
    translation (which preserves PDF page-break semantics) runs first;
    form-feed is also covered here as a defensive no-op in case the
    pipeline is reordered later.

    Args:
        text: Cleaned text that may still contain stray C0 control
            characters from corrupt source documents.

    Returns:
        Text with C0 control chars (except TAB/LF/CR) removed.
    """
    return _XML_ILLEGAL_RE.sub("", text)


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


def flatten_pseudo_tables(text: str) -> str:
    """Convert misclassified pseudo-tables back into prose.

    pymupdf-layout sometimes wraps prose - definitions, vertical lists,
    multi-row labels - inside a fake markdown table row using <br> tags
    instead of real cells. The signal that it is fake (not a real
    table) is the absence of a '|---|' separator on the next line.

    For each line that starts with '|' AND contains '<br>' AND is NOT
    followed by '|---', this function:
      - strips the outer pipes
      - replaces <br> with newline
      - replaces inner pipes (column separators) with newline

    Real markdown tables (with separator) are left intact - the LLM
    downstream handles their <br>-collapsed cells fine, and rewriting
    them risks losing structure.

    Args:
        text: Markdown text potentially containing pseudo-tables.

    Returns:
        Text with pseudo-tables flattened to prose; real tables intact.
    """
    lines = text.split("\n")
    result: list[str] = []
    n = len(lines)

    for i in range(n):
        line = lines[i]
        next_line = lines[i + 1] if i + 1 < n else ""

        if line.startswith("|") and "<br>" in line and not next_line.startswith("|---"):
            cleaned = line.strip().lstrip("|").rstrip("|").strip()
            cleaned = cleaned.replace("<br>", "\n")
            cleaned = cleaned.replace("|", "\n")
            result.append(cleaned)
        else:
            result.append(line)

    out = "\n".join(result)
    # Collapse any 3+ consecutive newlines that may result from the
    # multi-line replacement meeting an existing blank line.
    return re.sub(r"\n{3,}", "\n\n", out)
