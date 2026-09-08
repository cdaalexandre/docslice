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


# A bare number or a 'Page N' label on its own line looks like a page
# marker, but looking like one is not enough: prose broken by PDF
# layout strands real content on its own line too - a year inside a
# citation, an article number in a legal text, a value from a table
# that lost its rows. Matching the pattern is a necessary condition,
# never a sufficient one. See _is_isolated below.
_PAGE_NUMBER_RE = re.compile(r"^\s*-?\s*\d{1,5}\s*-?\s*$")
_PAGE_LABEL_RE = re.compile(r"^\s*[Pp]age\s+\d+\s*$")


def _looks_like_page_marker(line: str) -> bool:
    """Report whether a single line matches a page-marker pattern.

    Args:
        line: One line of text, without its trailing newline.

    Returns:
        True if the line is a bare page number ('42', '- 42 -') or a
        'Page N' label. Says nothing about whether it *is* a marker -
        that needs the isolation check too.
    """
    return bool(_PAGE_NUMBER_RE.match(line) or _PAGE_LABEL_RE.match(line))


def _is_isolated(lines: list[str], index: int) -> bool:
    """Report whether the line at index sits alone between blank lines.

    A running header or footer is surrounded by blank lines once the
    page break is normalized. Content stranded on its own line by a
    layout break keeps prose touching it on at least one side, so the
    two cases separate cleanly.

    Args:
        lines: All lines of the text.
        index: Position of the candidate line.

    Returns:
        True if both neighbours are blank or absent (start/end of text).
    """
    before_blank = index == 0 or not lines[index - 1].strip()
    after_blank = index == len(lines) - 1 or not lines[index + 1].strip()
    return before_blank and after_blank


def remove_page_markers(text: str) -> str:
    """Remove page numbers and 'Page N' labels that sit on their own line.

    Only *isolated* markers are removed - a matching line surrounded by
    blank lines (or at the start/end of the text). A matching line with
    prose touching it is left alone, because at that position it is far
    more likely to be content stranded by a layout break: a year in a
    broken citation, an article number in a legal document, a value
    from a table that lost its structure.

    The trade-off is deliberate. A footer that stayed glued to the text
    survives as low-signal noise; deleted content is unrecoverable.

    Args:
        text: Text potentially containing page markers. Expected to
            have been through normalize_text already, so runs of blank
            lines are collapsed to one and the isolation signal holds.

    Returns:
        Text with isolated page markers replaced by empty lines.
    """
    lines = text.split("\n")
    result: list[str] = []

    for index, line in enumerate(lines):
        if _looks_like_page_marker(line) and _is_isolated(lines, index):
            result.append("")
        else:
            result.append(line)

    return "\n".join(result)


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


def normalize_markdown(raw: str) -> str:
    r"""Normalize raw Markdown for the full .md output, preserving structure.

    Unlike `normalize_text` (which targets clean prose for TXT/DOCX and
    collapses whitespace), this keeps Markdown structure intact:
    headings, list indentation, table pipes, and intentional spacing
    all survive. Only the bare minimum is touched:

        1. Normalize line endings to LF (\r\n and \r become \n).
        2. Convert form-feed to a newline (preserves page-break breaks).
        3. Strip trailing whitespace per line (cosmetic, never structural).

    Control-char stripping, picture-marker removal, and pseudo-table
    flattening are applied separately by the service layer so this
    function stays a pure, single-purpose line-ending normalizer.

    Args:
        raw: Raw Markdown text from a PDF or EPUB extractor.

    Returns:
        Markdown with LF line endings and no trailing whitespace,
        structure otherwise untouched.
    """
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\f", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines)
