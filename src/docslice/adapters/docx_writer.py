"""Adapter - convert a TXT file to a Word-compatible .docx.

Fundamentacao: Percival & Gregory, Architecture Patterns, Cap. 2.
'Ports and Adapters - external libraries live in adapters.'

Why .docx instead of .doc:
    .doc is the legacy Word 97-2003 binary format. Modern Word and
    Google Docs use .docx (Office Open XML, ZIP-based). Google Drive
    auto-converts .docx into a native Google Doc on upload or
    double-click, with no API or auth required.

Why python-docx:
    Pure-Python, no Office or LibreOffice runtime needed. Maps the
    .docx XML structure to a clean object API. Sufficient for our
    needs (paragraphs, default style).

Paragraph handling:
    The TXT files produced by docslice already use blank lines to
    separate paragraphs (see domain/text_cleanup.normalize_text).
    Each blank-line-separated chunk becomes one Word paragraph.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docx import Document

from docslice.log import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)


def write_txt_as_docx(txt_path: Path, docx_path: Path) -> Path:
    """Convert a TXT file into a .docx file with one paragraph per block.

    Args:
        txt_path: Path to a UTF-8 TXT file (typically produced by the
            converter pipeline).
        docx_path: Destination path for the .docx file. Parent
            directory is created if missing.

    Returns:
        The docx_path argument, for chainability.

    Raises:
        FileNotFoundError: If txt_path does not exist.
    """
    text = txt_path.read_text(encoding="utf-8")

    document = Document()
    paragraphs = text.split("\n\n")
    for block in paragraphs:
        stripped = block.strip()
        if not stripped:
            continue
        document.add_paragraph(stripped)

    docx_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(docx_path))
    logger.debug("Wrote docx %s", docx_path)
    return docx_path
