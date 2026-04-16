"""Adapter - extract text from EPUB via ebooklib + BeautifulSoup.

Fundamentacao: Percival & Gregory, Architecture Patterns, Cap. 2.g.
'What Is a Port and What Is an Adapter, in Python?'

Isolated I/O: swapping ebooklib for another parser changes only this file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from docslice.log import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)


def extract_epub(path: Path) -> str:
    """Extract text from all document items in an EPUB file.

    Args:
        path: Path to the EPUB file.

    Returns:
        Raw text from all XHTML documents, concatenated.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If ebooklib cannot read the file.
    """
    from pathlib import Path as _Path

    p = _Path(path)
    if not p.exists():
        msg = f"EPUB file not found: {path}"
        raise FileNotFoundError(msg)

    try:
        book = epub.read_epub(str(path), options={"ignore_ncx": True})
    except Exception as exc:
        msg = f"Cannot open EPUB: {path}"
        raise RuntimeError(msg) from exc

    chapters: list[str] = []
    items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))

    for item in items:
        html_bytes = item.get_content()
        soup = BeautifulSoup(html_bytes, "html.parser")
        text = soup.get_text(separator="\n")
        if text.strip():
            chapters.append(text)

    logger.info(
        "EPUB extraction complete: %d document items, %d with text",
        len(items),
        len(chapters),
    )
    return "\n\n".join(chapters)
